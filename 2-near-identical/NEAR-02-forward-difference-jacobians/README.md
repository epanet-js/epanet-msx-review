# NEAR-02: Jacobians by forward differences in ROS2 and Newton

| | |
|---|---|
| **Category** | [Near-identical](../README.md): results change at the level of rounding, about as much as the unpatched code's own results differ between platforms |
| **Area** | Chemistry (Rosenbrock integrator and equilibrium solver) |
| **Results** | <!-- results:NEAR-02 -->Differs from 85a303d in 12 of 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP), by rounding; every case passes the acceptance rule (see [the acceptance check](../README.md#the-acceptance-table))<!-- /results --> |
| **Files** | `msxutils.c`, `msxutils.h`, `newton.c`, `ros2.c` (+87 / -8 lines) |
| **Patch** | [`NEAR-02.patch`](NEAR-02.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-17, on its own: the other near-identical changes are not needed ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none beyond the bit-identical series: the new helper skips the Jacobian columns that [BIT-07](../../1-bit-identical/BIT-07-solver-shortcuts/) found unused, as `jacobian()` does after it |
| **Also fixes** | none. It keeps, on purpose, a bug in Newton's update ([below](#newtons-update-a-bug-kept-on-purpose)) |

## What was slow

Two solvers compute a Jacobian by finite differences with `jacobian()` ([msxutils.c:452](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxutils.c#L452)): ROS2, the Rosenbrock integrator, at every accepted step ([ros2.c:197](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/ros2.c#L197)), and Newton's method for the `EQUIL` species, at every iteration ([newton.c:130](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/newton.c#L130)). `jacobian()` uses central differences: for each column j, the functions at x + ε·e<sub>j</sub> and at x − ε·e<sub>j</sub>, with ε = 10<sup>−7</sup> (one-sided where x<sub>j</sub> is 0). That is two evaluations per column.

- **ROS2** then evaluated the rates at y once more for its first stage, and at the new y for its second: 2n + 2 rate evaluations per accepted step, for n Jacobian columns. On the chloramine case (8 rate species, one of whose columns BIT-07 skips, so n = 7) that is 16 evaluations per step.
- **Newton** runs in every pipe segment after every reaction step, and at junctions and tanks. Each iteration took 2n evaluations of the equilibrium expressions: 12 for the chloramine model's 6 equilibrium species, and 93 % of the calls take two iterations.

In the profiles of the bit-identical series on the chloramine case, the two Jacobians were most of the run.

## What the change does

One helper, `jacobianFwd()` in `msxutils.c`, computes the Jacobian by forward differences from function values the caller already has at x: column j is (F(x + ε·e<sub>j</sub>) − F(x))/ε, with the same step ε = 10<sup>−7</sup> as `jacobian()`, skipping the unused columns. It takes one evaluation per column where `jacobian()` takes two. It has two users:

1. **ROS2.** The rates at y, which the first stage needs anyway, are evaluated first (or taken from the estimate of the first step size, when one was just made), and the Jacobian is built from them. An accepted step takes n + 2 evaluations instead of 2n + 2: 9 instead of 16 on the chloramine case. A rejected step, which keeps its Jacobian, takes 2 as before. `factorize()` is given another work vector, so that the rates at y survive it.
2. **Newton, for two or more equations.** Each iteration evaluates the functions at x once, then the forward-difference Jacobian: n + 1 evaluations instead of 2n, 7 instead of 12 on the chloramine case. For a single equation, as in the arsenic models, Newton keeps central differences: forward differences would save nothing (two evaluations either way), and they flipped segment merges on Net3 arsenic (see [Tried and not kept](#tried-and-not-kept)).

Where x<sub>j</sub> is 0, `jacobian()` already took the one-sided difference (F(x + ε·e<sub>j</sub>) − F(x))/ε, so those columns are bit for bit as before.

### Newton's update: a bug kept on purpose

`newton_solve()` computes its update from the function values that `jacobian()` leaves in its work vector, which are those at x + ε·e<sub>n</sub>, the last perturbed point, not those at x. For equilibria that are linear in the unknowns, it converges to the root shifted by −ε in the last unknown: on the chloramine case, dissolved CO<sub>2</sub> sits 10<sup>−7</sup> mol/L (4.5·10<sup>−4</sup> relative) from its true value, in the unpatched code and in the converged reference alike. This is a bug, listed with [the bugs found but not yet written up](../../3-bug-fixes/README.md#found-not-yet-written-up).

NEAR-02 keeps that behaviour, so as not to mix a bug fix into a near-identical change. After `jacobianFwd()`, the work vector holds F(x + ε·e<sub>n</sub>), the same values, bit for bit, as `jacobian()` left there, and the update uses them. NEAR-02 computes F(x) anyway, so a fix would cost nothing on top of it, but the fix moves dissolved CO<sub>2</sub> by about 3 times its tolerance at every node and link of the chloramine case: it changes results beyond rounding, and belongs in its own write-up with its own test.

## How far the results move

**Why the results move.** Forward differences approximate a column with an error of about ε/2 times a second derivative of the functions, where central differences have about ε²/6 times a third derivative. So the Jacobians differ; the methods do not.

- *ROS2* uses its Jacobian only in the linear systems of its two stages. It is a W-method: it keeps its order of accuracy with any approximation of the Jacobian (Verwer et al., 1999, *SIAM J. Sci. Comput.* 20(4)), and its step-size control still checks every step against each species' tolerances. The chloramine rates are polynomials of degree at most 2 in each species, so central differences give their Jacobian exactly, up to rounding, and forward differences differ from it by ε/2 times a second derivative. The stages, and so the concentrations, change by much less than the tolerances the step-size control enforces.
- *Newton* converges to where the functions are zero, whatever Jacobian takes it there; the Jacobian decides only the path. The chloramine model's equilibria are linear in the unknowns, so forward and central differences give the same Jacobian up to rounding, and Newton reaches the same point: its results move in their last bits. With nonlinear equilibria the path differs and the result can move within Newton's stopping tolerance; on a model with three coupled nonlinear equilibria, written for this check, it moved by at most 1.9·10<sup>−10</sup> relative, where building the unpatched code without fused multiply-add moved it by 10<sup>−6</sup> to 9·10<sup>−6</sup>.

**Which cases and species can move.** Only models solved with ROS2, or with two or more equilibrium species: among the benchmark cases, the chloramine ones (Net3 chloramine, its 14-species output case, and the chloramine runs on the larger networks). Every other case uses Euler or RK5 and at most one equilibrium species, and keeps its bits. Within the chloramine model every species can move, since the rates and equilibria couple them.

**Merges.** Like any change of the last bits, this one can flip a segment merge where two segments differ by almost exactly a species' tolerance ([why](../README.md#why-a-rounding-change-can-move-results-by-more-than-rounding)). That is why Newton keeps central differences for a single equation: on Net3 arsenic, forward differences there flipped merges and moved results beyond tier B, for no gain.

Beyond the benchmark cases, test models with ROS2 and full and no coupling moved by at most 2.8·10<sup>−9</sup> (1.4·10<sup>−8</sup> relative), against 8.2·10<sup>−7</sup> for the unpatched code built without fused multiply-add. Results do not depend on the thread count.

<!-- moves:NEAR-02 -->
Against 85a303d unpatched, solve mode, one thread, every concentration after every step (every sixth step on the larger networks). Tier A is below the species' report precision, tier B within its own tolerance; [the near-identical page](../README.md#how-within-tolerance-was-decided) has the rule.

| Case | Verdict | Species that moved most | Largest difference | 99th percentile | Nodes and links beyond tier B | Judgement |
| --- | --- | --- | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | IDENTICAL | - | - | - | - | PASS |
| Net6, chlorine bulk + wall | IDENTICAL | - | - | - | - | PASS |
| KY8, chlorine + dispersion | IDENTICAL | - | - | - | - | PASS |
| Richmond, bacterial regrowth | IDENTICAL | - | - | - | - | PASS |
| Net3, chloramine decay | A | NH4 (MOLES) | 3e-12 | 2.8e-12 | 0 | PASS: within tolerance, as every platform is |
| Net3, arsenic adsorption | IDENTICAL | - | - | - | - | PASS |
| MSX example (4 nodes) | IDENTICAL | - | - | - | - | PASS |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | - | - | - | - | PASS |
| Net3 chloramine, 14 species, every node and link every 5 min | A | NH4 (MOLES) | 3e-12 | 2.8e-12 | 0 | PASS: within tolerance, as every platform is |
| L-Town 24 h, chlorine bulk + wall (Euler) | IDENTICAL | - | - | - | - | PASS |
| L-Town 24 h, bacterial regrowth (RK5) | IDENTICAL | - | - | - | - | PASS |
| L-Town 24 h, chloramine decay (ROS2) | A | NH4 (MOLES) | 2.8e-12 | 2.3e-12 | 0 | PASS: within tolerance where a platform is not |
| NW Model 12 h, chlorine bulk + wall (Euler) | IDENTICAL | - | - | - | - | PASS |
| NW Model 12 h, bacterial regrowth (RK5) | IDENTICAL | - | - | - | - | PASS |
| NW Model 12 h, chloramine decay (ROS2) | A | NH4 (MOLES) | 2.9e-12 | 2.2e-12 | 0 | PASS: within tolerance where a platform is not |
<!-- /moves -->

## Measured

<!-- measured:NEAR-02 -->
The bit-identical series (FIX-01, FIX-02, BIT-01 to BIT-17) against the same with NEAR-02 added, so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 17.5 at the start and 11.3 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 0.777 | 0.762 | 1.02x | 0.341 | 0.346 | 0.99x | yes |
| Net6, chlorine bulk + wall | 0.528 | 0.513 | 1.03x | 0.387 | 0.377 | 1.03x | yes |
| KY8, chlorine + dispersion | 0.527 | 0.540 | 0.98x | 0.197 | 0.211 | 0.93x | yes |
| Richmond, bacterial regrowth | 0.698 | 0.695 | 1.00x | 0.171 | 0.185 | 0.92x | yes |
| Net3, chloramine decay | 1.24 | 0.866 | 1.43x | 0.270 | 0.196 | 1.38x | **no** |
| Net3, arsenic adsorption | 0.434 | 0.434 | 1.00x | 0.145 | 0.147 | 0.99x | yes |
| MSX example (4 nodes) | 62.8 ms | 63.2 ms | 0.99x | 67.5 ms | 67.3 ms | 1.00x | yes |
| **Median** | | | **1.00x** | | | **0.99x** | |

To measure it yourself:

```sh
tools/try.py only:NEAR-02 --against bit
```
<!-- /measured -->

## Tried and not kept

- *Simplified Newton* (the first iteration's factorised Jacobian kept for the later iterations of a solve): a further 1.13x on the chloramine case, and bit-identical to NEAR-02 on every benchmark case, because their equilibria are linear in the unknowns. On the model with three coupled nonlinear equilibria it moved results by up to 1.9·10<sup>−5</sup> relative, two to twenty times the platforms' spread on that model (10<sup>−6</sup> to 9·10<sup>−6</sup>, as above): still within tier A, but the limit is then Newton's own tolerance, not rounding. A Jacobian kept from an earlier iterate also converges more slowly, and can fail where Newton converges.
- *Forward differences in Newton for a single equation*: nothing to gain over central differences with one unknown, and the last-bit change flipped merges on Net3 arsenic (adsorbed arsenate up to 6.3 µg/ft², 47 nodes and links beyond tier B).
- *A step relative to each concentration* (√ε<sub>machine</sub>·|y|, as in the forward-difference version left in a comment in `jacobian()`, [msxutils.c:506](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxutils.c#L506)): no faster than the absolute step, and a larger change on HOCL.
- *Newton's update from F(x)*: a fix that changes results ([above](#newtons-update-a-bug-kept-on-purpose)).
- *A faster LU factorisation for small systems* (swapping row pointers instead of rows): bit-identical, within noise; `factorize()` and `solve()` are both chains of dependent operations.
