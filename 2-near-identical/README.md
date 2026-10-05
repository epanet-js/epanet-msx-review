# Near-identical changes

[All changes](../README.md)

**Every change in this folder alters MSX's results.** Each moves concentrations at the level of rounding, by no more than the unpatched code's own results already move between platforms. They apply after the [bit-identical series](../1-bit-identical/README.md) (FIX-01, FIX-02, BIT-01 to BIT-17), each on its own or together, and add no API, no file format and no numerical method: the same Lagrangian transport with the same segments and merging rule, the same integrators and the same Newton solver. The Jacobians are approximated differently, and some arithmetic is done in another order. Results stay independent of the thread count.

| ID | Change | Area | Measured, this change alone |
|---|---|---|---|
| [NEAR-01](NEAR-01-reassociate-expressions/) | Reassociate rate expressions around their invariant parts | Chemistry (expression interpreter) | <!-- summary:NEAR-01 -->1.03x median, up to 1.14x (Richmond, bacterial regrowth)<!-- /summary --> |
| [NEAR-02](NEAR-02-forward-difference-jacobians/) | Jacobians by forward differences in ROS2 and Newton | Chemistry (integrator and equilibrium solver) | <!-- summary:NEAR-02 -->up to 1.43x (Net3, chloramine decay); at 8 threads up to 1.38x (Net3, chloramine decay)<!-- /summary --> |
| [NEAR-03](NEAR-03-dispersion-pivot-chain/) | Dispersion: a tridiagonal solve without a chain of divisions | Dispersion | <!-- summary:NEAR-03 -->up to 1.34x (KY8, chlorine + dispersion)<!-- /summary --> |

Each change was judged on its own: `only:NEAR-NN` is the bit-identical series plus that one change, and the bit-identical series gives 85a303d's results bit for bit, so whatever moves is that change's doing. `near` is all three together.

<!-- near-verdicts -->
| Change | Cases whose results move | Species that moved most (case) | Acceptance rule | Larger networks | Same bits at 1, 8, 10 threads and without OpenMP | Speed-up, 1 thread | 8 threads |
| --- | ---: | --- | --- | --- | --- | ---: | ---: |
| `only:NEAR-01` | 6 of 9 | A5s (Net3, arsenic adsorption): FAIL, max 4.9, p99 0.81 | 9 of 9 pass | not run | yes, 9 cases | 1.03x | 1.00x |
| `only:NEAR-02` | 2 of 9 | NH4 (Net3, chloramine decay): A, max 3e-12, p99 2.8e-12 | 9 of 9 pass | not run | yes, 9 cases | 1.00x | 0.99x |
| `only:NEAR-03` | 1 of 9 | CL2 (KY8, chlorine + dispersion): A, max 1.1e-10, p99 1.1e-13 | 9 of 9 pass | not run | yes, 9 cases | 0.99x | 1.00x |
| `near` | 8 of 9 | A5s (Net3, arsenic adsorption): FAIL, max 4.9, p99 0.81 | 9 of 9 pass | not run | yes, 9 cases | 1.05x | 1.07x |

Speed-ups are median over the 7 main cases, against the bit-identical series.
<!-- /near-verdicts -->

<!-- near-paragraphs -->
### NEAR-01: Reassociate rate expressions around their invariant parts

BIT-04 caches the parts of a rate expression that depend only on a pipe's parameters and hydraulics, but only where the expression, as written, computes them first: Richmond's `Kdet*Xa*U*Av` still multiplied by `U` and `Av` in every segment. NEAR-01 expands sums and products, gathers terms with the same factors and takes shared factors out, so that more of each expression is computed once per pipe: Richmond's rate program goes from 72 operations to 57, BWSN2's chlorine rate from 9 to 4. On Net3 arsenic it moves some species further than any platform sample does, within the rule's allowance of twice the largest.

[Write-up, measurements and patch](NEAR-01-reassociate-expressions/)

### NEAR-02: Jacobians by forward differences in ROS2 and Newton

