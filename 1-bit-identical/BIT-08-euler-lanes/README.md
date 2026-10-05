# BIT-08: Evaluate Euler rates for eight segments at once

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Chemistry (expression interpreter, Euler integrator) |
| **Results** | <!-- results:BIT-08 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `mathexpr.c`, `mathexpr.h`, `msxchem.c` (+400 / -0 lines) |
| **Patch** | [`BIT-08.patch`](BIT-08.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-07 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none beyond the series order: it runs [BIT-05](../BIT-05-interpreter-dispatch/)'s joined rate program, and gives identical segments their results with [BIT-06](../BIT-06-identical-segments-once/)'s copy |
| **Also fixes** | none |

## What was slow

With the Euler integrator, a segment's reaction is one evaluation of the rate program ([msxchem.c:572-581](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L572-L581)), and after [BIT-04](../BIT-04-pipe-invariant-cache/) and [BIT-05](../BIT-05-interpreter-dispatch/) that program is a few operations: five dispatches in the Net6 and KY8 chlorine model. The cost per segment was the work around it: copying the segment's concentrations into the array of values, dispatching each operation, checking the results for NaN and writing them back.

## What the change does

`mathexpr_runLanes()` runs a joined program for eight segments at once. The values are laid out as eight lanes per variable; every operation is applied to the eight lanes in a loop that the compiler vectorises, and the dispatch is paid once for the eight.

For a model integrated with Euler that has no equilibrium or formula species, and whose rate program needs a stack of fewer than 32 entries, `evalPipeReactions` hands each pipe with two or more segments to `evalPipeLanes()`. That function:

- puts the pipe's parameters, the constants, its hydraulic variables and BIT-04's cached values into every lane, once per pipe;
- gathers the species of up to eight segments, runs the program, then checks and updates each segment exactly as before and in the same order, including the reacted-mass sum;
- gives no lane to a segment that holds the same water as the one before it ([BIT-06](../BIT-06-identical-segments-once/)); such segments get its results afterwards, as in BIT-06.

Lanes left over at the end of a pipe repeat its last segment, and their results are not used. Each thread gets its own lane buffer, for Euler models only. On the benchmarks this applies to Net6, KY8, the output-heavy BWSN2 case and the chlorine runs on L-Town and the NW Model; RK5 and ROS2 models are unaffected.

## Why the results are unchanged

Each lane goes through the same operations, on the same operands, in the same order, as a single evaluation of the program would. Vectorising applies them side by side, never across lanes, and no value is combined across lanes. The maths functions (`exp`, `pow` and the others) are still called once per lane, as the same C library functions; GCC and Clang replace such calls with vector versions only under options that already allow results to change, such as `-ffast-math` or `-fveclib`. Each segment is then checked and updated by the same statements as before, in the same order, so the reacted-mass sum is added in the same order too.

Beyond the benchmark cases, the change was checked with and without OpenMP, with the `switch` dispatch used where labels-as-values are not available (built with Clang; MSVC itself was not tested), and on three torture models written for the lanes: Euler with every math function, with terms that produce NaN, and with hydraulic variables.

## Measured

<!-- measured:BIT-08 -->
Each table compares the series up to BIT-07 ("before") with BIT-08 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.13 | 1.14 | 0.99x | 0.647 | 0.607 | 1.07x | yes |
| Net6, chlorine bulk + wall | 0.875 | 0.842 | 1.04x | 0.820 | 0.829 | 0.99x | yes |
| KY8, chlorine + dispersion | 1.57 | 1.28 | 1.23x | 0.628 | 0.505 | 1.24x | yes |
| Richmond, bacterial regrowth | 0.798 | 0.795 | 1.00x | 0.305 | 0.305 | 1.00x | yes |
| Net3, chloramine decay | 1.27 | 1.26 | 1.01x | 0.397 | 0.403 | 0.99x | yes |
| Net3, arsenic adsorption | 0.494 | 0.500 | 0.99x | 0.219 | 0.242 | 0.91x | yes |
| MSX example (4 nodes) | 84.8 ms | 84.2 ms | 1.01x | 80.2 ms | 83.4 ms | 0.96x | yes |
| **Median** | | | **1.01x** | | | **0.99x** | |

To measure it yourself:

```sh
tools/try.py BIT-08 --against BIT-07
```
<!-- /measured -->

## Tried and not kept

- Four lanes gave the same times as eight; sixteen were 5 % slower.
- Lanes for every segment, without leaving out BIT-06's identical ones: no faster overall (one thread, Net6 0.546 s against 0.530 s, KY8 0.535 s against 0.546 s).
