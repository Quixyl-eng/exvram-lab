# Security policy

ExVRAM Lab is a research repository. It does not ship model weights and it does not run a hosted inference service.

## Report a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/ExVRAM/exvram-lab/security/advisories/new).

Include the branch, the file, and a way to reproduce the issue without sending credentials or private model files. A maintainer will answer on the advisory.

## In scope

- Accidental secrets, tokens, or private keys in the tree or in history on `main`
- Path handling that writes outside the working directory the user chose
- A benchmark runner that downloads or executes an unpinned binary without an explicit user path

## Out of scope

- Model refusal behavior, jailbreak prompts, and quality scores. Those are research results under [docs/P9_EVAL_PROTOCOL.md](docs/P9_EVAL_PROTOCOL.md), not vulnerabilities in this repository.
- Vulnerabilities in llama.cpp, PyTorch, or another upstream the adapter only names. Report those upstream.
- Missing GPU results. A machine without CUDA is a supported configuration.

Do not open a public issue that contains a live token, a private key, or a zero-day exploit.
