# Bug fixes

[All changes](../README.md)

These three bugs were found while making EPANET-MSX faster. Their fixes come first in the series: each applies on its own to 85a303d, and the bit-identical series builds on FIX-01 and FIX-02. On every benchmark case the results are the same with them as without them, in every way of running MSX, at 1 and 8 threads and without OpenMP; what changes is what happens in the cases each bug is about.

| ID | Bug | What happens | Fix |
|---|---|---|---|
| [FIX-01](FIX-01-reaction-loop-error-race/) | Every pipe of the reaction loop writes the same error code | An integration or equilibrium failure in one pipe is overwritten by the next pipe's success, with one thread as with many: the run carries on with concentrations that were never solved | Each thread keeps its own code; the largest is returned |
| [FIX-02](FIX-02-zero-flow-segment-leak/) | A new segment is taken from the pool for every link at every quality step, and lost when the link has no flow | Memory grows by one segment per zero-flow link per step: about 70 MB per simulated week on Net6 | Take no segment for a link without flow |
| [FIX-03](FIX-03-tempfile-descriptor-leak/) | The descriptor that `mkstemp` opens is never closed | Every `MSXopen` leaks two file descriptors and every `MSXsolveH` one; a program running about 80 scenarios in one process runs out at macOS's default limit of 256 | Close it (upstream `dev` fixed it another way, PR #21) |

**FIX-01 can stop a model that runs today.** A model whose equilibrium or integration fails in some pipes appears to run with 85a303d. With FIX-01 it stops with error 513 or 514. The error is real: it was there before, and was being lost. It happened on one of the two utility models in this work, where water entered through a junction without pH, so the chloramine equilibria had no solution in the segments it reached; the unpatched code reported results with unsolved equilibria.

Each fix's folder has its write-up and its patch. Tests that show each bug and pass with its fix (`FIX-NN_test.c`, with any input files as `FIX-NN_*.inp` and `FIX-NN_*.msx`) will be added to the folders, and `tools/try.py FIX-NN` checks that a fix leaves the benchmark results unchanged.

<!-- fix-paragraphs -->
### FIX-01: Keep one pipe's reaction error from being lost to the next pipe's success

When the integration or the equilibrium solve fails in a pipe, MSX should stop with error 513 or 514. Since MSX 2.0 the error is lost: every pipe of the reaction loop writes its code into one shared variable, so the next pipe's 0 overwrites it, with one thread as with many, and the run carries on with unsolved concentrations in that pipe and reports success. A model that appears to run today can stop with error 514 (or 513) once this is fixed. The error is real: it was seen on one utility model, where water entered through a junction that set no pH.

`errcode` is shared by all threads of the OpenMP loop in `MSXchem_react()`, and MSX 1.1's return at the first error was commented out, because a `return` cannot leave an OpenMP loop. With several threads it is also a data race.

**Fix:** each thread keeps its own code, and a pipe that fails merges its code into the shared one inside a critical section, keeping the largest, so the same code is returned at any thread count.

[Write-up, measurements and patch](FIX-01-reaction-loop-error-race/)

### FIX-02: Take no new segment for a link without flow

At every quality step `advectSegs()` takes a segment from the pool for every link, ready for the water entering it. For a link without flow, `evalnodeoutflow()` returns before using it and never gives it back, so memory grows by one segment per zero-flow link per step: about 70 MB per simulated week on Net6. Results are not affected.

MSX 1.1's `release()` gave the segment back; the topological routing of MSX 2.0 dropped that call.

**Fix:** test for flow before taking the segment, and take none for a link without flow.

[Write-up, measurements and patch](FIX-02-zero-flow-segment-leak/)

### FIX-03: Close the file descriptor that `mkstemp` opens

On systems other than Windows, every `MSXopen` leaks two file descriptors and every `MSXsolveH` one, so a toolkit program that runs one scenario after another in one process runs out of descriptors after about 80 scenarios at macOS's default limit of 256. Results are not affected.

`MSXutils_getTempName()` calls `mkstemp()` for a unique name, but `mkstemp()` also creates and opens the file; MSX discards the descriptor and opens the file again by name.

