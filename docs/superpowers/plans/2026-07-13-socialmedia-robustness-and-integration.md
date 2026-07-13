# TraceGuard Social-Media Robustness and Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible social-media robustness evaluation, integrate verified evidence into TraceGuard, and finish every independently actionable system, report, and submission task owned by Zhu Yishuai.

**Architecture:** Keep `Detector` as the only source of `label` and `fake_prob`, add a batched inference method for throughput, and evaluate images directly from ZIP entries so ignored datasets do not need a second extracted copy. Store raw predictions and summaries separately, keep every metric traceable to `sample_id`, checkpoint hash, archive hash, command, and configuration, then promote only verified conclusions into the report.

**Tech Stack:** Python 3.10, PyTorch, torchvision, Pillow, NumPy, pytest, Markdown, FastAPI, Playwright, local nature-figure Python workflow.

---

### Task 1: Freeze the Experiment Contract

**Files:**
- Create: `docs/experiments/socialmedia_robustness_contract.md`
- Modify: `docs/inventory/datasets-and-models.md`
- Modify: `DEVLOG.md`

- [ ] **Step 1: Record the routing gate**

Write the contract with `User Value`, `Current Evidence`, `Scope`, `Out of Scope`, `Affected Modules`, `Data Contract`, `Acceptance Criteria`, `Validation Commands`, `Asset / Report Impact`, `Risks and Rollback`, and status `ready-for-implementation`.

- [ ] **Step 2: Fix the metric boundary**

Define two distinct analyses:

```text
paired GenImage: 8000 fake samples x Original/Facebook/WeChat/Weibo
  -> Fake Recall, mean fake_prob, probability delta, recall retention

platform classification benchmark: test_eachfake_500_real500 per platform
  -> Accuracy, macro F1, ROC AUC, Real Recall, Fake Recall
```

State explicitly that full Original-to-platform Accuracy/F1/AUC retention cannot be computed until the original `test_eachfake_500_real500` archive is supplied.

- [ ] **Step 3: Validate documentation formatting**

Run: `git diff --check`

Expected: exit code 0.

### Task 2: Add Authoritative Batched Detection

**Files:**
- Modify: `detection/inference_api.py`
- Create: `tests/test_detection_batch.py`

- [ ] **Step 1: Write failing tests**

Test that `Detector.predict_batch(images, batch_size=2)`:

```python
def test_predict_batch_preserves_order(detector_stub, sample_images):
    results = detector_stub.predict_batch(sample_images, batch_size=2)
    assert len(results) == len(sample_images)
    assert all(set(r) == {"label", "real_prob", "fake_prob", "risk_score"} for r in results)

def test_predict_batch_rejects_non_positive_batch_size(detector_stub, sample_images):
    with pytest.raises(ValueError, match="batch_size"):
        detector_stub.predict_batch(sample_images, batch_size=0)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `E:\anaconda\envs\osn_video2\python.exe -m pytest tests/test_detection_batch.py -q`

Expected: failure because `predict_batch` does not exist.

- [ ] **Step 3: Implement minimal batched inference**

Add `predict_batch(self, image_or_paths, batch_size=32)` that loads each input through `_load`, stacks `self.transform` outputs, runs `self.model` under `torch.no_grad()`, applies softmax, and returns the same fields and semantics as repeated `predict()` calls.

- [ ] **Step 4: Run focused and full tests**

Run:

```powershell
E:\anaconda\envs\osn_video2\python.exe -m pytest tests/test_detection_batch.py -q
E:\anaconda\envs\osn_video2\python.exe -m pytest tests -q
```

Expected: focused tests pass and all 140 existing tests plus new tests pass.

### Task 3: Build ZIP-Streaming Evaluation and Metrics

**Files:**
- Create: `experiments/__init__.py`
- Create: `experiments/socialmedia/__init__.py`
- Create: `experiments/socialmedia/evaluate.py`
- Create: `tests/test_socialmedia_evaluate.py`

- [ ] **Step 1: Write failing archive and pairing tests**

Create temporary ZIP fixtures and test:

```python
def test_checkpoint_entries_are_excluded(tmp_path):
    entries = list_image_entries(make_zip(tmp_path, ["set/a.jpg", "set/.ipynb_checkpoints/a-checkpoint.jpg"]))
    assert [entry.name for entry in entries] == ["set/a.jpg"]

def test_genimage_pairs_require_all_variants(zip_fixture):
    pairs = build_genimage_pairs(zip_fixture.original, zip_fixture.platforms)
    assert pairs[0].pair_status == "complete"
    assert pairs[0].sample_id == "genimage:adm:0_adm_174"
```

- [ ] **Step 2: Write failing metric tests**

Use fixed predictions to verify Accuracy, macro F1, rank-based ROC AUC, class recall, probability delta, and zero-denominator retention handling without adding scikit-learn.

- [ ] **Step 3: Run tests and verify RED**

Run: `E:\anaconda\envs\osn_video2\python.exe -m pytest tests/test_socialmedia_evaluate.py -q`

Expected: import failure because the evaluator does not exist.

- [ ] **Step 4: Implement archive parsing and metrics**

Implement focused units:

```python
list_image_entries(zip_path) -> list[ArchiveImage]
build_genimage_pairs(original_zip, platform_zips) -> list[PairRecord]
parse_eachfake_label(filename) -> Literal["real", "fake"]
binary_metrics(labels, probabilities, threshold=0.5) -> dict[str, float]
paired_fake_metrics(records) -> list[dict[str, object]]
```

Reject duplicate canonical sample IDs, missing variants, unreadable images, ambiguous labels, and non-finite probabilities with explicit errors.

- [ ] **Step 5: Implement resumable inference CLI**

Support:

```powershell
python -m experiments.socialmedia.evaluate paired-genimage `
  --manifest dataset/socialmedia/manifests/genimage_socialmedia_pairs.csv `
  --checkpoint best.pth --device cuda --batch-size 32 `
  --output results/socialmedia/paired_genimage
```

