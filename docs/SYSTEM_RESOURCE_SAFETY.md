# System resource safety

Experimental launches go through `src/exvram/resource_guard.py`. The guard
decides. It does not close user programs, change power limits, or edit the
Windows pagefile.

## Modes

| Mode | When | Permission |
|---|---|---|
| `INTERACTIVE` | Someone is using the machine | Default. A heavy calibration waits |
| `BENCHMARK` | An exclusive measurement | `allow_exclusive` must be true. The CLI does not set that by itself |

`INTERACTIVE` defers when telemetry is missing, CPU use is at or above 85%,
GPU temperature is at or above 85°C, free RAM is under 1024 MiB, or commit
charge is at or above 90% of the limit. It pauses when `user_gpu_busy` is
set or GPU utilization is at or above 40%. It refuses when free VRAM is
under 512 MiB or the projected peak would cross that reserve.

`BENCHMARK` without the exclusive flag is a refusal. With the flag, a
proceed result still says that prefill can peg the GPU. That is not a claim
that the desktop stays smooth.

When several checks fire, the stricter action wins: `REFUSE`, then `PAUSE`,
then `DEFER`, then `PROCEED`. A missing telemetry sample does not erase an
exclusive-run refusal.

## What the 27B baseline already does

Occupied 8192 q4_0 peaked at 7767 MiB on an 8151 MiB RTX 5060, with GPU
utilization at 99–100%. Interactive mode cannot promise a hitch-free desktop
if a game or another GPU process is also resident. The honest response is
`REFUSE` or `PAUSE`, plus the unchanged q4_0 configuration or a shorter
context. The guard will not evict tokens and will not kill the other process.

Sampling on Windows should use the existing pieces: `nvidia-smi` or NVML for
the GPU, and `GlobalMemoryStatusEx` for RAM and commit. The parser
`parse_nvidia_smi_csv` accepts one CSV line
(`utilization.gpu`, `memory.used`, `memory.free`, `temperature.gpu`,
`power.draw`). Wiring a live collector is optional and must keep
`kills_processes` false.

CPU tests construct a `HostSnapshot` directly. They do not need a GPU.