**Fix:** close the descriptor at once. Upstream `dev` fixed the same leak another way (PR #21), so this patch does not apply there.

[Write-up, measurements and patch](FIX-03-tempfile-descriptor-leak/)
<!-- /fix-paragraphs -->

## Fixed as part of a performance change

Two bit-identical groups also fix a bug, because the faster code cannot keep it:

- [BIT-02](../1-bit-identical/BIT-02-terms-evaluated-once/): a cycle of `FORMULA` species (such as B defined from C and C from B), or a cycle of `[TERMS]` that the input check misses, recursed until the stack overflowed. Evaluating each term and formula once, in an order fixed when the file is opened, finds any such cycle, and `MSXopen` returns error 506. This covers interpreted chemistry; with the `COMPILER` option the generated code still recurses (see below).
- [BIT-11](../1-bit-identical/BIT-11-dispersion-mass-without-locks/): the dispersed mass in the mass balance was summed in whatever order the threads finished, so its last digits changed from run to run and with the thread count. It is now summed in link order. Concentrations were never affected.

## Found, not yet written up

These were found by reading the code and confirmed with small models, but have no write-up, test or patch in this repository yet. Line numbers are at 85a303d, in `src/solver/`. Several of them change results on the models they affect, so their fixes would be judged by their own tests, not by the bit-identity of the benchmark cases.

- **Newton's update uses a perturbed function value.** `jacobian()` leaves `f` evaluated at x + ε·eₙ, and `newton_solve()` uses it as f(x) for the step ([newton.c:130](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/newton.c#L130), [msxutils.c:485](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxutils.c#L485)). With `EQUIL B B-A` and A = 1e-6, B comes out 10 % off. Fixing it changes every model with equilibria (dissolved CO₂ on the chloramine case moves by 3 times its tolerance).
- **Junction formulas and equilibria read parameters as zero**, and compiled chemistry dereferences a null pointer there (`MSX.Tank[0].param`): a node `FORMULA` or `EQUIL` that uses a `PARAMETER` gives 0 at every junction ([msxchem.c:360](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L360), [msxchem.c:1043](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L1043)).
- **Equilibria solved outside the reaction step ignore failures.** At junctions, in tank mixing and for the initial segments, `MSXchem_equil()`'s return code is dropped ([msxqual.c:1108](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1108), [msxtank.c:83](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxtank.c#L83), [msxqual.c:769](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L769) and others), so a failure there leaves the equilibrium species unsolved with no error. FIX-01 does not change these calls.
- **Dispersion takes a source of another species.** After searching the node's sources for the species, `solve_nodequal` tests the node's first source whatever its species ([msxdispersion.c:371](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L371)); a one-line fix.
- **The input check misses some cycles of `[TERMS]`.** It misses a term used with an operator next to it, such as `T2*2` ([msxinp.c:873](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxinp.c#L873)), and never checks the last term ([msxinp.c:1463](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxinp.c#L1463)). Unpatched, such a cycle overflows the stack; with BIT-02 interpreted chemistry reports error 506, but with the `COMPILER` option the generated `term()` function still recurses until the stack overflows ([msxcompiler.c:283](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxcompiler.c#L283)). Both modes need checking with a test.
- **Parameters set before `[COEFFICIENTS]` are overwritten.** A `[PARAMETERS]` section that comes first in the file (the manual allows any order) is overwritten by the coefficient's default ([msxinp.c:817](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxinp.c#L817)).
- **More threads after `MSXopen` crash.** The per-thread work arrays are sized for the thread count at `MSXopen`; raising it later leaves the new threads with null arrays ([msxchem.c:143](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L143), and the solvers' and dispersion's open functions).
- **Dispersion memory is never freed.** `msx_freesparse()` is never called, and the dispersion arrays leak on every `MSXopen`/`MSXclose` cycle: about 3 MB per cycle on a three-pipe model ([smatrix.c:161](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/smatrix.c#L161), [msxproj.c:531](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxproj.c#L531)).
- **Compiled tank formulas use a pipe's parameters and hydraulics** (the `COMPILER` option): `MSXgetTankFormulas` is passed the parameters of the last pipe the thread worked on ([msxchem.c:902](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L902)).
- **Compiled chemistry writes `ABS` as `abs()`**, the integer function, which clang rejects, so a model using `ABS` with the `COMPILER` option fails to open (error 522) ([mathexpr.c:853](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/mathexpr.c#L853)).
- **Dispersion ignores the linear solver's errors** ([msxdispersion.c:399](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L399)); no input that triggers it was found.
- **`FIXED` dispersion coefficients are multiplied by chlorine's molecular diffusivity** ([msxinp.c:1319](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxinp.c#L1319)), which looks unintended; a question for the maintainers.
- **The Windows Release build uses `/fp:fast`** ([src/solver/CMakeLists.txt:59](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/CMakeLists.txt#L59)), so Windows results can differ from other platforms', and the `x == x` test for NaN ([msxerr.c:92](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxerr.c#L92)) may be optimised away.
- Not yet confirmed: on Linux the compiled-chemistry library is opened by its bare name ([msxfuncs.c:74](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxfuncs.c#L74)), so the `COMPILER` option probably fails there; and the math error flag is written from several threads.
