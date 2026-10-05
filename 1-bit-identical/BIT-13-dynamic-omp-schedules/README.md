# BIT-13: Hand pipes to threads dynamically in the reaction and dispersion loops

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Multithreading (chemistry and dispersion) |
| **Results** | <!-- results:BIT-13 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxchem.c`, `msxdispersion.c` (+8 / -4 lines) |
| **Patch** | [`BIT-13.patch`](BIT-13.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-12 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none outside the series; the argument for unchanged results uses [FIX-01](../../3-bug-fixes/FIX-01-reaction-loop-error-race/) and [BIT-11](../BIT-11-dispersion-mass-without-locks/), which come before it |
| **Also fixes** | none. The race on the reaction loop's error code is fixed on its own, by [FIX-01](../../3-bug-fixes/FIX-01-reaction-loop-error-race/) |

## What was slow

MSX runs three loops over pipes in parallel with OpenMP: the reaction loop in `MSXchem_react()` ([`msxchem.c` L284](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L284)) and the two pipe loops of the dispersion code, in `dispersion_pipe()` and `segqual_update()` ([`msxdispersion.c` L103](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L103) and [L426](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L426)). All three used OpenMP's default static schedule, which gives each thread one equal block of pipes. The work in those blocks is not equal:

- A pipe's work grows with its number of water-quality segments, which ranges from 1 to 335 on KY8; after [BIT-06](../BIT-06-identical-segments-once/), with the number of those segments whose water differs. In the dispersion loops, pipes that do not disperse cost almost nothing.
- Two of an M1 Pro's ten cores are slower efficiency cores, and a thread running there gets as many pipes as the others.

Threads that finish their block early wait at the end of the loop for the slowest. Modelled from the segment counts, the busiest thread in the dispersion loops had 1.14 to 1.18 times the mean work on KY8 at 8 threads, and 1.61 times on a Richmond model with dispersion.

On the unpatched chemistry this mattered little. It matters more once BIT-02 to BIT-08 have made each step's reaction loop short, so that the wait at its end is a larger share of it.

## What the change does

The reaction loop uses `schedule(dynamic, 2)` and both dispersion loops `schedule(dynamic, 8)`: a thread that finishes takes the next 2 (or 8) pipes.

The chunk of 2 for the reaction loop was chosen from this comparison, made at an earlier point in the work (with most of BIT-02 to BIT-05 applied and none of BIT-06 to BIT-12), with the schedule set through `OMP_SCHEDULE`. Quality time at 8 threads, seconds, fastest / median of 5 runs:

| Case | static | dynamic, 1 | dynamic, 2 | dynamic, 4 | guided |
| --- | ---: | ---: | ---: | ---: | ---: |
| Richmond, bacterial regrowth | 1.05 / 1.09 | 0.73 / 0.85 | 0.72 / 0.78 | 0.75 / 0.79 | 0.70 / 0.79 |
| BWSN2, two-source chlorine | 2.13 / 2.49 | 1.79 / 2.12 | 1.70 / 2.05 | 1.99 / 2.12 | 2.01 / 2.59 |
| Net3, chloramine decay | 0.88 / 1.19 | 0.70 / 0.96 | 0.66 / 0.77 | 0.72 / 0.84 | 0.74 / 0.84 |
| Net6, chlorine bulk + wall | 1.17 / 1.52 | 1.02 / 1.39 | 0.81 / 1.34 | 0.89 / 1.59 | 0.79 / 1.09 |

`schedule(dynamic, n)` has been part of OpenMP since version 1.0, so MSVC's OpenMP 2.0 supports it. At one thread the schedule makes no difference.

## Why the results are unchanged

The schedule decides only which thread does which pipe, and when. That cannot change a result as long as each pipe's arithmetic does not depend on the thread that does it, and nothing is combined across pipes in an order that depends on the schedule. Both hold:

- **Each pipe is computed the same way on any thread.** A pipe's computation reads its own segments, shared inputs that the loop does not change (hydraulics, constants, parameters, and in `segqual_update()` the node concentrations just solved for), and the thread's working arrays. The working arrays are filled for each pipe and segment before they are read, so what the thread did before does not matter. The caches added earlier in the series ([BIT-04](../BIT-04-pipe-invariant-cache/)'s invariants, [BIT-12](../BIT-12-dispersion-solve/)'s coefficients and segment lists) are kept per pipe, not per thread. The patch changes only the `#pragma omp for` lines and their comments.
- **Nothing is summed across pipes inside these loops.** The mass each pipe reacts is kept per pipe and added up in pipe order at the end of the run. The reaction loop's error code is merged by taking the largest ([FIX-01](../../3-bug-fixes/FIX-01-reaction-loop-error-race/)), which does not depend on order. The dispersed mass is written per pipe and summed in pipe order after the loop ([BIT-11](../BIT-11-dispersion-mass-without-locks/)). Those were the only two shared totals.

