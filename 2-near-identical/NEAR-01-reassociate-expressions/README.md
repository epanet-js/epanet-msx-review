# NEAR-01: Reassociate rate expressions around their invariant parts

| | |
|---|---|
| **Category** | [Near-identical](../README.md): results change at the level of rounding, about as much as the unpatched code's own results differ between platforms |
| **Area** | Chemistry (expression interpreter) |
| **Results** | <!-- results:NEAR-01 -->Differs from 85a303d in 30 of 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP), by rounding; every case passes the acceptance rule (see [the acceptance check](../README.md#the-acceptance-table))<!-- /results --> |
| **Files** | `mathexpr.c` (+391 / -22 lines) |
| **Patch** | [`NEAR-01.patch`](NEAR-01.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-17, on its own: the other near-identical changes are not needed ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none beyond the bit-identical series: it extends the expression rewriter of [BIT-05](../../1-bit-identical/BIT-05-interpreter-dispatch/), and its gain comes through the cache of [BIT-04](../../1-bit-identical/BIT-04-pipe-invariant-cache/) |
| **Also fixes** | none |

**On one case, Net3 arsenic, NEAR-01 moves some species further than any platform sample does.** It passes the acceptance rule there only through the rule's allowance of twice the largest platform value. [How far the results move](#how-far-the-results-move) explains why, and [the category page](../README.md#near-01-on-net3-arsenic) has the numbers.

## What was slow

In the profiles taken during development on the bit-identical code, the largest part of a run on the cases with long rate expressions (Richmond, BWSN2) was the interpreter evaluating them: one dispatch per operation, for every segment at every step.

[BIT-04](../../1-bit-identical/BIT-04-pipe-invariant-cache/) computes the parts of an expression that depend only on a pipe's parameters, constants and hydraulics once per pipe, when its hydraulics change. It can split off only a part that the expression, as written, computes on its own: a left prefix of a product or a sum, or a whole operand. Taking an invariant factor out of the middle of a product would change the order of the floating-point operations. [BIT-05](../../1-bit-identical/BIT-05-interpreter-dispatch/) rewrites expressions only with identities that are exact in floating point (operands of `+` and `*` swapped, signs moved), so it cannot regroup them either. So invariant work was still done per segment:

- Richmond's Xb rate contains `Kdet*Xa*U*Av`. `Xa` is a concentration, so the interpreter computes `Kdet*Xa`, then `*U`, then `*Av`, in every segment at every evaluation, where `Kdet*U*Av` could be computed once per pipe.
- BWSN2's `-(k1*T1 + k2*(1-T1))*CL2` takes 8 operations after BIT-05. Expanded and regrouped, it is `(T1*(k2-k1) - k2)*CL2`, with both coefficients fixed: 4.
- Net6 and KY8's `-Kb*CL2-(4/D)*Kw*Kf/(Kw+Kf)*CL2` has two terms with the same factor `CL2`, computed separately: 5 operations after BIT-05, where `CL2*c`, with `c` cached per pipe, takes 2.

## What the change does

BIT-05's rewriter gets rules that are exact in real arithmetic but not in floating point. They are applied once, when the file is read, to each pipe term, formula, rate and equilibrium expression; tank expressions and compiled chemistry (the `COMPILER` option) are untouched, as in BIT-05.

1. **Expand.** Each arithmetic part of an expression is expanded into a sum of terms, each an invariant coefficient times other factors (at most 32 terms of at most 8 factors; a larger expression keeps BIT-05's form). A division by an invariant becomes part of the coefficient; a division by anything else, a reciprocal factor.
2. **Gather.** Terms with the same other factors are merged by adding their coefficients.
3. **Take out shared factors.** The factor shared by most terms is taken out of them (Horner's rule), and so on within each part.
4. **Move signs across sums.** `-(a+b)` may become `(-a)-b`, and `-(a-b)` become `b-a`. BIT-05 leaves these out because they can change the sign of a zero result.
5. **Choose.** BIT-05's cost model counts the dispatches each candidate form takes after BIT-04's split and the operand fusion, and the cheapest is kept. Of two forms that take as many dispatches, the one that keeps the value bit for bit is kept.

The invariant coefficients then become parts that BIT-04 caches, computed once per pipe per hydraulic step. A division by an invariant becomes a multiplication by a cached quotient where that saves a dispatch.

Operations per evaluation:

| Expression | As written | After BIT-05 | With NEAR-01 |
|---|---:|---:|---:|
| BWSN2 `-(k1*T1 + k2*(1-T1))*CL2` | 9 | 8 | 4 |
| Net6 and KY8 `-Kb*CL2-(4/D)*Kw*Kf/(Kw+Kf)*CL2` | 6 | 5 | 2: `CL2*c`, `c` cached |
| Richmond Xa rate `(MUa-Kd)*Xa - Kdet*Xa*U + Kdep*Xb/Av` | 11 | 11 | 6: `(MUa + -(Kd+Kdet*U))*Xa + Xb*(Kdep/Av)` |
| Richmond Xb rate | 11 | 11 | 6 |
| Net3 arsenic A5w rate | 15 | 12 | 10 |

Richmond's whole rate program goes from 72 operations as written to 57. The chloramine model has nothing to gain beyond BIT-05, so its expressions keep BIT-05's form and their bits.

## How far the results move

**Why the last bits change.** Each rewritten form equals the original in real arithmetic, but floating-point operations round, so a regrouped form can round differently: `(Kdet*U*Av)*Xa` and `((Kdet*Xa)*U)*Av` can differ in the last bit, and `a*x - b*x` and `(a-b)*x` by more where the two terms nearly cancel. Each rate evaluation can therefore differ by a unit or so in the last place, and the integrators carry that into the concentrations. Where nothing amplifies it, the concentrations move in their last digits, far inside tier A.

**Which cases and species can move.** Only the cases whose pipe expressions NEAR-01 rewrites: BWSN2, Net6, KY8, Richmond, Net3 arsenic, the MSX example, and the chlorine and bacteria runs on the larger networks. The chloramine cases, and the BWSN2 output case, whose rates are single products such as `-k1*S1`, keep their bits. Within a case, every species can move, even one whose own expression is unchanged: species are coupled through the rate expressions, and a segment merge mixes all species at once.

**Why merges can amplify a last-bit change on Net3 arsenic.** MSX merges two neighbouring segments when every species differs by less than its absolute tolerance ([`MSXqual_isSame()`](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L577)). Where a difference sits almost exactly at that tolerance, the last bit decides whether the segments merge, and from then on the two runs carry differently mixed water. On Net3 arsenic, any change of the last bits flips some of these decisions: building the unpatched code with fused multiply-add across statements does, and so did forward differences in Newton's method for its single equilibrium, which [NEAR-02](../NEAR-02-forward-difference-jacobians/) leaves out for that reason. Adsorbed arsenate (A5s) then moves most, because its equilibrium, `A5s = Smax*Ks*A5w/(1 + Ks*A5w)`, multiplies a change in the arsenate dissolved at the wall (A5w) by up to `Smax*Ks` = 250 where little arsenate has reached the wall.

**On Net3 arsenic, NEAR-01 is at the edge of the rule.** Of the three near-identical changes, it is the only one that moves any of the nine main and output cases beyond tier B, and this is that case. Every platform sample does too, but for some species NEAR-01's 99th-percentile difference and its number of nodes and links beyond tier B are larger than any sample's, and so is the movement of the arsenate mass balance. They are within twice the largest platform value, so the case passes the rule's second clause, but only through that allowance, at the top of the platform spread. [The category page](../README.md#near-01-on-net3-arsenic) shows it species by species against each platform sample, with the limits of the rule and the converged reference.

Beyond the benchmark cases, the test models written during development to exercise every operator and function of the interpreter moved by at most 1.2·10<sup>−10</sup>, within tier A. Results do not depend on the thread count: the rewriting is done once, when the file is read.

<!-- moves:NEAR-01 -->
Against 85a303d unpatched, solve mode, one thread, every concentration after every step (every sixth step on the larger networks). Tier A is below the species' report precision, tier B within its own tolerance; [the near-identical page](../README.md#how-within-tolerance-was-decided) has the rule.

| Case | Verdict | Species that moved most | Largest difference | 99th percentile | Nodes and links beyond tier B | Judgement |
| --- | --- | --- | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | A | CL2 (MG) | 1e-15 | 2.5e-24 | 0 | PASS: within tolerance, as every platform is |
| Net6, chlorine bulk + wall | A | CL2 (MG) | 1.8e-15 | 2.2e-16 | 0 | PASS: within tolerance, as every platform is |
| KY8, chlorine + dispersion | A | CL2 (MG) | 1.4e-15 | 1.7e-16 | 0 | PASS: within tolerance, as every platform is |
| Richmond, bacterial regrowth | A | Nb (log(N)) | 2e-14 | 8.9e-16 | 0 | PASS: within tolerance where a platform is not |
| Net3, chloramine decay | IDENTICAL | - | - | - | - | PASS |
| Net3, arsenic adsorption | FAIL | A5s (UG) | 4.9 | 0.81 | 101 | PASS: as close as the platforms |
| MSX example (4 nodes) | A | AS5 (UG) | 8.5e-14 | 5.5e-14 | 0 | PASS: within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | - | - | - | - | PASS |
| Net3 chloramine, 14 species, every node and link every 5 min | IDENTICAL | - | - | - | - | PASS |
| L-Town 24 h, chlorine bulk + wall (Euler) | A | CL2 (MG) | 1.8e-15 | 1.1e-16 | 0 | PASS: within tolerance, as every platform is |
| L-Town 24 h, bacterial regrowth (RK5) | A | Nb (log(N)) | 4.9e-15 | 8.9e-16 | 0 | PASS: within tolerance, as every platform is |
| L-Town 24 h, chloramine decay (ROS2) | IDENTICAL | - | - | - | - | PASS |
| NW Model 12 h, chlorine bulk + wall (Euler) | A | CL2 (MG) | 2.4e-15 | 1.7e-16 | 0 | PASS: within tolerance where a platform is not |
| NW Model 12 h, bacterial regrowth (RK5) | A | Nb (log(N)) | 2e-14 | 8.9e-16 | 0 | PASS: within tolerance, as every platform is |
| NW Model 12 h, chloramine decay (ROS2) | IDENTICAL | - | - | - | - | PASS |
<!-- /moves -->

## Measured

<!-- measured:NEAR-01 -->
The bit-identical series (FIX-01, FIX-02, BIT-01 to BIT-17) against the same with NEAR-01 added, so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 17.5 at the start and 11.3 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 0.777 | 0.748 | 1.04x | 0.341 | 0.359 | 0.95x | **no** |
| Net6, chlorine bulk + wall | 0.528 | 0.511 | 1.03x | 0.387 | 0.387 | 1.00x | **no** |
| KY8, chlorine + dispersion | 0.527 | 0.497 | 1.06x | 0.197 | 0.188 | 1.04x | **no** |
| Richmond, bacterial regrowth | 0.698 | 0.614 | 1.14x | 0.171 | 0.162 | 1.06x | **no** |
| Net3, chloramine decay | 1.24 | 1.29 | 0.96x | 0.270 | 0.273 | 0.99x | yes |
| Net3, arsenic adsorption | 0.434 | 0.431 | 1.01x | 0.145 | 0.140 | 1.04x | **no** |
| MSX example (4 nodes) | 62.8 ms | 63.9 ms | 0.98x | 67.5 ms | 67.6 ms | 1.00x | **no** |
| **Median** | | | **1.03x** | | | **1.00x** | |

To measure it yourself:

```sh
tools/try.py only:NEAR-01 --against bit
```
<!-- /measured -->

## Tried and not kept

- *Multiplying by the reciprocal of an invariant divisor everywhere* (Richmond's `/CL2C` in the inhibition terms): slower or within noise. NEAR-01 turns a division into a multiplication only where that saves a dispatch.
- *Common subexpressions and super-instructions in the interpreter*: about 2 of Richmond's 57 dispatches; nothing removable in the chloramine program (about 95 essential dispatches).
- *Own `exp`, `pow` and `log10`*: a scalar replacement is not faster than Apple's libm. With NEAR-01, `exp` is 6.4 % and `log10` 2.1 % of the Richmond run, so a 2x faster `exp` would gain at most 3 % on one case.
- *Not computing rates that are the constant 0* (BWSN2's tracer; chloramine's H, ALK and TOC): bit-identical, no gain; those operations are off the critical path.