ROS2 and Newton's method computed their Jacobians by central differences, two evaluations of the expressions per column, and on the chloramine case the two Jacobians were most of the run. One helper now computes them by forward differences from the values at the current point, with the same step: an accepted ROS2 step takes 9 rate evaluations instead of 16, and a Newton iteration 7 instead of 12. Newton keeps central differences for a single equation, and the bug in its update is left as it is, for a fix of its own.

[Write-up, measurements and patch](NEAR-02-forward-difference-jacobians/)

### NEAR-03: Dispersion: a tridiagonal solve without a chain of divisions

Dispersion is about half of the KY8 run. Each pipe's tridiagonal solve waited, row by row, for a division by the previous pivot, and the walk along the pipe's segments that builds the system waited on memory. The pivots are now ratios of determinants, whose recurrence needs no division, and the system is solved while it is built: 6.4 to 3.7 ns per row on systems taken from KY8.

[Write-up, measurements and patch](NEAR-03-dispersion-pivot-chain/)
<!-- /near-paragraphs -->

## How "within tolerance" was decided

A tolerance cannot be set by feel, so the first question was how much the unpatched code's own results already vary between platforms. The method is the one used for EPANET's [near-identical changes](https://github.com/epanet-js/epanet-performance/blob/main/2-near-identical/README.md#how-within-tolerance-was-decided), restated in MSX's terms.

### Platform samples

`tools/build-msx.sh` builds the unpatched source (MSX and EPANET 2.2) three other ways:

| Platform sample | Build | What it stands for |
|---|---|---|
| FMA off | `base@nofma`: `-ffp-contract=off` | x86-64 builds without fused multiply-add, MSVC with `/fp:precise` |
| FMA across statements | `base@fmafast`: `-ffp-contract=fast` | GCC's default on 64-bit ARM Linux |
| x86-64 | `base@x86`: built for x86-64 and run under Rosetta, without OpenMP | A second platform: no fused multiply-add and another maths library |

The reference is `base` as built here (Apple clang, arm64, `-O3`, which fuses multiply-adds within a statement). Results do not depend on the thread count, so every sample runs on one thread. On Linux the tools use `base@clang` and `base@native` in place of `base@x86`.

**Windows is a fourth platform, not sampled here.** The official Windows Release build compiles with `/fp:fast` (`src/solver/CMakeLists.txt`), which lets MSVC reassociate and contract floating-point expressions, so Windows results already differ from those of the other platforms, probably by more than any sample above. MSVC cannot be run on this machine, so it is described rather than measured.

### Tiers, per species

Every concentration of every species at every node and link after every step (`bench -dump`, float64) is compared with the reference by [`tools/compare.py`](../tools/compare.py). Each species is judged on its own terms, from the `.msx` file:

- **Tier A**: below the species' report precision, and within tier B: |difference| ≤ min(½·10<sup>−precision</sup>, aTol + rTol·|c|). Where the report precision is coarse (chloramine in moles prints as 0.00 at the default 2 decimals) tier B is the binding limit.
- **Tier B**: within the species' own tolerance: |difference| ≤ aTol + rTol·|c|, with aTol and rTol the species' tolerances (or the `ATOL`/`RTOL` options, or MSX's defaults 0.01 and 0.001) and c the reference value. aTol is both the integrators' absolute tolerance and MSX's threshold for "the same water": two neighbouring segments are merged when every species differs by less than its aTol (`MSXqual_isSame`).

A case's verdict is its worst species: IDENTICAL, A, B, or FAIL (beyond tier B somewhere); A~ or B~ when the step times differ. The tools also report, per species, the largest absolute and relative difference, the 99th percentile of the differences over all values, and the number of nodes and links beyond each tier at some step.

The report is compared line by line (EPANET's date and time stamps removed): which printed values change, and by how many units of their last digit. The mass balance is compared figure by figure, relative to the largest figure in that species' balance.

### Why a rounding change can move results by more than rounding

The merging rule is a threshold. When two segments differ by almost exactly aTol, the last bit of a concentration decides whether they merge, and from then on the two runs carry differently mixed water. That is MSX's counterpart of a control switching a step earlier in EPANET. On Net3 with arsenic, built with fused multiply-add across statements instead of within statements, adsorbed arsenate differs by up to about 2 µg/ft² at one link and dozens of nodes and links go beyond tier B; built for x86-64, Richmond's bacterial cell count moves by up to about 0.9 log units (the tables below have this run's values). Every species moves, even a simple first-order decay, because a merge mixes all species at once.

### A converged reference

`bit@conv` is the same model run with [`tools/converged.patch`](../tools/converged.patch): the integrators' tolerances 1000 times tighter, Newton's to 8 significant digits instead of 3, and Euler, which has no error control, replaced by RK5. Segments are still merged with each species' own aTol, so the reference differs from the default run only in how accurately the chemistry is solved; tightening `ATOL` in the `.msx` file would also have changed which segments merge. It is the analogue of EPANET's `ACCURACY 1e-6`, and it shows how far the default settings already sit from the converged answer: on the chloramine case, ammonium is off by about 0.2 % (relative) at about 200 nodes and links, because Newton stops at a relative step of 10<sup>−3</sup>; Euler on Net6 and KY8 is off by up to 0.04 to 0.06 mg/L of chlorine.

### The rule

Per case, for every change:

1. Where every platform sample is within tolerance (tier A or B for every species), the change must be within tolerance too.
2. Where a sample is not, the change must stay as close as the platforms: for every species, its 99th-percentile difference and its number of nodes and links beyond tier B may be at most twice the largest platform value (floors: the species' tier-A absolute limit, and 5 nodes or links).
3. Failing that, it passes if, for every species, it is no farther from the converged reference than the builds without it, within twice their largest value on the same two measures.

The report and mass balance are judged alongside. Printed values may move by one unit of their last digit (a value that sat on a rounding boundary), or by no more than twice as many units as a platform sample's. Each mass-balance figure may move by 10<sup>−5</sup> of the species' largest figure (the report prints six significant digits), or by twice the largest platform difference.

A change must also leave results independent of the thread count: each build gives the same bits at 1, 8 and 10 threads and built without OpenMP.

### How much the unpatched code varies

Each sample against `base`: the verdict, then the species farthest from it relative to its tier-B limit, with its largest absolute difference (and the largest relative difference over values of at least aTol), its 99th percentile, and the most nodes and links beyond tier B for any species. Concentrations are in the species' own units.

<!-- near-platforms -->
| Case | FMA off | FMA across statements | x86-64 | Report and mass balance |
| --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | A: CL2 max 2.1e-05 (rel 0.0001), p99 1.7e-10 | IDENTICAL | A: CL2 max 1.2e-05 (rel 5e-05), p99 2.3e-10 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| Net6, chlorine bulk + wall | A: CL2 max 0.00013 (rel 0.0005), p99 1.8e-08 | A: CL2 max 0.00015 (rel 0.0006), p99 1.6e-08 | A: CL2 max 5.6e-05 (rel 0.0002), p99 1.6e-08 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| KY8, chlorine + dispersion | A: CL2 max 0.0011 (rel 0.003), p99 3.2e-07 | A: CL2 max 0.0011 (rel 0.003), p99 3.1e-07 | A: CL2 max 0.0011 (rel 0.003), p99 2.9e-07 | FMA off: MSX tables identical (and 23 lines of EPANET's hydraulic log); FMA across statements: MSX tables identical (and 22 lines of EPANET's hydraulic log); x86-64: MSX tables identical (and 21 lines of EPANET's hydraulic log) |
| Richmond, bacterial regrowth | FAIL: Nb max 1 (rel 4), p99 0.0019, beyond B 110 | IDENTICAL | FAIL: Nb max 0.87 (rel 0.2), p99 0.00095, beyond B 25 | FMA off: 7 lines, ≤1 last digit; mass balance 8e-05; FMA across statements: identical; x86-64: 5 lines; mass balance 3e-05 |
| Net3, chloramine decay | A: NH4 max 2.6e-09 (rel 2e-06), p99 1e-10 | A: NH4 max 2e-08 (rel 2e-05), p99 1.5e-10 | A: NH4 max 2.7e-09 (rel 2e-06), p99 9.4e-11 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| Net3, arsenic adsorption | FAIL: A5s max 5.4 (rel 2e+02), p99 1.1, beyond B 114 | FAIL: A5s max 2.4 (rel 1e+01), p99 0.13, beyond B 29 | FAIL: A5s max 5.7 (rel 2e+02), p99 1.1, beyond B 118 | FMA off: 19 lines, ≤20 last digit; mass balance 2e-05; FMA across statements: 10 lines, ≤1 last digit; mass balance 3e-05; x86-64: 16 lines, ≤20 last digit; mass balance 2e-05 |
| MSX example (4 nodes) | A: AS5 max 1.6e-14 (rel 2e-15), p99 8.9e-15 | IDENTICAL | A: AS5 max 1.6e-14 (rel 2e-15), p99 8.9e-15 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| BWSN2, 2 species, every node and link every 5 min | A: S2 max 9.3e-06 (rel 4e-05), p99 1.6e-08 | IDENTICAL | A: S2 max 2.1e-05 (rel 8e-05), p99 1.5e-08 | FMA off: 2 lines, ≤1 last digit; FMA across statements: identical; x86-64: 1 lines, ≤1 last digit |
| Net3 chloramine, 14 species, every node and link every 5 min | A: NH4 max 1.3e-09 (rel 2e-06), p99 2.7e-11 | A: NH4 max 2.7e-09 (rel 3e-06), p99 3.3e-11 | A: NH4 max 1.8e-09 (rel 3e-06), p99 3.8e-11 | FMA off: identical; FMA across statements: identical; x86-64: identical |
<!-- /near-platforms -->

### How far the default settings are from converged

Every build against the converged reference, by the same measures.

<!-- near-converged -->
Every build against `bit@conv`.

| Case | `base` | `base@nofma` | `base@fmafast` | `base@x86` | `only:NEAR-01` | `only:NEAR-02` | `only:NEAR-03` | `near` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 2.1e-05 (rel 0.0001), p99 1.7e-10 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 1.2e-05 (rel 5e-05), p99 2.3e-10 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 |
| Net6, chlorine bulk + wall | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 |
| KY8, chlorine + dispersion | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 |
| Richmond, bacterial regrowth | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | FAIL: Nb max 1 (rel 4), p99 0.0019, beyond B 110 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | FAIL: Nb max 0.87 (rel 0.2), p99 0.00095, beyond B 25 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 |
| Net3, chloramine decay | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 |
| Net3, arsenic adsorption | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 27 (rel 9e+02), p99 7.1, beyond B 199 | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 26 (rel 1e+03), p99 7, beyond B 198 | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 26 (rel 1e+03), p99 7, beyond B 198 |
| MSX example (4 nodes) | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 |
| BWSN2, 2 species, every node and link every 5 min | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 1.7e-05 (rel 5e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 2.4e-05 (rel 9e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 |
| Net3 chloramine, 14 species, every node and link every 5 min | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 |
<!-- /near-converged -->

## NEAR-01 on Net3 arsenic

<!-- near-arsenic-text -->
This is the one case where a near-identical change moves results beyond tier B, and it is at the edge of the rule, so it is set out in full here. [NEAR-01](NEAR-01-reassociate-expressions/) on its own moves adsorbed arsenate (A5s) by up to 4.9 µg/ft² at one link, arsenate (A5, A5w) by up to 1.9 µg/L, and 101 to 126 nodes and links go beyond tier B for the arsenic species. That is beyond tier B, and at the top of the platform spread or above it:

- **Against the platforms, species by species** (the table below): its 99th-percentile difference is larger than every platform sample's for A5 (0.022 against at most 0.015), A5w (0.022 against 0.016) and NH2CL (0.0049 against 0.0045), and only for A5s is it inside the spread (0.81 against 1.1). Its counts of nodes and links beyond tier B are above every sample's for A5 (122 against 118), A5w (126 against 116) and NH2CL (24 against 21). It **passes only through the allowance of twice the largest platform value**, which clause 2 of the rule gives; with a factor of 1 it would fail.
- **The report and mass balance**: 19 lines differ, by up to 5 units of their last digit (the FMA-off and x86-64 samples move by up to 20); the mass balance moves by 5.6·10<sup>−5</sup> of the largest figure, against 3.0·10<sup>−5</sup> for the largest sample, inside the limit of twice that.
- **Why it moves so much.** Any last-bit change flips segment merges on this case, because many neighbouring segments differ by almost exactly the merging tolerance. Built with fused multiply-add across statements, the unpatched code moves A5s by 2.4 µg/ft² with 29 nodes and links beyond tier B; a forward-difference Newton for this model's single equilibrium, tried and rejected (see [Tried and rejected](#tried-and-rejected)), moved it by 6.3 µg/ft² with 47. Built without fused multiply-add, or for x86-64, the unpatched code moves it by 5.4 and 5.7 µg/ft².
- **Against the converged run**, NEAR-01 is no farther off than the unpatched code: its 99th-percentile distance for A5s is 7.0 µg/ft² against 7.1 for 85a303d and every platform sample, and its largest 26 against 27. The default settings leave every build about equally far from the converged answer on this case; the change moves results within that band, not away from it.

So NEAR-01 is accepted on this case by clause 2, at its limit. A reviewer who wants a stricter rule than the one set out above should look at this case first; the other changes leave Net3 arsenic bit-for-bit unchanged.
<!-- /near-arsenic-text -->

<!-- near-arsenic -->
| Species | Candidate p99 / beyond B | FMA off | FMA across statements | x86-64 | Limit (2x the largest) | Within |
| --- | --- | --- | --- | --- | --- | --- |
| A3 | 8.2e-11 / 0 | 2.1e-10 / 0 | 2.8e-11 / 0 | 4.9e-10 / 0 | 0.005 / 5 | yes |
| A5 | 0.022 / 122 | 0.015 / 113 | 0.0064 / 24 | 0.014 / 118 | 0.03 / 236 | yes |
| A5w | 0.022 / 126 | 0.016 / 114 | 0.0068 / 29 | 0.015 / 116 | 0.033 / 232 | yes |
| A5s | 0.81 / 101 | 1.1 / 101 | 0.13 / 25 | 1.1 / 102 | 2.3 / 204 | yes |
| NH2CL | 0.0049 / 24 | 0.0045 / 20 | 0.0026 / 8 | 0.0044 / 21 | 0.0089 / 42 | yes |

Distance from the converged reference `bit@conv` (p99 / beyond B), clause 3:

| Species | Candidate | `base` | `base@nofma` | `base@fmafast` | `base@x86` | Limit | Within |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 0.005 / 5 | yes |
| A5 | 0.33 / 198 | 0.34 / 198 | 0.34 / 199 | 0.34 / 198 | 0.34 / 198 | 0.68 / 398 | yes |
| A5w | 0.33 / 198 | 0.34 / 199 | 0.34 / 199 | 0.34 / 199 | 0.34 / 199 | 0.68 / 398 | yes |
| A5s | 7 / 114 | 7.1 / 114 | 7.1 / 114 | 7.1 / 114 | 7.1 / 114 | 14 / 228 | yes |
| NH2CL | 0.0063 / 28 | 0.0065 / 26 | 0.0066 / 26 | 0.0064 / 28 | 0.0065 / 27 | 0.013 / 56 | yes |
<!-- /near-arsenic -->

## The acceptance table

<!-- near-acceptance -->
Reference `base` (85a303d unpatched); platform samples `base@nofma`, `base@fmafast`, `base@x86`; converged reference `bit@conv`. Each `only:NEAR-NN` is the bit-identical series plus that change alone; `near` is all three. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), 2026-10-05.

#### `only:NEAR-01`

| Case | Verdict | Largest differences | Report | Judgement | Why |
| --- | --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | A | CL2 1e-15 (p99 2.5e-24) | identical | PASS | within tolerance, as every platform is |
| Net6, chlorine bulk + wall | A | CL2 1.8e-15 (p99 2.2e-16) | identical | PASS | within tolerance, as every platform is |
| KY8, chlorine + dispersion | A | CL2 1.4e-15 (p99 1.7e-16) | identical | PASS | within tolerance, as every platform is |
| Richmond, bacterial regrowth | A | Nb 2e-14 (p99 8.9e-16), Na 4.4e-15 (p99 0), S 1.7e-16 (p99 0), 3 more species | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Net3, arsenic adsorption | FAIL | A5s 4.9 (p99 0.81, 101 beyond B), A5w 1.9 (p99 0.022, 126 beyond B), A5 1.9 (p99 0.022, 122 beyond B), 2 more species | 19 lines, ≤5 last digit; mass balance 6e-05 | PASS | as close as the platforms |
| MSX example (4 nodes) | A | AS5 8.5e-14 (p99 5.5e-14), AStot 8.5e-14 (p99 5.5e-14), AS3 7.8e-16 (p99 3.3e-16), 2 more species | identical | PASS | within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Net3 chloramine, 14 species, every node and link every 5 min | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |

#### `only:NEAR-02`

| Case | Verdict | Largest differences | Report | Judgement | Why |
| --- | --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Net6, chlorine bulk + wall | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| KY8, chlorine + dispersion | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Richmond, bacterial regrowth | IDENTICAL | identical | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay | A | NH4 3e-12 (p99 2.8e-12), NH2CL 5.3e-14 (p99 4.9e-14), NHCL2 4.6e-14 (p99 4.3e-14), 4 more species | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |
| Net3, arsenic adsorption | IDENTICAL | identical | identical | PASS | within tolerance where a platform is not |
| MSX example (4 nodes) | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Net3 chloramine, 14 species, every node and link every 5 min | A | NH4 3e-12 (p99 2.8e-12), NH2CL 5.3e-14 (p99 4.9e-14), NHCL2 4.6e-14 (p99 4.3e-14), 4 more species | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |

#### `only:NEAR-03`

| Case | Verdict | Largest differences | Report | Judgement | Why |
| --- | --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Net6, chlorine bulk + wall | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| KY8, chlorine + dispersion | A | CL2 1.1e-10 (p99 1.1e-13) | identical | PASS | within tolerance, as every platform is |
| Richmond, bacterial regrowth | IDENTICAL | identical | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Net3, arsenic adsorption | IDENTICAL | identical | identical | PASS | within tolerance where a platform is not |
| MSX example (4 nodes) | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Net3 chloramine, 14 species, every node and link every 5 min | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |

#### `near`

| Case | Verdict | Largest differences | Report | Judgement | Why |
| --- | --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | A | CL2 1e-15 (p99 2.5e-24) | identical | PASS | within tolerance, as every platform is |
| Net6, chlorine bulk + wall | A | CL2 1.8e-15 (p99 2.2e-16) | identical | PASS | within tolerance, as every platform is |
| KY8, chlorine + dispersion | A | CL2 1.1e-10 (p99 1.1e-13) | identical | PASS | within tolerance, as every platform is |
| Richmond, bacterial regrowth | A | Nb 2e-14 (p99 8.9e-16), Na 4.4e-15 (p99 0), S 1.7e-16 (p99 0), 3 more species | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay | A | NH4 3e-12 (p99 2.8e-12), NH2CL 5.3e-14 (p99 4.9e-14), NHCL2 4.6e-14 (p99 4.3e-14), 4 more species | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |
| Net3, arsenic adsorption | FAIL | A5s 4.9 (p99 0.81, 101 beyond B), A5w 1.9 (p99 0.022, 126 beyond B), A5 1.9 (p99 0.022, 122 beyond B), 2 more species | 19 lines, ≤5 last digit; mass balance 6e-05 | PASS | as close as the platforms |
| MSX example (4 nodes) | A | AS5 8.5e-14 (p99 5.5e-14), AStot 8.5e-14 (p99 5.5e-14), AS3 7.8e-16 (p99 3.3e-16), 2 more species | identical | PASS | within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | identical | identical | PASS | within tolerance, as every platform is |
| Net3 chloramine, 14 species, every node and link every 5 min | A | NH4 3e-12 (p99 2.8e-12), NH2CL 5.3e-14 (p99 4.9e-14), NHCL2 4.6e-14 (p99 4.3e-14), 4 more species | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |

Totals: PASS 36
<!-- /near-acceptance -->

## Results do not depend on the thread count

<!-- near-threads -->
| Build | Cases | Same bits at 1, 8, 10 threads and without OpenMP |
| --- | ---: | --- |
| `only:NEAR-01` | 9 | yes, every case |
| `only:NEAR-02` | 9 | yes, every case |
| `only:NEAR-03` | 9 | yes, every case |
| `near` | 9 | yes, every case |
| `bit` | 9 | yes, every case |
<!-- /near-threads -->

## The larger networks

The rule was also applied on L-Town and the NW Model (`--cases real`), comparing every sixth step to keep the dumps to a manageable size. These runs are long for the unpatched code and its platform samples, so they were made once.

<!-- near-real -->
<!-- /near-real -->

## Limitations

The rule is a yardstick, not a proof. A reviewer should weigh these points:

- **(a) Clause 1 is lenient.** Anything within tier B passes where the platforms are within tolerance, even on a case where every platform agrees with the reference to 10<sup>−15</sup>. A change could move such a case by far more than the platforms do and still pass. The tables show the actual differences, so this can be checked case by case.
- **(b) The factor of 2 and the floors are a judgement.** There are three samples, all built with Apple clang on one Mac (one of them for another architecture), and the largest of three values is a noisy measure of platform spread.
- **(c) The 99th percentile over all values is blind to rare movement.** If fewer than 1 % of the values move, it is zero, whatever the size of the movement; the largest difference is reported but not used by clauses 2 and 3, only the count of nodes and links beyond tier B is.
- **(d) Changes are judged one at a time,** so the movement of each can be attributed. The cumulative `near` row shows they do not compound, but a different combination (for example with a later change) would have to be judged again.
- **(e) The cases are few and short.** Seven main cases and two output-heavy ones, run for 4 to 48 simulated hours; the larger networks were judged once, comparing every sixth step; the utility models were only timed.
- **(f) The converged reference is not converged in transport.** It tightens the chemistry only (the segment merging is unchanged, so transport error remains), and it replaces Euler with RK5, so on the Euler cases it measures the integrator's error as well as rounding.
- **(g) Windows is not sampled.** The official Windows build uses `/fp:fast`, probably the largest platform difference of all.
- **(h) Bug fixes are not judged by this rule.** A fix that changes results (such as Newton's update from a perturbed value, listed in [3-bug-fixes](../3-bug-fixes/README.md#found-not-yet-written-up)) fails it by design; such fixes are gated by their own tests, and how far they move results is reported, not judged.

## Tried and rejected

Measured during development on a shared machine, so the timings are indicative.

**They would move results beyond rounding:**

- *Simplified Newton* (keep the first iteration's factorised Jacobian for the later iterations of an equilibrium solve): a further 1.13x on the chloramine case, and bit-identical to NEAR-02 on every benchmark case, because their equilibria are linear in the unknowns. On a model with three coupled nonlinear equilibria (written for this check) it moved results by up to 1.9·10<sup>−5</sup> relative, ten times the platforms' spread on the same model. That is still within tier A, but the limit is then Newton's own tolerance, not rounding. A Jacobian kept from an earlier iterate also converges more slowly, and can fail where Newton converges.
- *Forward differences in Newton for a single equation* (the arsenic models): nothing to gain over central differences with one unknown, and the last-bit change flipped merges on Net3 arsenic (adsorbed arsenate up to 6.3 µg/ft², 47 nodes and links beyond tier B). NEAR-02 keeps central differences there.
- *Newton's update from f(x)* instead of f(x + ε·eₙ): it would move dissolved CO<sub>2</sub> on the chloramine case by 10<sup>−7</sup> mol/L at all 216 nodes and links, 3.1 times tier B. A fix, not a speed-up, and one that changes results, so it is listed with [the bugs not yet written up](../3-bug-fixes/README.md#found-not-yet-written-up).
- *Forward differences in ROS2 with a step relative to each concentration* (√ε<sub>machine</sub>·|y|): no faster than NEAR-02's absolute step, and a larger change on HOCL.

**No measurable gain, or not worth it:**

- *RK5 reusing the last derivative of the previous step* ("first same as last" across calls, per segment): exact only when the segment's concentrations, hydraulics and parameters are unchanged and nothing was clamped to zero or recomputed by an equilibrium or formula. After BIT-06 it would save 7.8 % of BWSN2's remaining rate evaluations (about 1.3 % of the run), none on Richmond, 0.08 % on arsenic, and needs a vector of derivatives per segment.
- *RK5's step-size control*: two `pow` calls per step, 4.2 % of BWSN2, 2.3 % of Richmond and 3.9 % of arsenic after BIT-06. Caching the one that depends only on the first step saves at most 2 %, and a cheaper `exp`/`log` form no more.
- *A faster LU factorisation for small systems* (swapping row pointers instead of rows): bit-identical, within noise; both `factorize()` and `solve()` are chains of dependent operations.
- *Own `exp`, `pow` and `log10`* (as EPANET's NEAR-01 did for `pow`): a scalar replacement is not faster than Apple's libm. After NEAR-01, `exp` is 6.4 % and `log10` 2.1 % of Richmond, and no batched path evaluates them. `pow` in Net6 and KY8 is already cached per pipe (BIT-04). A 2x faster `exp` would gain at most 3 % on one case.
- *Multiplying by the reciprocal of an invariant divisor in the interpreter* (Richmond's `/CL2C`): slower or within noise. NEAR-01 turns such divisions into multiplications only where that saves a dispatch.
- *Not computing rates that are the constant 0* (BWSN2's tracer; chloramine's H, ALK and TOC): bit-identical, no gain; those operations are off the critical path.
- *Common subexpressions and super-instructions in the interpreter*: about 2 of Richmond's 57 dispatches; nothing removable in the chloramine program (about 95 essential dispatches).
- *Dispersion: the reciprocal of each pivot* (a Thomas solve with one division per row): 6.4 to 5.8 ns per row, against 3.7 ns for NEAR-03. The divider is pipelined; the dependency chain was the cost.
- *A better fill-reducing ordering for the dispersion node matrix* (EPANET 2.2's `genmmd`): the nodal solve is about 1 % of KY8's run, so it could save at most 0.6 %.
- *Sums in another order, to move water through the nodes in parallel*: moving water level by level would give BWSN2 about 37 nodes per level, 5-7 µs of work against a 1-2 µs barrier, so at most 4-6 % on one case, and would need per-thread segment pools.

## Running the checks

```sh
tools/try.py only:NEAR-01 only:NEAR-02 only:NEAR-03 near --quick     # speed, and the verdict where results differ
tools/yardstick.py run --builds base,base@nofma,base@fmafast,base@x86,bit@conv,only:NEAR-01,only:NEAR-02,only:NEAR-03,near \
                       --cases main,output
tools/yardstick.py threads --builds only:NEAR-01,only:NEAR-02,only:NEAR-03,near
```

`base@x86` needs macOS with Rosetta; on Linux use `base@clang,base@native`. [benchmarking.md](../benchmarking.md#near-identical-changes) describes the tools.
