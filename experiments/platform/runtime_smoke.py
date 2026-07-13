"""Short single-host API concurrency smoke test for TraceGuard."""

import argparse
import base64
import csv
import json
import math
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REQUIRED_RESPONSE_FIELDS = {
    "status",
    "label",
    "tamper_type",
    "fake_prob",
    "risk_score",
    "risk_level",
    "bbox_list",
}


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percent * len(ordered)) - 1))
    return ordered[index]


def summarize(rows: list[dict], wall_seconds: float) -> dict:
    successful = [row for row in rows if row["ok"]]
    latencies = [float(row["latency_seconds"]) for row in successful]
    return {
        "requests": len(rows),
        "successes": len(successful),
        "failures": len(rows) - len(successful),
        "success_rate": len(successful) / len(rows) if rows else 0.0,
        "wall_seconds": wall_seconds,
        "throughput_requests_per_second": len(successful) / wall_seconds if wall_seconds else 0.0,
        "latency_seconds": {
            "min": min(latencies, default=0.0),
            "median": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "max": max(latencies, default=0.0),
        },
    }


def analyze_once(endpoint: str, payload: bytes, request_id: int, timeout: float) -> dict:
    started = time.perf_counter()
    row = {
        "request_id": request_id,
        "ok": False,
        "http_status": 0,
        "latency_seconds": 0.0,
        "label": "",
        "tamper_type": "",
        "fake_prob": "",
        "risk_level": "",
        "error": "",
    }
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            missing = sorted(REQUIRED_RESPONSE_FIELDS - body.keys())
            if missing:
                raise ValueError(f"missing response fields: {', '.join(missing)}")
            row.update(
                ok=response.status == 200 and body.get("status") == "success",
                http_status=response.status,
                label=body["label"],
                tamper_type=body["tamper_type"],
                fake_prob=body["fake_prob"],
                risk_level=body["risk_level"],
            )
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        row["error"] = str(exc)
    finally:
        row["latency_seconds"] = time.perf_counter() - started
    return row


def run_smoke(
    endpoint: str,
    image_path: Path,
    request_count: int,
    concurrency: int,
    timeout: float,
) -> tuple[list[dict], dict]:
    image_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = json.dumps({"image_base64": image_base64}).encode("utf-8")
    started = time.perf_counter()
    rows = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(analyze_once, endpoint, payload, request_id, timeout)
            for request_id in range(1, request_count + 1)
        ]
        for future in as_completed(futures):
            rows.append(future.result())
    wall_seconds = time.perf_counter() - started
    rows.sort(key=lambda row: row["request_id"])
    summary = summarize(rows, wall_seconds)
    summary.update(
        endpoint=endpoint,
        image=str(image_path),
        concurrency=concurrency,
        timeout_seconds=timeout,
    )
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/api/v1/analyze")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("requests and concurrency must be positive")

    rows, summary = run_smoke(
        args.endpoint,
        args.image,
        args.requests,
        args.concurrency,
        args.timeout,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "requests.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if summary["failures"] == 0 else 1)


if __name__ == "__main__":
    main()
