# Measurements

[All changes](../README.md)

The tables in this repository's READMEs are generated from the files here by [`tools/update-docs.py`](../tools/update-docs.py), and [`tools/run-all.sh`](../tools/run-all.sh) makes all of them again. <!-- machine -->Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG` with OpenMP, measured 2026-10-05<!-- /machine -->.

**These files come from one quick pass**, `QUICK=1 tools/run-all.sh`: for each build the faster of a checked run and one timed run (or the checked run alone, where noted), on a machine in use. Each file records the load average at its start and end, and each case's record the load at its own start and end. `tools/run-all.sh` without `QUICK=1` remakes them as the best of a checked run and 5 timed runs, interleaved (3 for the scaling and build-flavour runs), in about 6 hours.

| File | What it holds | Made by (`tools/run-all.sh` step) |
|---|---|---|
| `series.json` | The 7 main cases, step mode, 1 and 8 threads, for 85a303d, each fix on its own, and each bit-identical group added to the ones before it. The per-change tables come from here. | `series` |
| `near-series.json` | The same for the bit-identical series alone, each near-identical change on top of it on its own, and all three | `near` |
| `output-groups.json` | The output-heavy cases, solve and read mode, before and after BIT-14, BIT-15 and BIT-16 | `output-groups` |
| `headline-step.json`, `headline-solve.json` | 85a303d, `bit` and `near` at 1, 8 and all threads, in step and solve mode. The headline and per-case tables come from here. | `headline-step`, `headline-solve` |
| `output-headline.json` | The same on the output-heavy cases, solve and read mode | `output-headline` |
| `flavours.json` | Build options: no optimisation, no OpenMP | `flavours` |
| `scaling.json` | 1 to 10 threads | `scaling` |
| `verify-solve.json`, `verify-output.json`, `verify-noomp.json` | One checked run per build in the modes the timing runs do not cover: solve mode, the output-heavy cases in step and read mode, and every build without OpenMP | `verify-solve`, `verify-noomp` |
| `yardstick.json`, `yardstick.md` | The acceptance check of the near-identical changes: platform samples, converged reference, each change alone | `yardstick` |
| `threads.json` | The near-identical builds at 1, 8 and 10 threads and without OpenMP | `threads` |
| `real.json` | L-Town and the NW Model, 85a303d, `bit` and `near`, one checked run each at 1 and 8 threads | `real` |
| `yardstick-real.json`, `yardstick-real.md` | The acceptance check on L-Town and the NW Model, every sixth step | `yardstick-real` |
| `stress.json`, `yardstick-stress.json`, `yardstick-stress.md` | The stress cases (water age and tracers on BWSN2, full coupling on Net3): 85a303d, `bit` and `near`, one checked run each in step and solve mode at 1 and 8 threads; and the acceptance check on them | `stress`, `yardstick-stress` |
| `private.json` | The four utility models: labels, times, return codes, whether results were identical, and the load average; no sizes, memory or results (`tools/private-summary.py`) | `private` |
| `literature.json`, `literature.md`, `yardstick-literature.json`, `yardstick-literature.md` | The published reaction models on L-Town and dispersion on BWSN2 ([models/literature.md](../models/literature.md)): 85a303d, `bit` and `near`, one checked run each at 1 and 8 threads; and the acceptance check on them | `literature`, `yardstick-literature` |
| `literature-large-8.json`, `literature-large-1.json` | The same models on NW Model and BWSN2: 85a303d, `bit` and `near` on 8 threads; `bit` and `near` on 1 thread | `literature-large` |
| `private-literature-*.json` | The same models on the utility models, as `private.json` (labels, times, return codes, identical or not, load) | `private-literature` |
| `status.json` | The last check against upstream (`tools/check.py`), used to report what changed since | - |

Each run in the timing files records the case, the mode, the thread count, the build, the times of each phase in seconds (`open`, `H` for `MSXsolveH`, `Q` for the water quality, `report`, `close` and `total`), the number of steps, the peak memory (`rss_kb`) and, for the checked run, a hash of every concentration after every step (`hash`) and in solve mode the MD5 of the output file and the report.
