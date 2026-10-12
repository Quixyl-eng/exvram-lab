# Contributing to ExVRAM Lab

ExVRAM Lab is an Apache-2.0 research project. External contributors are welcome. The active phase is P9: a quality gate, a comparison against a higher-quality reference and Ternary-Bonsai where that comparison is actually run, the Coletti minimal-refusal quant, and separate refusal and over-refusal rates. See [docs/ROADMAP.md](docs/ROADMAP.md).

This repository does not vendor model weights, llama.cpp, or CUDA kernels. A pull request that adds weights, a new inference engine, a first-party CUDA kernel, or an unmeasured tokens/second number will not be merged.

## First session, no GPU

Python 3.10 or newer is enough. Torch and an NVIDIA driver are optional.

```bash
git clone https://github.com/ExVRAM/exvram-lab.git
cd exvram-lab
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
exvram validate-environment
exvram list-adapters
exvram run-synthetic-microbenchmark --output results/synthetic.json
python -m unittest discover -s tests -q
python -m compileall -q src tests
ruff check .
```

`validate-environment` reports the host and whether CUDA is visible. Missing CUDA is a normal result. `run-synthetic-microbenchmark` writes `synthetic: true` and a CPU checksum. `pseudo_operations_per_second` is not tokens/second and not a VRAM measurement. `results/` is gitignored.

CPU unit tests live in `tests/`. GPU-only tests skip, or record the backend as unavailable, when CUDA is absent. Do not add a fallback that invents a GPU timing.

## GPU benchmarks

Read [docs/SAFE_WORKFLOW.md](docs/SAFE_WORKFLOW.md) and [docs/GPU_ENVIRONMENT.md](docs/GPU_ENVIRONMENT.md) first. Keep weights and runtime binaries outside the git tree.

Two different GPU entry points already exist:

- `exvram run-layer-benchmark` times CUDA kernels only when a CUDA build of Torch is installed in an isolated environment such as `.venv-gpu`. Without CUDA it must record the backend as unavailable.
- `benchmark/run_p5_context_scaling.py` and `benchmark/run_p6_reproducibility.py` call an external `llama-server` binary. They do not download llama.cpp or a GGUF.

A full-model reproduction uses the published recipe, not a new command. On Linux, from an activated virtual environment:

```bash
python benchmark/run_p6_reproducibility.py \
  --server /path/to/llama-server \
  --model /path/to/Qwen3.8-27B-UD-IQ2_XXS.gguf \
  --contexts 8192 \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --decode-tokens 256 \
  --output experiments/results/p6_repro_other_gpu.jsonl \
  --work-dir work/p6_repro_other_gpu
```

Match the flags in `recipes/rtx5060_8gb_qwen38_27b_8k.yaml` and [docs/P6_REPRODUCIBILITY.md](docs/P6_REPRODUCIBILITY.md). Record the GPU you actually used. Do not copy the RTX 5060 tok/s into a row for a different card. Quality stays `NOT_RUN` until [docs/P9_EVAL_PROTOCOL.md](docs/P9_EVAL_PROTOCOL.md) is executed.

P9 quality:

```bash
python benchmark/run_p9_quality.py --help
```

The protocol id is `p9-2026-10-02-1`. A dry run checks the sample counts and does not score a model. Generating scores requires the locked IQ2 artifact, `llama-server`, and the datasets the runner fetches into `work/p9/datasets` (gitignored). If the BF16 reference does not fit in host RAM, write `REFERENCE_KIND=UNAVAILABLE`. Do not label another model as `REFERENCE_BF16`.

## Add an inference backend

Backends are boundaries around existing projects. Kernels stay upstream.

1. Add `adapters/<name>/README.md` stating the upstream URL, license, what is not copied, and how availability is detected.
2. Register an `ExternalAdapter` in `src/exvram/adapters/registry.py`. Set `import_names` or `executable_names`. Set `copied_code` so the plan reports that no source was vendored.
3. Point `plan()` at the existing experiment config. The default plan status is `integration_only`.
4. Extend `tests/correctness/test_adapters.py` so a missing install is `unavailable` and the command builder does not download a model.
5. Run `exvram list-adapters` and the CPU unit tests.

Marlin and FlashInfer are named in the README ecosystem list and do not have adapter directories yet. That is a documentation task, not permission to vendor their code.

## Reproduce an existing experiment

1. Pick a measured document, for example [docs/P6_FINAL_RESULT.md](docs/P6_FINAL_RESULT.md) or [docs/P1_REAL_GPU_RESULTS.md](docs/P1_REAL_GPU_RESULTS.md).
2. Use the recipe, manifest, and runner named there. Pinned llama.cpp build for the occupied-8192 result is b10982, commit `fc82583e6`.
3. Write a new JSONL row. Do not edit historical rows so that a past RTX 5060 number looks like your machine.
4. Fill [docs/CONTRIBUTOR_RESULT.md](docs/CONTRIBUTOR_RESULT.md). `MEASURED` and `ESTIMATED` stay separate. Memory-planner output is `ESTIMATED`.

## Propose a new research method

Open an issue before writing code. Ready-to-file tasks are listed in [docs/CONTRIBUTOR_ISSUES.md](docs/CONTRIBUTOR_ISSUES.md). The proposal needs:

- the existing open-source method it is compared with
- the metric (quality, VRAM, decode, prefill, refusal) and the hardware
- why an adapter around an existing project is not enough

P8 1-bit work is frozen on `experiment/p8-low-bit` and does not block P9. A custom CUDA or Triton kernel waits on a named measured gap. A new inference engine, a Rust rewrite, and a weights commit are out of scope.

## Tests and review

Before opening a pull request:

```bash
ruff check .
python -m unittest discover -s tests -q
python -m compileall -q src tests
git diff --check
```

Confirm `git status` shows no `*.gguf`, `*.safetensors`, `.env`, checkpoints, or host paths with usernames. The pull request template asks for the evidence class and the commands you ran.

Discussion happens in English in GitHub issues and pull requests. Research claims stay attached to a command and a record.
