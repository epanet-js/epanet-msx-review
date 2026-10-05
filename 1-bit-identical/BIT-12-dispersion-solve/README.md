# BIT-12: Factor once, solve into the segments, keep coefficients and segment lists

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Dispersion |
| **Results** | <!-- results:BIT-12 -->Identical to 85a303d in all 14 runs (9 cases; step and solve mode at 1 and 8 threads, read mode on the output-heavy cases, and built without OpenMP)<!-- /results --> |
| **Files** | `msxdispersion.c` (+270 / -119 lines) |
| **Patch** | [`BIT-12.patch`](BIT-12.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-11 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

For each species that disperses, MSX solves dispersion at every quality step in three passes ([`msxqual.c` L1324-L1332](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1324-L1332)):

- `dispersion_pipe()` ([`msxdispersion.c` L82](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L82)) sets up, for each pipe whose Peclet number is below the limit, a tridiagonal system with one row per segment and one for each end. It solves it for three right-hand sides: the segments' current concentrations, a unit concentration at the downstream end, and a unit concentration at the upstream end. Each segment keeps its three responses.
- `solve_nodequal()` builds a sparse system for the junction concentrations from the responses of each pipe's end segments, and solves it.
- `segqual_update()` ([L409](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L409)) sets each segment's concentration from its three responses and the new concentrations of the pipe's two end nodes.

On KY8 about 1,100 of the 1,614 pipes pass the Peclet test, holding about 79,500 of the network's 84,300 segments (up to 335 in one pipe), and the three passes run 242 times in the 4-hour run. Timed inside the unpatched code at one thread, `dispersion_pipe()` took 1.01 s per run, `segqual_update()` 0.31 s and `solve_nodequal()` 0.02 s, of a run of about 10 s. Once the chemistry is fast (BIT-02 to BIT-08), these passes are a large part of what is left of the KY8 run.

Four kinds of work were redundant:

- **Three factorisations of one matrix.** `tridiag()` ([L591-L608](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L591-L608)) was called three times with the same matrix ([L214](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L214), [L236](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L236), [L256](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L256)), and each call repeated the forward elimination. That elimination is a chain of dependent divisions, so it runs at the latency of the divider: about 3.9 ns per row.
- **Three copy walks.** After each solve, a walk of the pipe's linked list copied the solution into the segments ([L221-L228](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L221-L228), [L243-L250](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L243-L250), [L263-L270](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L263-L270)). With the walk that built the system, each pipe's list was walked four times per species and step.
- **Hydraulics recomputed.** Each pipe's velocity, Reynolds number, friction factor (`pow(diam, 5)`, `sqrt`) and dispersion coefficient (`pow(Re/1000, -2.2)` or `exp`) were recomputed for every pipe, species and quality step ([L111-L156](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L111-L156)), although they depend only on the hydraulic state, which changes only at hydraulic steps (KY8 has a 1-hour hydraulic time step and a 60-second quality step).
- **A fifth list walk.** `segqual_update()` walked each dispersing pipe's linked list once more ([L443-L451](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L443-L451)), after the walk through all the other pipes. A linked-list walk cannot load a segment before it has loaded the one before it, so each segment no longer in cache cost a full memory access: about 13 ns per segment on KY8. The walk also summed two masses, `mass1` and `mass2`, that were never used.

## What the change does

1. **Factor once for the three right-hand sides.** A new `tridiag3()` does the forward elimination once, carrying the three right-hand sides through the same loop as three independent recurrences, then back-substitutes all three in one loop. The unit right-hand sides are written as the constants they were (`0.0`, and `1.0` in the boundary row). The three recurrences overlap in the processor, so three solves cost little more than one: 5.1 ns per row in a micro-benchmark, against 11.7 ns for three calls of `tridiag()`.

2. **Back-substitute straight into the segments.** The walk that builds the system records each segment's pointer in an array. The back substitution, which runs from the upstream end, stores the three responses (`hresponse`, `dresponse`, `uresponse`) directly in the segments, so the three copy walks are gone. Row 0, the downstream boundary, was computed but never read, and is no longer back-substituted.

3. **Keep each pipe's dispersion coefficient while its hydraulics are unchanged.** The computation moves unchanged into `linkhydraulics()`, which stores the velocity, Reynolds number and coefficient for each dispersing species and pipe, together with the flow, status and two end-node heads it used. They are reused while those four values compare equal. Entries start with a NaN flow, so the first use always computes. If the cache cannot be allocated, every step computes as before. This step gains least, about 2 % of `dispersion_pipe()`: on KY8 the hydraulic part fell from 0.019 s to 0.004 s per run.

4. **Keep each pipe's segment list between the dispersion passes.** The array of segment pointers from step 2 is kept per pipe (sized from the pipe's segment count, and doubled when needed), and `segqual_update()` loops over it instead of walking the linked list, so the loads of different segments overlap. The unused `mass1` and `mass2` sums are removed. If a pipe's array cannot be grown during a run, the out-of-memory flag is set and the step returns error 501, as when a new segment cannot be allocated.

Steps 1 and 4 carry most of the gain. When the steps were written, the dispersion code alone on KY8 at one thread went from 1.34 s to 0.99 s with step 1 and to 0.84 s with step 2, did not change measurably with step 3, and fell to 0.61 s with step 4, which took `segqual_update()` from 0.25 s to 0.08 s. On five more dispersion models (described below) the dispersion code alone became 2.1 to 2.6 times faster at one thread.

The extra memory is small: an array of segment pointers for each dispersing pipe (at least 32 entries, doubled as needed), 40 bytes per link and dispersing species for the coefficients, and two more per-thread solution arrays of the maximum segment count.

## Why the results are unchanged

