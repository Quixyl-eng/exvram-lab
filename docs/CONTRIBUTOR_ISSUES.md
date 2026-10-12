# Issues ready for external contributors

These seven issues are specified so a maintainer can file them on GitHub. The automation token used to prepare this branch cannot create labels or issues on `ExVRAM/exvram-lab` (`Resource not accessible by integration`). Default labels that already exist are `good first issue`, `help wanted`, and `documentation`. Create `research`, `benchmark`, `quality`, and `GPU` before applying those names.

Do not mark a research run as `good first issue`. Two issues below are scoped for a first contribution. None of them ask for a new inference engine or a CUDA kernel.

## 1. Reproduce the occupied-8192 recipe on another GPU

Labels: `help wanted`, `benchmark`, `GPU`, `research`

**Problem.** The occupied-8192 UD-IQ2_XXS result is one RTX 5060 8 GB measurement: median decode 30.10 tok/s, q4_0 KV, 65/65 CUDA layers. Another card is not in the record, so a reader cannot tell which part of that number is the recipe and which part is that GPU.

**Expected result.** A `MEASURED` contributor record for a different NVIDIA GPU, using the same model file and the P6 runner. Quality may stay `NOT_RUN`. Do not paste the RTX 5060 rate into the new row.

**Done when.**

- The JSON file is under `experiments/results/` and follows [CONTRIBUTOR_RESULT.md](CONTRIBUTOR_RESULT.md).
- `model.sha256` matches the artifact that was loaded.
- `hardware.gpu` is not `NVIDIA GeForce RTX 5060`, or the notes say it is a second 5060 with a different driver and the raw log is distinct.
- `quality.status` is `NOT_RUN` unless P9 was actually run.
- The pull request does not edit the historical P6 JSONL.

**Files.** `recipes/rtx5060_8gb_qwen38_27b_8k.yaml`, `benchmark/run_p6_reproducibility.py`, `docs/P6_FINAL_RESULT.md`, `docs/CONTRIBUTOR_RESULT.md`.

**How to test.** Run the Linux command in [CONTRIBUTING.md](../CONTRIBUTING.md) with your `llama-server` and GGUF. Then `ruff check .` and `python -m unittest discover -s tests -q` if you touch Python.

**Equipment.** An NVIDIA GPU, the published Qwen3.8-27B UD-IQ2_XXS GGUF (not stored in git), and llama.cpp. 8 GB is the card the recipe was measured on. A smaller card should record the fit failure instead of a guessed tok/s.

## 2. Run the P9 quality protocol

Labels: `help wanted`, `quality`, `research`, `GPU`

**Problem.** Protocol `p9-2026-10-02-1` is locked and the base IQ2 quality gate is `NOT_RUN`. Speed from P6 is not a quality score. The BF16 reference does not fit in the 15.93 GiB host that wrote the protocol.

**Expected result.** Sample rows and a summary from `benchmark/run_p9_quality.py` for the locked base IQ2 artifact. If no same-protocol reference fits, `reference_kind` stays `UNAVAILABLE`. Do not invent `REFERENCE_BF16`.

**Done when.**

- The protocol id on every row is `p9-2026-10-02-1`.
- Decoding uses temperature 0 and seed 42.
- Category counts match `SAMPLE_COUNTS` in `src/exvram/p9_eval.py`.
- The summary does not claim `P9_SUCCESS` while the reference is unavailable.
- No model weights are added to git.

**Files.** `docs/P9_EVAL_PROTOCOL.md`, `docs/P9_BASE_QUALITY.md`, `benchmark/run_p9_quality.py`, `src/exvram/p9_eval.py`.

**How to test.** `python benchmark/run_p9_quality.py --dry-run` must print the protocol counts before any GPU job. The full run uses the server flags in the protocol doc.

**Equipment.** NVIDIA GPU that can hold the IQ2 checkpoint the way P6 did, llama-server build b10982 or a newer build called out in the notes, and enough disk for the gitignored datasets under `work/p9/datasets`. A CPU-only dry run is useful and is not a quality result.

## 3. Compare IQ2_XXS with Ternary-Bonsai

Labels: `help wanted`, `quality`, `research`, `benchmark`, `GPU`

**Problem.** Huihui Ternary-Bonsai PTQ1_0 and PQ2_0 are inventoried in [docs/UNCENSORED_OSS_MATRIX.md](UNCENSORED_OSS_MATRIX.md). File size is not a quality comparison. The ternary files need the PrismML llama.cpp fork, not stock llama.cpp. No ExVRAM quality or decode row exists for them.

**Expected result.** One `MEASURED` record for UD-IQ2_XXS and one for a named Ternary-Bonsai file, same prompts, same context target, each with its own SHA-256 and backend commit. Quality uses `p9-2026-10-02-1` or is explicitly `NOT_RUN`.

**Done when.**

- The two backends are named. A stock llama.cpp failure to load PTQ1_0 is recorded as a failed load, not as a low score.
- Neither row copies the other row's tok/s.
- The pull request does not declare a winner from speed alone.

