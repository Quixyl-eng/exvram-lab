## Summary

<!-- What changed, and which phase it belongs to. P9 is the active phase. -->

## Evidence

- [ ] No new tokens/second or quality number
- [ ] `MEASURED` result attached (command, SHA-256, hardware)
- [ ] `ESTIMATED` only (planner or file size). Speed fields are null
- [ ] Documentation or test only

GPU used, if any:

## Tests

```text
ruff check .
python -m unittest discover -s tests -q
python -m compileall -q src tests
```

## Scope check

- [ ] No model weights, checkpoints, or `.env` files
- [ ] No vendored CUDA kernel or new inference engine
- [ ] Historical JSONL rows are unchanged
- [ ] `git diff --check` is clean