The unpatched code already gave the same concentrations at any thread count; the static schedule is one assignment of pipes to threads, and the dynamic schedule a different one in every run. Every benchmark case is checked after this group at 1 and 8 threads, in step and solve mode, and without OpenMP, and the whole series also at 10 threads. When the dispersion schedule was written, the five extra dispersion models of [BIT-12](../BIT-12-dispersion-solve/#why-the-results-are-unchanged) were also checked with it, at 1 and 8 threads and without OpenMP.

## Measured

The change can only matter with more than one thread: compare the 8-thread columns.

<!-- measured:BIT-13 -->
Each table compares the series up to BIT-12 ("before") with BIT-13 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.01 | 1.01 | 1.00x | 0.487 | 0.474 | 1.03x | yes |
| Net6, chlorine bulk + wall | 0.801 | 0.776 | 1.03x | 0.686 | 0.716 | 0.96x | yes |
| KY8, chlorine + dispersion | 0.736 | 0.750 | 0.98x | 0.253 | 0.242 | 1.05x | yes |
| Richmond, bacterial regrowth | 0.735 | 0.722 | 1.02x | 0.228 | 0.229 | 1.00x | yes |
| Net3, chloramine decay | 1.29 | 1.29 | 1.01x | 0.437 | 0.320 | 1.37x | yes |
| Net3, arsenic adsorption | 0.443 | 0.447 | 0.99x | 0.187 | 0.149 | 1.26x | yes |
| MSX example (4 nodes) | 63.2 ms | 63.4 ms | 1.00x | 60.2 ms | 66.4 ms | 0.91x | yes |
| **Median** | | | **1.00x** | | | **1.03x** | |

To measure it yourself:

```sh
tools/try.py BIT-13 --against BIT-12
```
<!-- /measured -->

## Tried and not kept

- *Other schedules for the reaction loop* (table above): chunks of 1 or 4 were a little slower than chunks of 2 on all four cases; `guided` was faster on Net6, about the same on Richmond, and slower on BWSN2 and Net3; chunks of 16 were poor on Net3, which has only 117 pipes.
- *`OMP_WAIT_POLICY=active`*, where threads spin between parallel loops instead of sleeping: mixed. With the patched code at 8 threads, KY8 went from 0.31 s to 0.18 s, but BWSN2 from 1.33 s to 1.75 s; with all 10 cores every case got slower (Net6 from 0.43 s to 1.34 s), because spinning threads compete with everything else on the machine. The default, passive, is the safer choice. It is an environment variable, so a user can still set it on a machine that does nothing else.
- *A minimum size for each parallel loop* (OpenMP's `if` clause), so that small loops run on one thread: what pays off depends on the machine and its load, so no single threshold works. For example, on a busy machine `segqual_update()` on a Richmond dispersion model took 0.068 s at 8 threads against 0.017 s at 1. [BIT-15](../BIT-15-link-averages-once/) does use one (1,000 links), for a loop that is cheap per link.
- *Fewer threads than cores*: not needed. OpenMP uses every core by default (10 on an M1 Pro, two of them efficiency cores), and with the dynamic schedules 8 and 10 threads give much the same times.
