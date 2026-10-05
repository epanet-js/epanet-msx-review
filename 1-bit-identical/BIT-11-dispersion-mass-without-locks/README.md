# BIT-11: Sum dispersed mass per link without locks, in link order

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Dispersion (multithreading) |
| **Results** | <!-- results:BIT-11 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxdispersion.c` (+19 / -12 lines) |
| **Patch** | [`BIT-11.patch`](BIT-11.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-10 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | The dispersed mass in the mass balance no longer changes with the number of threads or from run to run ([see below](#what-it-also-fixes)); concentrations were never affected |

## What was slow

For each species that disperses, MSX ends every quality step with three passes ([`msxqual.c` L1324-L1332](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1324-L1332)): `dispersion_pipe()` solves each pipe's tridiagonal system, `solve_nodequal()` solves for the junction concentrations, and `segqual_update()` sets each pipe's segments from the new node concentrations. The two pipe passes run in parallel with OpenMP.

`segqual_update()` also adds up the mass that dispersion carries into each pipe through its two ends, for the mass balance. Every thread added its pipes' contributions to one shared total, inside two `#pragma omp critical` sections per pipe ([`msxdispersion.c` L476-L481](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L476-L481) and [L504-L509](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L504-L509)). On KY8 about 1,100 pipes pass the Peclet test, so each call took the lock about 2,200 times.

In a profile of the unpatched code at 8 threads, 568 of the main thread's 741 samples in `segqual_update()` were waits for that lock. Timed inside the code, the function took 0.83 s per KY8 run at 8 threads, against 0.31 s with one thread. Once the chemistry was fast (BIT-02 to BIT-08), this, not the chemistry, is what kept the KY8 case from getting faster beyond 4 threads; the unpatched code, whose chemistry dominates, still gains up to 8 threads.

## What the change does

Each pipe writes its two contributions to its own two slots of a shared array, `massdisp`, allocated with the other dispersion arrays in `dispersion_open()`: slot 2k-1 for the downstream end of pipe k and slot 2k for the upstream end. A pipe that does not disperse, or has no segments, leaves zeros. After the parallel loop, one thread adds the slots in pipe order, downstream end first, which is the order a single thread used before.

An OpenMP `reduction(+: ...)` would also remove the lock, but it adds per-thread partial sums whose grouping depends on the number of threads, so the total would still change with the thread count.

Measured on its own when it was written, the change took `segqual_update()` on KY8 at 8 threads from 0.83 s to 0.21 s per run, and the whole dispersion code from 1.18 s to 0.66 s. At one thread it makes no difference.

## Why the results are unchanged

Concentrations are not touched. The loop computes every segment as before; only where each pipe's dispersed mass is added up has changed.

The total uses the same additions, in the same order, as the unpatched code on one thread. The only extra additions are the zeros of pipes that do not disperse. Adding +0.0 leaves any sum unchanged except -0.0, and a sum that starts at +0.0 can never become -0.0 in round-to-nearest arithmetic. So the dispersed mass now equals the unpatched one-thread value bit for bit, at any thread count.

This was checked at 1, 2, 4 and 8 threads, with repeated runs at 4 and 8, on five dispersion models on KY8, Net3 and Richmond that cover two dispersing species, a fixed dispersion coefficient, and setpoint and mass boosters at junctions (the models are described in [BIT-12](../BIT-12-dispersion-solve/#why-the-results-are-unchanged)).

### What it also fixes

Before, the additions happened in the order in which threads reached the lock, so the total changed in its last bits between runs and between thread counts. On a two-species KY8 model at 8 threads, one run in three gave `0x1.073144919391bp+4` instead of `0x1.073144919391cp+4`; on a Richmond model at 4 threads, `...eb5p+12` instead of `...eb6p+12`.

The total (`MSX.MassBalance.indisperse`) is used only by the mass balance: it is part of the mass inflow and of the mass ratio ([`msxqual.c` L446](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L446)), which the report prints to six significant figures ([`msxrpt.c` L377](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxrpt.c#L377) and [L387](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxrpt.c#L387)). A last-bit difference therefore rarely showed in the report. It never reached the concentrations or the binary output file.

## Measured

Only KY8 uses dispersion among the benchmark cases; the others do not run this code, so their rows show noise. The gain is at more than one thread.

<!-- measured:BIT-11 -->
Each table compares the series up to BIT-10 ("before") with BIT-11 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.00 | 1.01 | 1.00x | 0.516 | 0.478 | 1.08x | yes |
| Net6, chlorine bulk + wall | 0.764 | 0.768 | 0.99x | 0.671 | 0.659 | 1.02x | yes |
| KY8, chlorine + dispersion | 1.11 | 1.23 | 0.91x | 0.577 | 0.360 | 1.60x | yes |
| Richmond, bacterial regrowth | 0.737 | 0.727 | 1.01x | 0.240 | 0.254 | 0.95x | yes |
| Net3, chloramine decay | 1.29 | 1.28 | 1.01x | 0.442 | 0.456 | 0.97x | yes |
| Net3, arsenic adsorption | 0.456 | 0.441 | 1.03x | 0.193 | 0.173 | 1.12x | yes |
| MSX example (4 nodes) | 62.7 ms | 62.5 ms | 1.00x | 56.5 ms | 59.3 ms | 0.95x | yes |
| **Median** | | | **1.00x** | | | **1.02x** | |

To measure it yourself:

```sh
tools/try.py BIT-11 --against BIT-10
```
<!-- /measured -->

## Tried and not kept

None.
