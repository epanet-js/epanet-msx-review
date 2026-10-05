# NEAR-03: Dispersion: a tridiagonal solve without a chain of divisions

| | |
|---|---|
| **Category** | [Near-identical](../README.md): results change at the level of rounding, by less than the unpatched code's own results differ between platforms |
| **Area** | Dispersion |
| **Results** | <!-- results:NEAR-03 -->Differs from 85a303d in 2 of 14 runs, by rounding; every case passes the acceptance rule (see [the acceptance check](../README.md#the-acceptance-table))<!-- /results --> |
| **Files** | `msxdispersion.c` (+165 / -58 lines) |
| **Patch** | [`NEAR-03.patch`](NEAR-03.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-17, on its own: the other near-identical changes are not needed ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none beyond the bit-identical series: it replaces the pipe solve of [BIT-12](../../1-bit-identical/BIT-12-dispersion-solve/), and keeps BIT-12's `tridiag3()` as its fallback |
| **Also fixes** | none |

## What was slow

Only the KY8 case has dispersion (a `[DIFFUSIVITY]` section), and once the bit-identical series is applied, dispersion is about half of its run. For each dispersing pipe, species and step, `dispersion_pipe()` walks the pipe's segments from downstream to upstream to build a tridiagonal system, one row per segment plus one for each end, and solves it for three right-hand sides: the segments' concentrations, and a unit concentration at each end. [BIT-12](../../1-bit-identical/BIT-12-dispersion-solve/) factors the system once for all three.

Two chains of dependent operations set the pace:

- **The forward elimination.** Each row's pivot is β<sub>j</sub> = b<sub>j</sub> − a<sub>j</sub>·c<sub>j−1</sub>/β<sub>j−1</sub>, so every row waits for a division by the pivot before it (about 10 cycles) and a multiply-add. On 2,061 systems taken from KY8 (73 rows on average), the solve took 6.4 ns per row in a micro-benchmark.
- **The walk along the segment list.** Each segment's address comes from the one before, and it waits on memory: 4.7 ns per row when the segments are not in the cache.

## What the change does

A new function, `linksolve()`, builds and solves each pipe's system in one pass.

1. **Pivots as ratios.** The pivots are computed as β<sub>j</sub> = p<sub>j</sub>/p<sub>j−1</sub>, where p<sub>j</sub> = b<sub>j</sub>·p<sub>j−1</sub> − a<sub>j</sub>·c<sub>j−1</sub>·p<sub>j−2</sub> is the determinant of the leading rows. Each p takes a multiplication and a subtraction after the one before, and the divisions for the pivots no longer wait for each other. The other divisions become multiplications by 1/β<sub>j</sub>. The right-hand side for the upstream end is zero except in its last row, so its solution needs only the back substitution.
2. **Overflow guard.** Every diagonal element is at least 1 (b<sub>j</sub> = 1 − a<sub>j</sub> − c<sub>j</sub>, with a<sub>j</sub> and c<sub>j</sub> ≤ 0, and the system is diagonally dominant), so every pivot is at least 1 and p only grows. p is scaled by 10<sup>−100</sup> whenever it passes 10<sup>100</sup>, checked every 4 rows; with diagonal elements below 10<sup>25</sup>, it cannot pass 10<sup>200</sup> between checks.
3. **Fallback.** A system with a diagonal element of 10<sup>25</sup> or more (a segment of almost no volume) is rebuilt and solved by BIT-12's `tridiag3()`, exactly as before.
4. **Solved while built.** The elimination of row j needs only the segments up to j + 1, so the system is solved as the segments are walked, and the arithmetic overlaps the waits on memory. The segments are kept in BIT-12's per-pipe list, for the back substitution and for `segqual_update()`.

On the 2,061 KY8 systems, the solve alone went from 6.4 to 3.7 ns per row. Steps 1 and 4 carry the gain; steps 2 and 3 keep it safe.

## How far the results move

**Why the last bits change.** The pivots and the eliminated right-hand sides are the same quantities computed in another order (as ratios of determinants, and with multiplications by reciprocals instead of divisions), so they round differently: about 10<sup>−14</sup> relative per system. Where p is rescaled, the factor 10<sup>−100</sup>, not a power of 2, adds rounding of the same order.

**Which cases and species can move.** Only models with dispersion; among the benchmark cases, KY8. The dispersing species move most; other species can move too, through the reactions and through segment merges, which mix all species at once. A change in the last bits can flip a merge where two segments differ by almost exactly a species' tolerance ([why](../README.md#why-a-rounding-change-can-move-results-by-more-than-rounding)); the table below shows how far the values moved on this run.

Beyond the benchmark cases, five more dispersion models were checked (variants of Net3, Richmond and KY8 with dispersion, one of them with two species): the largest differences were 5·10<sup>−13</sup> to 1.3·10<sup>−10</sup> mg/L, all within tier A. Forcing the fallback for every pipe gives the bits of the series without NEAR-03; forcing frequent rescaling (at 10<sup>30</sup> instead of 10<sup>100</sup>) stays within tier A, at 1.2·10<sup>−12</sup>. Results do not depend on the thread count: each pipe's system is solved by one thread, in the same order.

<!-- moves:NEAR-03 -->
Against 85a303d unpatched, solve mode, one thread, every concentration after every step (every sixth step on the larger networks). Tier A is below the species' report precision, tier B within its own tolerance; [the near-identical page](../README.md#how-within-tolerance-was-decided) has the rule.

| Case | Verdict | Species that moved most | Largest difference | 99th percentile | Nodes and links beyond tier B | Judgement |
| --- | --- | --- | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | IDENTICAL | - | - | - | - | PASS |
| Net6, chlorine bulk + wall | IDENTICAL | - | - | - | - | PASS |
| KY8, chlorine + dispersion | A | CL2 (MG) | 1.1e-10 | 1.1e-13 | 0 | PASS: within tolerance, as every platform is |
| Richmond, bacterial regrowth | IDENTICAL | - | - | - | - | PASS |
| Net3, chloramine decay | IDENTICAL | - | - | - | - | PASS |
| Net3, arsenic adsorption | IDENTICAL | - | - | - | - | PASS |
| MSX example (4 nodes) | IDENTICAL | - | - | - | - | PASS |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | - | - | - | - | PASS |
| Net3 chloramine, 14 species, every node and link every 5 min | IDENTICAL | - | - | - | - | PASS |
<!-- /moves -->

## Measured

<!-- measured:NEAR-03 -->
The bit-identical series (FIX-01, FIX-02, BIT-01 to BIT-17) against the same with NEAR-03 added, so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 17.5 at the start and 11.3 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 0.777 | 0.778 | 1.00x | 0.341 | 0.339 | 1.01x | yes |
| Net6, chlorine bulk + wall | 0.528 | 0.526 | 1.01x | 0.387 | 0.369 | 1.05x | yes |
| KY8, chlorine + dispersion | 0.527 | 0.394 | 1.34x | 0.197 | 0.205 | 0.96x | **no** |
| Richmond, bacterial regrowth | 0.698 | 0.704 | 0.99x | 0.171 | 0.176 | 0.97x | yes |
| Net3, chloramine decay | 1.24 | 1.25 | 0.99x | 0.270 | 0.269 | 1.00x | yes |
| Net3, arsenic adsorption | 0.434 | 0.441 | 0.98x | 0.145 | 0.153 | 0.95x | yes |
| MSX example (4 nodes) | 62.8 ms | 63.5 ms | 0.99x | 67.5 ms | 67.3 ms | 1.00x | yes |
| **Median** | | | **0.99x** | | | **1.00x** | |

To measure it yourself:

```sh
tools/try.py only:NEAR-03 --against bit
```
<!-- /measured -->

## Tried and not kept

- *The reciprocal of each pivot* (a Thomas solve with one division per row): 6.4 to 5.8 ns per row, against 3.7 ns for NEAR-03. The divider is pipelined; the chain of dependencies was the cost.
- *Software prefetch* in the segment walk and in `segqual_update()`, and *local copies of pointers* in the build loop: within noise.
- *A better fill-reducing ordering for the dispersion node matrix* (EPANET 2.2's `genmmd`): the nodal solve is about 1 % of KY8's run, so it could save at most 0.6 %.
