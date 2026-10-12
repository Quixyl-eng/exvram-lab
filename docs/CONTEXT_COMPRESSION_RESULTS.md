# Context compression results

Status: **no new measurement**. Quality for every compression candidate is
`NOT_VERIFIED`. The P5 and P6 numbers below are older measurements, cited so
the extrapolation has a source. They are not 16k, 32k, or 64k results.

P9 is still the active phase. This track does not block it and does not
change `recipes/rtx5060_8gb_qwen38_27b_8k.yaml`.

## Quality rule, fixed before any compression run

`classify_quality` in `src/exvram/context_compression.py` implements this.

- Orientation, not a pass: a 2 percentage-point drop in success rate.
- `ZERO_QUALITY_LOSS` only when there are at least 2400 paired trials, no
  miss on names, numbers, instructions, code, citations, or facts at the
  start, middle, and end, and the upper uncertainty bound on
  (uncompressed − compressed) is ≤ 0. A tie inside that noise is
  `MEASURED_DELTA`, not zero loss.
- Fewer trials, any critical miss, or a drop that the bound cannot clear is
  `MEASURED_DELTA` once numbers exist, and `NOT_VERIFIED` when they do not.
- A failed or unverified compression steps back toward q4_0, then off.
  `relax_after_quality` does that. It does not drop tokens.

Suites, when a run is eventually allowed: reasoning, coding, factual
retrieval in a long document, exact numbers and quotes, instruction
following, long-context retrieval, multi-hop reasoning, and position
retention. The same items are scored with compression off. Configured
context and occupied context are recorded separately.

## What was already measured

From [KV_TRADEOFF.md](KV_TRADEOFF.md), one RTX 5060, IQ2_XXS, quality
`NOT_RUN`:

| KV | Configured context | KV MiB | Recurrent state MiB | Peak VRAM MiB | Decode tok/s |
|---|---:|---:|---:|---:|---:|
| q4_0 | 8192 | 144 | 149.62 | 7641 | 29.04 |
| q8_0 | 8192 | 272 | 149.62 | 7687 | 18.74 |
| f16 | 8192 | 512 | 149.62 | 7764 | 19.60 |

Occupied 8192 q4_0, five runs, median decode 30.10 tok/s, peak 7767 MiB,
median TTFT about 244 s. That is the production baseline. It is not a
compression improvement.

The planner extrapolates only the KV term and holds the recurrent state at
149.62 MiB. Rows other than q4_0 at 8192 are `ESTIMATED`. Speed and TTFT
in those rows are null.

| Context | q4_0 peak | q4_0 fits 8151 | q8_0 fits | f16 fits |
|---|---:|---|---|---|
| 8192 | 7641 measured | yes | yes, measured 7687 | yes, measured 7764 |
| 16384 | estimated | see `plan-context-compression` | estimated | estimated |
| 32768 | estimated | estimated | estimated | estimated |
| 65536 | estimated above the card for q4_0 | no | no | no |

`python -m exvram plan-context-compression` prints the matrix. Do not paste
an estimated peak into a results JSONL as if the GPU had been sampled.

## Answers

1. **Best OSS method.** None. No candidate was run for this track. The only
   KV representations with ExVRAM timings on this GPU are llama.cpp q4_0,
   q8_0, and f16, and only through configured 8192. q4_0 is the baseline
   because it was the fastest and smallest in that speed table, not because
   quality was shown to match f16.
2. **VRAM reduction versus uncompressed KV.** f16 is the uncompressed
   attention cache in that table. q4_0 used 144 MiB instead of 512 MiB at
   c8192. Peak fell from 7764 to 7641 MiB. That is a cache-buffer change,
   not a 32k result, and quality is `NOT_RUN`.
3. **Longest context actually checked.** Occupied 8192 tokens on q4_0.
   16k, 32k, and 64k were not loaded.
4. **Accuracy.** `NOT_VERIFIED`. There is no paired score against
   uncompressed context.
5. **Prefill and TTFT.** No new prefill. The occupied-8192 q4_0 median TTFT
   remains about 244 s. Compression did not change it.
6. **Decode.** No new decode. The baseline median is 30.10 tok/s. q8_0 and
   f16 were slower in the single P5 c8192 rows. That is not a quality
   comparison.
7. **Lost names, numbers, code, or citations.** `NOT_VERIFIED`. The planner
   refuses to drop tokens in order to fit.
8. **Windows load.** Not remeasured. The occupied-8192 run already reached
   99–100% GPU and left little free VRAM. See
   [SYSTEM_RESOURCE_SAFETY.md](SYSTEM_RESOURCE_SAFETY.md).
9. **Background use without a hitch.** Not promised. Interactive mode
   refuses a start when free VRAM is under 512 MiB or another GPU
   application is busy. The 27B baseline itself peaks near 7767 of 8151 MiB,
   so it cannot share the card quietly with a game.
10. **Advantage over q4_0 KV.** No measured advantage. q4_0 is the baseline.
    Turning compression on does not replace it until a `ZERO_QUALITY_LOSS`
    row exists, and none does.
11. **Advantage over Ternary-Bonsai.** None measured. Ternary-Bonsai is a
    weight file, not a KV method, and it has no ExVRAM run.
12. **Ship it in ExVRAM Runtime.** No. Keep it off. The switch is
    `plan-context-compression` without `--enable`, which stays on q4_0.

## Reproduce the plan, CPU only

```bash
python -m exvram plan-context-compression --task code --context 65536 --mode INTERACTIVE --enable
```

The command does not load a GGUF. A GPU run still requires the operator to
pass BENCHMARK mode and the resource guard's exclusive permission, on a
machine that is not already busy.
