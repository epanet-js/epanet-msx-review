# BIT-07: Skip solver work whose result is known

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Chemistry (ROS2 and Newton solvers) |
| **Results** | <!-- results:BIT-07 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxchem.c`, `msxutils.c`, `msxutils.h`, `newton.c`, `newton.h`, `ros2.c`, `ros2.h` (+153 / -10 lines) |
| **Patch** | [`BIT-07.patch`](BIT-07.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-06 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

- **Newton's tolerance.** `newton_solve` computed `pow(10.0, -numsig)` on every call ([newton.c:118](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/newton.c#L118)): once per segment per step for models with equilibrium species, and in every derivative evaluation with full coupling. `numsig` is always `NUMSIG`, which is 3 ([msxchem.c:32](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L32)).
- **ROS2's Jacobian.** The Rosenbrock integrator computes the Jacobian of the rates at every accepted step ([ros2.c:197](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/ros2.c#L197)), by central differences: two rate evaluations for each rate species ([msxutils.c:485](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxutils.c#L485-L503)). In the chloramine model that is 16 of the 18 rate evaluations of a step. One of its eight rate species, alkalinity (`ALK`), appears in no rate expression: its column of the Jacobian is all zeros, and costs two rate evaluations per step for nothing. Once identical segments are reacted once ([BIT-06](../BIT-06-identical-segments-once/)), the Jacobians are the largest cost of the Net3 chloramine run.

## What the change does

1. **Newton's tolerance once.** The value is kept in the solver's per-thread struct, with the `numsig` it was computed for, and is computed again only if `numsig` changes.
2. **Zero columns of ROS2's Jacobian skipped.** When the file is opened, a read-only walk of the pipe and tank rate expressions, and of the terms and formula species they use, recursively, marks the rate species that no rate depends on. `ros2_integrate` passes that list to `jacobian()`, which sets those columns to zero without evaluating the rates. This is done only without full coupling: with `COUPLING FULL`, any species can change the equilibrium species, and through them the rates, so the Jacobian is computed as before. Newton's Jacobian is unchanged (it passes no list).

The first part is too small to measure on these cases; it is kept because it is free. The second applies to ROS2 models: on the benchmarks, Net3 chloramine and the chloramine runs on L-Town and the NW Model, where 18 rate evaluations per step become 16.

## Why the results are unchanged

1. It is the same value, computed once.
2. Without full coupling, a rate species that no rate expression mentions, directly or through terms and formula species, cannot change any rate. The two evaluations for its column give identical rates, and the old code stored their difference divided by the step, `(f[i] - w[i]) / eps2` with `f[i]` equal to `w[i]`: that is +0, exactly what the column now holds. The exception is a rate that evaluates to infinity, where the old code stored NaN; a model whose rates become infinite gives no meaningful results with either version.

Beyond the benchmark cases, the change was checked at 1 and 8 threads and without OpenMP, and on the six torture models of [BIT-02](../BIT-02-terms-evaluated-once/#why-the-results-are-unchanged), which include ROS2 with full and with no coupling.

## Measured

<!-- measured:BIT-07 -->
Each table compares the series up to BIT-06 ("before") with BIT-07 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.17 | 1.13 | 1.04x | 0.609 | 0.647 | 0.94x | yes |
| Net6, chlorine bulk + wall | 0.842 | 0.875 | 0.96x | 0.821 | 0.820 | 1.00x | yes |
| KY8, chlorine + dispersion | 1.48 | 1.57 | 0.94x | 0.623 | 0.628 | 0.99x | yes |
| Richmond, bacterial regrowth | 0.802 | 0.798 | 1.00x | 0.345 | 0.305 | 1.13x | yes |
| Net3, chloramine decay | 1.34 | 1.27 | 1.05x | 0.421 | 0.397 | 1.06x | yes |
| Net3, arsenic adsorption | 0.504 | 0.494 | 1.02x | 0.232 | 0.219 | 1.06x | yes |
| MSX example (4 nodes) | 85.0 ms | 84.8 ms | 1.00x | 84.6 ms | 80.2 ms | 1.06x | yes |
| **Median** | | | **1.00x** | | | **1.06x** | |

To measure it yourself:

```sh
tools/try.py BIT-07 --against BIT-06
```
<!-- /measured -->

## Tried and not kept

- **More of the Jacobian's structure.** Evaluating, for each column, only the rate expressions that depend on that species would save more, and would be exact under the same condition (no full coupling). But it needs a separate program per column and an extra rate evaluation per step, and would help one benchmark case. It was not done; part 2 is the share of that idea that needs neither.
- **Forward differences** for the ROS2 and Newton Jacobians: about half the rate evaluations, but results move at the level of rounding. This is [NEAR-02](../../2-near-identical/NEAR-02-forward-difference-jacobians/).
- **A simplified Newton method**, keeping the first iteration's factorised Jacobian: identical on the benchmark cases, whose equilibria are linear in the unknowns, but on a test model with nonlinear equilibria it moved results by up to 1.9e-5 relative, about ten times the spread between platforms, and it changes how the method converges.
- **Reusing RK5's last derivative from one call to the next:** exact only when nothing about the segment has changed, and it needs a stored derivative for every segment. After BIT-06 it would save about 8 % of BWSN2's remaining rate evaluations, about 1 % of the run, and nothing on Richmond.
- **Reusing f(y) in ROS2's first stage:** the Jacobian is evaluated at y ± ε, not at y, so there is nothing to reuse. After a rejected step reuse would be exact without coupling, but Net3 chloramine had 568,433 accepted steps and no rejected one.
- **Caching the `pow` in RK5's step-size control** (2-4 % of the RK5 cases after BIT-06): at most 2 %.
- **A faster LU factorisation** (`factorize`, about 12 % of Net3 chloramine): little to gain for 8 unknowns without changing the order of the arithmetic. Row pointers in `factorize` and `solve` gave identical results, within noise.
