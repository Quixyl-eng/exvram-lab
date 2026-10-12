# Contributor result template

Use this record when you publish a run that is not already one of the lab's historical JSONL files. The machine-readable blank is [experiments/results/contributor_result.example.json](../experiments/results/contributor_result.example.json). That file is an example. It is not a measurement. Do not cite its null fields as numbers.

The historical result contract in [schemas/result.schema.json](../schemas/result.schema.json) is unchanged. Full-model runners keep writing that shape. This template is the checklist a reviewer applies to a new external result.

## Evidence class

| Class | When to use it | Tokens/second |
|---|---|---|
| `MEASURED` | You ran the command on the hardware in the record | Fill only the rates and the peak VRAM you observed. Leave a field null if that probe failed, and say so in `notes` |
| `ESTIMATED` | Memory planner, file size, or a fit calculation | `decode_tokens_per_second`, `prefill_tokens_per_second`, and `peak_vram_mib` stay null |

`synthetic: true` is only for the CPU workflow checksum. A synthetic record is not `MEASURED` model inference.

## Required fields

| Field | Meaning |
|---|---|
| `hardware.gpu` | Device name from `nvidia-smi` or the toolkit |
| `hardware.vram_mib` | Total VRAM, MiB |
| `hardware.cpu` | CPU model |
| `hardware.ram_mib` | Physical RAM, MiB |
| `hardware.os` | Operating system and version |
| `model.id` | Model id, not a local path |
| `model.sha256` | SHA-256 of the file you loaded. Required for `MEASURED` |
| `model.quantization` | Quant name, for example `UD-IQ2_XXS` |
| `runtime.backend` | `llamacpp`, `exllamav3`, `ollama`, or another registered adapter |
| `runtime.backend_commit` | Upstream revision you executed |
| `runtime.context_tokens` | Configured context |
| `runtime.kv` | K/V cache types |
| `runtime.command` | The command a reviewer can re-run, with paths replaced by placeholders |
| `metrics.decode_tokens_per_second` | Decode rate, or null |
| `metrics.prefill_tokens_per_second` | Prefill rate, or null |
| `metrics.peak_vram_mib` | Peak VRAM, or null |
| `quality.status` | `NOT_RUN`, `PASS`, `FAIL`, or `INCONCLUSIVE` |
| `quality.protocol` | For P9, `p9-2026-10-02-1`, otherwise null |
| `quality.summary` | What was scored, or why it was not scored |

A `MEASURED` row still sets `quality.status` to `NOT_RUN` when the speed run did not execute the quality protocol. Throughput is not a quality score.

Copy the example, replace the nulls you actually observed, and add the JSON file under `experiments/results/` with a name that includes the GPU and the phase. Keep host usernames and absolute paths out of the file.