Write append-safe raw CSV rows, `run_metadata.json`, `summary_by_platform.csv`, `summary_by_generator.csv`, and `failures.csv`. Resume by the compound key `(sample_id, variant)` and never overwrite a completed row silently.

- [ ] **Step 6: Run tests and verify GREEN**

Run focused tests, then `python -m pytest tests -q`.

Expected: all tests pass.

### Task 4: Establish a Reproducible GPU Runtime

**Files:**
- Create: `docs/experiments/socialmedia_runtime.md`

- [ ] **Step 1: Create an isolated environment outside the user Conda directory**

Create `E:\anaconda\envs\traceguard` with Python 3.10. Install a CUDA-enabled PyTorch/torchvision pair compatible with the RTX 4060 and the current NVIDIA driver, plus `Pillow`, `numpy`, `scipy`, `PyYAML`, `pytest`, `fastapi`, `uvicorn`, `pydantic`, and `matplotlib`.

- [ ] **Step 2: Verify GPU and checkpoint loading**

Run:

```powershell
E:\anaconda\envs\traceguard\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
E:\anaconda\envs\traceguard\python.exe -c "from detection import Detector; Detector('best.pth', 'cuda'); print('checkpoint_ok')"
```

Expected: CUDA is true, device is the RTX 4060 Laptop GPU, and checkpoint loading succeeds.

- [ ] **Step 3: Run a timed smoke benchmark**

Evaluate 32 paired images and record elapsed time, peak GPU memory, package versions, checkpoint SHA-256, and exact command. Select a batch size that stays below available GPU memory without changing model outputs.

### Task 5: Run Social-Media Experiments

**Files:**
- Generate ignored outputs under: `results/socialmedia/`
- Modify: `docs/experiments/socialmedia_robustness_contract.md`
- Modify: `DEVLOG.md`

- [ ] **Step 1: Run paired GenImage inference**

Evaluate 32,000 image variants: 8000 Original plus 8000 each for Facebook, WeChat, and Weibo. Preserve all raw rows and failures.

- [ ] **Step 2: Run three platform classification benchmarks**

Evaluate each `*_test_eachfake_500_real500.zip`, derive labels only from validated filenames, and report class balance alongside Accuracy, macro F1, ROC AUC, Real Recall, and Fake Recall.

- [ ] **Step 3: Verify result integrity**

Require 32,000 unique paired prediction keys, zero silent failures, correct archive/checkpoint hashes, finite probabilities, and exact per-generator counts. If any item fails, keep the run incomplete and diagnose it.

- [ ] **Step 4: Freeze reportable conclusions**

Promote only measurements supported by raw CSV and run metadata. Keep the missing original balanced benchmark as an explicit dependency on the detection teammate.

### Task 6: Produce Report-Level Figures and Cases

**Files:**
- Create generated figures under: `output/figures/socialmedia/`
- Modify: `reports/TraceGuard.md`
- Modify: `docs/submission_progress.md`

- [ ] **Step 1: Use the local nature-figure Python workflow**

Create a performance-retention figure and a generator-by-platform comparison figure. Do not put figure titles or report prose inside the canvas; use Word-style captions in the report.

- [ ] **Step 2: Select auditable cases**

Choose stable, degraded, and conflicting samples from measured deltas. Generate full pipeline evidence only for this small case set, retaining the same `sample_id` used by detection results.

- [ ] **Step 3: Replace stale or unsupported report text**

Remove outdated FakeTrace implementation claims, replace planned/future language for already implemented Web/API/CLI capabilities, insert verified social-media results, and leave teammate-owned localization metrics and ablation results visibly unresolved when absent.

### Task 7: Verify the Product and Submission Surface

**Files:**
- Modify as evidence requires: `README.md`, `docs/submission_progress.md`, `DEVLOG.md`
- Generate ignored browser evidence under: `output/verification/`

- [ ] **Step 1: Run full automated tests**

Run `E:\anaconda\envs\traceguard\python.exe -m pytest tests -q` and record the exact result.

- [ ] **Step 2: Start the server and verify the actual browser workflow**

Use the local Playwright workflow to verify desktop and narrow-screen upload, loading, success, and error states. Confirm `/api/v1/health`, `/`, and `/api/v1/analyze` against the real checkpoint.

- [ ] **Step 3: Audit deliverables**

Check README commands, source package boundaries, report placeholders, originality statement status, required forms, model/data license gaps, and the final Word synchronization path. Do not sign, stamp, upload, or submit on the user's behalf without explicit authority.

### Task 8: Stop Only at the Defined Boundary

**Files:**
- Modify: `DEVLOG.md`
- Modify: `docs/submission_progress.md`

- [ ] **Step 1: Produce the dependency matrix**

Separate remaining items into:

```text
Zhu Yishuai complete
Zhang Xiao missing: ablation raw table, baseline/source balanced originals, training/eval scripts
He Jie missing: CASIA localization metrics, evidence consistency analysis, final case figures
User confirmation required: signatures, stamp, liaison uploader, final submission action
```

- [ ] **Step 2: Verify no independently actionable task remains**

Re-read `docs/project_plan.md`, `docs/submission_progress.md`, `DEVLOG.md`, the contest guide, report source, README, tests, and generated evidence. Stop only when every remaining item belongs to another teammate or requires user authority/information.
