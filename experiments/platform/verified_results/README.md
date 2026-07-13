# Platform runtime smoke result

The verified summary records one short CUDA run against the unpacked working submission package.

```powershell
E:\aNB\envs\traceguard\python.exe experiments\platform\runtime_smoke.py `
  --endpoint http://127.0.0.1:8012/api/v1/analyze `
  --image tests\fixtures\006_biggan_00020.png `
  --requests 12 `
  --concurrency 3 `
  --timeout 60 `
  --output-dir output\experiments\platform_smoke_20260713
```

The per-request CSV remains in ignored local output because it contains repeated run detail. The tracked JSON keeps the environment, hashes, aggregate metrics, response contract and interpretation limit needed for report review.
