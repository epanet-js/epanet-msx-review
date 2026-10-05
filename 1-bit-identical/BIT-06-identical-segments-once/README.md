# BIT-06: React a pipe's identical segments once

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Chemistry (pipe reactions) |
| **Results** | <!-- results:BIT-06 -->Identical to 85a303d in all 14 runs (9 cases; step and solve mode at 1 and 8 threads, read mode on the output-heavy cases, and built without OpenMP)<!-- /results --> |
| **Files** | `msxchem.c` (+130 / -12 lines) |
| **Patch** | [`BIT-06.patch`](BIT-06.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-05 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

At the start of a run every pipe is cut into 100 segments with the same concentrations ([msxqual.c:773-776](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L773-L776)), and many of them stay identical. A segment changes only through its own reactions until it leaves the pipe, and those reactions are the same in every segment that holds the same water in the same pipe. Water entering at the upstream end is merged into the last segment when its concentrations are within the species' tolerances ([msxqual.c:1371](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1371)); otherwise it starts a new segment. Yet `evalPipeReactions` integrated every segment on its own, at every step ([msxchem.c:548](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L548)).

An instrumented build counted the segment-steps whose concentrations and integration step are bit for bit those of the segment reacted just before, its downstream neighbour:

| Case | Segment-steps that repeat the one before |
|---|---:|
| BWSN2, two-source chlorine | 96.3 % |
| Richmond, bacterial regrowth | 79.9 % |
| Net6, chlorine bulk + wall | 64.0 % |
| Net3, chloramine decay | 25.2 % |
| Net3, arsenic adsorption | 20.3 % |
| KY8, chlorine + dispersion | 13.2 % |
| MSX example (4 nodes) | 12.9 % |

BWSN2's chemistry is cheap, but its 14,822 pipes start with about 1.5 million segments, so nearly all of its reaction time went on repeats. On BWSN2 this change gives the largest gain of any group in the series.

## What the change does

Before reacting a segment, `evalPipeReactions` counts the consecutive segments upstream of it that hold the same water. The test, `isSameWater()`, is strict: the integration step `hstep` and every species concentration `c[m]` must be equal bit for bit. They are compared as 64-bit integers, because `memcmp` here cost 11 % of the BWSN2 run.

After the segment is reacted, those segments are given its results instead of being integrated:

- its concentrations after the reactions, which go into the reacted-mass total;
- its concentrations after the equilibria and formulas that follow;
- its integration step.

The reacted mass is still added segment by segment, each with its own volume, in the same order, by one function used on both paths (the original loop, moved unchanged). Euler, RK5 and ROS2 are all covered, with or without equilibrium and formula species. Tanks are not: they hold one segment, or a few.

## Why the results are unchanged

Same water, same pipe, same reactions: same bits. Within one pipe and one time step, the chemistry of a segment depends only on its concentrations, its integration step, and the pipe's parameters, the constants and the pipe's hydraulic variables (`Av`, `U`, `Re` and the others are per pipe; a segment's volume enters only the reacted-mass total). Every evaluation starts from a fresh copy of the segment's concentrations, so nothing carries over from the segment before. The same inputs through the same code give the same bits, so the copy is exactly what integrating the segment would have produced. Zero concentrations of different signs (+0 and -0) compare unequal as integers, so such segments are simply integrated as before.

Errors are unchanged too: the segment that is integrated is always the first of its run, the one the unpatched code integrated first.

Beyond the benchmark cases, the change was checked at 1 and 8 threads and without OpenMP, on the output-heavy cases, on the six torture models of [BIT-02](../BIT-02-terms-evaluated-once/#why-the-results-are-unchanged) (Euler, RK5 and ROS2, each with full and no coupling), and on two models with nonlinear equilibria.

## Measured

<!-- measured:BIT-06 -->
Each table compares the series up to BIT-05 ("before") with BIT-06 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 6.43 | 1.17 | 5.49x | 2.05 | 0.609 | 3.37x | yes |
| Net6, chlorine bulk + wall | 0.927 | 0.842 | 1.10x | 0.892 | 0.821 | 1.09x | yes |
| KY8, chlorine + dispersion | 1.40 | 1.48 | 0.94x | 0.568 | 0.623 | 0.91x | yes |
| Richmond, bacterial regrowth | 3.02 | 0.802 | 3.77x | 0.816 | 0.345 | 2.36x | yes |
| Net3, chloramine decay | 1.79 | 1.34 | 1.34x | 0.529 | 0.421 | 1.26x | yes |
| Net3, arsenic adsorption | 0.578 | 0.504 | 1.15x | 0.261 | 0.232 | 1.12x | yes |
| MSX example (4 nodes) | 91.8 ms | 85.0 ms | 1.08x | 85.7 ms | 84.6 ms | 1.01x | yes |
| **Median** | | | **1.15x** | | | **1.12x** | |

To measure it yourself:

```sh
tools/try.py BIT-06 --against BIT-05
```
<!-- /measured -->

## Tried and not kept

- Fewer initial segments, or merging segments more eagerly: this would remove much of the same work, but it changes the results.
- The same for tanks: a tank holds one segment or a few, so there is little to share.
- Copying the results to the identical segments more cheaply: no measurable gain.