**Files.** `docs/UNCENSORED_OSS_MATRIX.md`, `docs/UNCENSORED_PARETO.md`, `docs/P9_EVAL_PROTOCOL.md`, `docs/CONTRIBUTOR_RESULT.md`.

**How to test.** Load each file with the runtime its card documents. Record the command. Run the CPU unit tests if code changes.

**Equipment.** An NVIDIA GPU, both GGUF files, and the PrismML fork for the ternary file. This is not a first contribution.

## 4. Keep benchmark runners honest on a non-Windows host

Labels: `help wanted`, `benchmark`

**Problem.** The published full-model examples use `llama-server.exe` and PowerShell. A Linux contributor can already pass a binary path, but a missing binary should fail before any model read, with a message that points at CONTRIBUTING. That failure is not covered by a direct test of the P6 entry point.

**Expected result.** Invoking `benchmark/run_p6_reproducibility.py` with a server path that does not exist exits non-zero, does not create a `MEASURED` row, and the unit test checks that behavior without a GPU.

**Done when.**

- The new test passes under `python -m unittest discover -s tests -q`.
- An existing measured JSONL file is not modified.
- The README or `benchmark/README.md` shows the Linux command beside the PowerShell one.

**Files.** `benchmark/run_p6_reproducibility.py`, `benchmark/README.md`, `tests/correctness/test_full_model_runners.py`.

**How to test.** `python -m unittest tests.correctness.test_full_model_runners -q` and `ruff check .`.

**Equipment.** CPU only for the missing-binary test. A GPU is required only if you also attach a real reproduction, which belongs in issue 1.

## 5. Check one open-source quantizer that is still quality NOT_RUN

Labels: `help wanted`, `research`, `quality`

**Problem.** GemLite and HQQ have layer boundaries and, for GemLite, layer timings. Full-model quality on the Qwen3.8-27B checkpoint is not measured. P8 is frozen and must not grow a new kernel.

**Expected result.** Either a `MEASURED` quality note for an existing upstream quantizer on weights you can legally use, or a written `INCONCLUSIVE` that names the missing artifact and the command that failed. No quantizer source is copied into the tree.

**Done when.**

- The adapter README states `copied_code` is false.
- The result uses [CONTRIBUTOR_RESULT.md](CONTRIBUTOR_RESULT.md).
- P9's locked protocol is unchanged if you did not run it.

**Files.** `adapters/gemlite/README.md`, `adapters/hqq/README.md`, `docs/HQQ_GEMLITE_RESULTS.md`, `docs/P8` notes only as background.

**How to test.** CPU: `exvram list-adapters` and the adapter unit tests. GPU: only with an isolated `.venv-gpu` as in [docs/GPU_ENVIRONMENT.md](GPU_ENVIRONMENT.md).

**Equipment.** CPU is enough for an inconclusive boundary note. A measured layer or full model needs an NVIDIA GPU and the upstream package. Not a first issue.

## 6. Report CPU and RAM from validate-environment

Labels: `good first issue`, `documentation`, `help wanted`

**Problem.** Contributor records need CPU model and physical RAM. `detect_hardware()` records the OS string and Python version, and the GPU when CUDA or `nvidia-smi` answers. It does not record CPU or RAM, so every external result asks the author to type those by hand.

**Expected result.** `exvram validate-environment` prints CPU and physical RAM on Linux and Windows when the OS exposes them, and leaves the fields null with a warning when it does not. No fabricated GPU name.

**Done when.**

- A unit test covers the parser or the fallback without requiring a GPU.
- Missing CUDA still passes the existing hardware test.
- `ruff check .` and the unit tests pass.

**Files.** `src/exvram/hardware.py`, `src/exvram/cli.py`, `tests/correctness/test_hardware.py`.

**How to test.** `python -m unittest tests.correctness.test_hardware -q` on a machine with no NVIDIA driver.

**Equipment.** CPU only.

## 7. Add adapter notes for Marlin and FlashInfer

Labels: `good first issue`, `documentation`, `help wanted`

**Problem.** The README names Marlin and FlashInfer next to the backends that already have `adapters/<name>/README.md` and an `ExternalAdapter` entry. Those two have neither, so a new contributor cannot see the license boundary.

**Expected result.** Two short adapter notes and registry entries. Availability is `unavailable` until the upstream project is installed. No kernel source is copied. No tok/s is added.

**Done when.**

- `exvram list-adapters` lists both names.
- `tests/correctness/test_adapters.py` still passes, with coverage that a missing install is not reported as available.
- The notes link the upstream repositories and name their licenses.

**Files.** `src/exvram/adapters/registry.py`, `adapters/marlin/README.md`, `adapters/flashinfer/README.md`, `tests/correctness/test_adapters.py`.

**How to test.** `python -m unittest tests.correctness.test_adapters -q` and `exvram list-adapters`.

**Equipment.** CPU only.
