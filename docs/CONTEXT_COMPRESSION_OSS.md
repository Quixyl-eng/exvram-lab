# Context compression: open-source survey

Status: **survey only**. No method below was executed for this note. No new
tokens/second, VRAM, or quality figure is a measurement. The production
Qwen3.8-27B recipe stays UD-IQ2_XXS + q4_0 KV on llama.cpp b10982
(`fc82583e6`). P9 is unchanged.

Checked on 2026-10-12 from each project's GitHub license metadata and, for
llama.cpp, from that pinned source file. "License not stated" means the
repository API returned no SPDX license. Those trees are not cleared to copy.

## Three different technologies

| Family | What it changes | What it does not do |
|---|---|---|
| A. KV compression | Bytes per cached key/value element | It does not decide which tokens matter |
| B. Context selection | Which tokens keep a cache slot | It can drop a name, a number, or a line of code |
| C. Semantic compression | The text itself, before the model sees it | It is not a KV layout and cannot be scored as one |

A smaller KV buffer is not a substitute for retrieval, and a shortened prompt
is not a substitute for a quantized cache. The hybrid Qwen3.8 trunk makes
this sharper: P5 measured a recurrent-state buffer of 149.62 MiB at both
c2048 and c8192, separate from the KV buffer (`kv_unified = false`). A method
that only quantizes attention KV does not shrink that state. If the state
grows at 32k or 64k, a KV-only estimate is too small.

The pinned llama.cpp binary's `common/arg.cpp` contains `cache-type-k`,
`q4_0`, `iq4_nl`, and `flash-attn`. It does not contain the strings `turbo`
or `hadamard`. Stock KV types already measured in this lab are q4_0, q8_0,
and f16. See [KV_TRADEOFF.md](KV_TRADEOFF.md).

## Projects

| Project | Family | License seen | Windows | SM120 | Qwen3.8 hybrid | Role here |
|---|---|---|---|---|---|---|
| llama.cpp b10982 KV types | A | MIT | Already used for the baseline | Measured on this RTX 5060 for q4_0, q8_0, f16 | The GGUF path that produced the 65/65 runs | Only family with ExVRAM numbers. Quality `NOT_RUN` |
| llama.cpp Hadamard / TurboQuant KV, newer than b10982 | A | MIT for llama.cpp. The paper is not code | Not this pin | `NOT_VERIFIED` on SM120 | `NOT_VERIFIED`. Must not assume the recurrent state is attention KV | Next KV candidate only after the pin is upgraded and the strings exist in that build |
| [TheTom/turboquant_plus](https://github.com/TheTom/turboquant_plus) | A | Apache-2.0 | PyTorch / vLLM notes, not this runtime | `NOT_VERIFIED` | Hugging Face cache path. Hybrid GDN is `NOT_VERIFIED` | Reference. Upstream claims are not ExVRAM results. "Zero accuracy loss" in a README is not `ZERO_QUALITY_LOSS` |
| [hackimov/turboquant-kv](https://github.com/hackimov/turboquant-kv) | A | Apache-2.0 | Documents a Windows venv and `triton-windows` | `NOT_VERIFIED` | `NOT_VERIFIED` | Same paper, different tree. Do not vendor |
| [jy-yuan/KIVI](https://github.com/jy-yuan/KIVI) | A | MIT | Transformers research code | `NOT_VERIFIED` | README models are Llama, Falcon, Mistral | 2-bit asymmetric KV. Not a drop-in for the GGUF runtime |
| [SqueezeAILab/KVQuant](https://github.com/SqueezeAILab/KVQuant) | A | Not stated | Research CUDA tree | `NOT_VERIFIED` | Not stated | No license file was published in the API. Do not copy |
| [FasterDecoding/SnapKV](https://github.com/FasterDecoding/SnapKV) | B | Apache-2.0 | Transformers monkeypatch | `NOT_VERIFIED` | README: Llama, Mistral, Mixtral | Drops KV after an observation window. Can lose a fact outside that window |
| [Zefan-Cai/PyramidKV](https://github.com/Zefan-Cai/PyramidKV) | B | MIT, via KVCache-Factory | Research scripts | `NOT_VERIFIED` | Llama / Mistral in the factory notes | Layer budgets. Still selection, not a denser KV |
| [mit-han-lab/streaming-llm](https://github.com/mit-han-lab/streaming-llm) | B | MIT | Research code, last push 2024-07-11 | `NOT_VERIFIED` | Attention sinks plus a sliding window | Unbounded streams by forgetting the middle. Not acceptable until position checks pass |
| [FMInference/H2O](https://github.com/FMInference/H2O) | B | Not stated | Research code | `NOT_VERIFIED` | Not stated | Heavy-hitter eviction. No license file was found. Do not copy |
| [mit-han-lab/Quest](https://github.com/mit-han-lab/Quest) | B | MIT | Research code | `NOT_VERIFIED` | Query-aware page selection for standard attention | Can miss a page that does not match the query. `NOT_VERIFIED` here |
| [microsoft/LLMLingua](https://github.com/microsoft/LLMLingua) | C | MIT | Python, last push 2026-09-10 | Not a CUDA kernel | Prompt compression with a smaller LM | Changes the text. It is not a KV result and not a quality result until the same items are scored |
| [flashinfer-ai/flashinfer](https://github.com/flashinfer-ai/flashinfer) | Kernel library, not a policy | Apache-2.0 | Actively maintained | `NOT_VERIFIED` in this lab | Can host attention kernels. It does not choose a Qwen hybrid cache | Do not vendor. A kernel is not a compression method |

Ternary-Bonsai is a weight quant, listed in [UNCENSORED_OSS_MATRIX.md](UNCENSORED_OSS_MATRIX.md).
It is not a context-compression method. No ExVRAM decode or quality row
exists for it. It is not an alternative to q4_0 KV.

## What is allowed to run next

1. The existing llama.cpp KV types, on the existing runner, at a context the
   resource guard accepts. Quality stays on protocol `p9-2026-10-02-1` or
   `NOT_VERIFIED`.
2. A newer llama.cpp only after its build is shown to contain the KV feature
   and to load this GGUF on SM120. That is a new binary, not a silent swap
   of b10982.
3. Family B or C only as an explicit experiment with the critical checks in
   [CONTEXT_COMPRESSION_RESULTS.md](CONTEXT_COMPRESSION_RESULTS.md). The
   planner will not select them to save memory.

No first-party CUDA kernel. No fine-tune. No edit to the shipped weights.