**Step 1.** Each of the three solutions goes through the same operations on the same operands, in the same order, as in its own `tridiag()` call. The elimination coefficients (`gam`, `bet`) were computed three times, identically; now they are computed once. Where `tridiag()` read a zero or a one from the right-hand side, `tridiag3()` uses the constant: `0.0 - a[j] * y[j-1]` is the operation `r[j] - a[j] * y[j-1]` performs when `r[j]` is 0.0, and a compiler may not rewrite `0.0 - x` as `-x`, because the two differ when `x` is +0. The expressions keep the same shape, so a compiler that fuses multiply-adds fuses the same ones. This was also checked with fused multiply-add turned off (`-ffp-contract=off`), against the unpatched code built the same way.

**Step 2.** The same values, stored in a different place. The row-0 value that is no longer computed was never read.

**Step 3.** The values come from the same code with the same inputs. The other inputs (the pipe's diameter and length, the viscosity, the species' diffusivity or fixed coefficient) cannot change after `MSXopen`. Flows, statuses and heads are stored as the same single-precision values they are compared with, so the comparison is exact. A NaN never compares equal, so it is recomputed every time, as before. +0 and -0 compare equal, but the computation uses the flow only through its magnitude and the heads only through the magnitude of their difference, so both give the same result. Comparing the inputs, rather than watching the hydraulic time, also covers `MSXinit` and repeated runs. (One difference in a value that is never read: for a pipe without flow, the unpatched loop left `reynolds` at the previous pipe's value, where `linkhydraulics()` sets 0. Such a pipe fails the Peclet test before `reynolds` is read.)

**Step 4.** The same expression is applied to the same segments, in the same order; only how they are found changes. Between `dispersion_pipe()` and `segqual_update()` only `solve_nodequal()` runs, and it reads the pipes' end segments without changing any list. `mass1` and `mass2` were never read.

Of the benchmark cases only KY8 disperses, so when the change was written it was also checked on five more dispersion models: KY8 with a cheap first-order chlorine decay; KY8 with two dispersing species, one by molecular diffusivity and one with a fixed coefficient; Net3 with setpoint and mass boosters at junctions; Net3 with two dispersing species and one that does not disperse (RK5, Peclet limit 500); and Richmond with two setpoint boosters at junctions. Every concentration at every step was the same at 1 and 8 threads and without OpenMP, the binary output file and the report were the same, and so were the results with `-ffp-contract=off` against the unpatched code built the same way. Apart from BIT-11, nothing earlier in the series changes `msxdispersion.c`.

## Measured

Only KY8 uses dispersion among the benchmark cases; the others do not run this code, so their rows show noise.

<!-- measured:BIT-12 -->
Each table compares the series up to BIT-11 ("before") with BIT-12 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.01 | 1.01 | 1.00x | 0.478 | 0.487 | 0.98x | yes |
| Net6, chlorine bulk + wall | 0.768 | 0.801 | 0.96x | 0.659 | 0.686 | 0.96x | yes |
| KY8, chlorine + dispersion | 1.23 | 0.736 | 1.67x | 0.360 | 0.253 | 1.42x | yes |
| Richmond, bacterial regrowth | 0.727 | 0.735 | 0.99x | 0.254 | 0.228 | 1.11x | yes |
| Net3, chloramine decay | 1.28 | 1.29 | 0.99x | 0.456 | 0.437 | 1.04x | yes |
| Net3, arsenic adsorption | 0.441 | 0.443 | 1.00x | 0.173 | 0.187 | 0.92x | yes |
| MSX example (4 nodes) | 62.5 ms | 63.2 ms | 0.99x | 59.3 ms | 60.2 ms | 0.98x | yes |
| **Median** | | | **0.99x** | | | **0.98x** | |

To measure it yourself:

```sh
tools/try.py BIT-12 --against BIT-11
```
<!-- /measured -->

## Tried and not kept

Bit-identical, but no faster or not worth the complexity:

- *Skipping the elimination of the upstream right-hand side*, which is zero until the last row: no gain. The loop is bound by the latency of the chain through the pivot `bet`: with one, two and three right-hand sides it took 3.9, 4.6 and 5.1 ns per row.
- *Interleaving two pipes' tridiagonal solves*: the forward pass went from 5.0 to 3.2 ns per row, about 30 ms per KY8 run.
- *Walking eight pipes' segment lists in lockstep*: `dispersion_pipe()` on KY8 went from 0.547 s to 0.527 s, but it was slower when the segments were in cache (0.196 s to 0.213 s on the cheap KY8 model, 0.129 s to 0.141 s on the Richmond model).
- *Software prefetch* in the segment walk and in `segqual_update()`, and *local copies of pointers* in the loop that builds the system: within noise.
- *Reading the two node concentrations once per pipe* in `segqual_update()` instead of once per segment: no gain (0.252 s against 0.247 s).
- *Tuning `solve_nodequal()`*: it is serial, but takes 0.017 s per KY8 run in all.
- *One parallel region for all three passes*, which would save a fork and a join per species and step: it needs changes in `msxqual.c`, and was not done.

They would change results:

- *Multiplying by the reciprocal of each pivot* instead of dividing: it changes the last bits, and gains little (6.4 to 5.8 ns per row in a micro-benchmark), because the divider is pipelined and the cost is the chain of dependent operations. [NEAR-03](../../2-near-identical/NEAR-03-dispersion-pivot-chain/) takes the divisions off that chain (3.7 ns per row), as a near-identical change.
- *EPANET 2.2's `genmmd` ordering* for the junction matrix: a different elimination order changes the rounding. It could also save at most 0.6 %: after the bit-identical series, `solve_nodequal()` is about 0.011 s of a 0.68 s KY8 run, and the sparse solve about 1.2 % of its samples.
