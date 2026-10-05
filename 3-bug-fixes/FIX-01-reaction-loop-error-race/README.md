# FIX-01: Keep one pipe's reaction error from being lost to the next pipe's success

| | |
|---|---|
| **Category** | [Bug fix](../README.md): results are unchanged on every benchmark case |
| **Impact** | Wrong results with no error. When the integration or the equilibrium solve fails in a pipe, the pipe keeps concentrations that were never solved, the rest of the pipe is not reacted in that step, and the run reports success. With several threads, which code is returned is a data race. With the fix, such a model stops with error 513 or 514, as MSX 1.1 did. |
| **Reached from** | Any model in which RK5 or ROS2 fails to integrate, or Newton's method fails to solve the equilibria, in some pipe segment; through `runepanetmsx` or the toolkit (`MSXsolveQ`, `MSXstep`), at one thread or many |
| **Where** | `MSXchem_react()` in [`src/solver/msxchem.c:298`](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L298) |
| **Since** | EPANET-MSX 2.0: commit [98d0af2](https://github.com/USEPA/EPANETMSX/commit/98d0af2b12b814fd240534e9a481adb764caf940) (2021) made the reaction loop an OpenMP loop and commented out its early return. MSX 1.1 returned the error. |
| **Results** | <!-- results:FIX-01 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxchem.c` (+14 / -3 lines) |
| **Patch** | [`FIX-01.patch`](FIX-01.patch), first in the series; it applies on its own to 85a303d ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | none |

## The problem

At every quality step MSX reacts the water in every pipe: in each segment it integrates the rate expressions over the step (Euler, RK5 or ROS2), then solves the equilibrium expressions with Newton's method. Both can fail. RK5 and ROS2 fail when their step size shrinks to nothing, RK5 also when it needs too many steps, and ROS2 when its matrix is singular; Newton fails when its Jacobian is singular or it has not converged after 20 iterations. MSX should then stop with error 513 ("could not integrate reaction rate expressions") or 514 ("could not solve reaction equilibrium expressions").

In 85a303d the error is lost. Every pipe's return code is written into one shared variable, so the next pipe's 0 overwrites a failed pipe's 513 or 514. With one thread, an error survives only if it happens in the last pipe. With several, it survives only if its thread happens to write last. The run carries on, and nothing in the return codes or the report shows that, in the failed pipe:

- the failed segment kept its equilibrium species at their values from before the step (Newton's result is discarded), or took the integrator's last values;
- the segments upstream of it in the same pipe were not reacted at all in that step.

**A model that appears to run today can stop with error 514 (or 513) once FIX-01 is applied.** The error is real: it was there before, and was being lost. This was seen on one utility model: water entered the network through a junction that set no pH, so the chloramine equilibria had no solution in the segments that water reached, and the unpatched code reported results with unsolved equilibria. With FIX-01 the run stops at the first step where this happens.

## Why it happens

`MSXchem_react()` runs the pipes in an OpenMP loop:

```c
// src/solver/msxchem.c, MSXchem_react()
    int k, m;
    int errcode = 0;
    ...
// --- examine each link
#pragma omp parallel
{
    #pragma omp for private(k)
    for (k = 1; k <= MSX.Nobjects[LINK]; k++)
    {
        // --- skip non-pipe links

        if (MSX.Link[k].len == 0.0) continue;
        ...
         errcode = evalPipeReactions(k, dt);
        //if (errcode) return errcode;
    }
}
    if (errcode) return errcode;
```

`errcode` is declared outside the parallel region, so all threads share it, and every pipe writes it, whether it failed or not. The test after the loop sees only the last value written. MSX 1.1 had the same loop without OpenMP, and returned at the first error:

```c
        errcode = evalPipeReactions(k, dt);
        if ( errcode ) return errcode;
```

A `return` cannot leave an OpenMP loop, so when MSX 2.0 made the loop parallel, the test was commented out and moved after the loop. With one thread, the loop runs the pipes in index order and the last pipe's code wins. With several threads it is also a data race: threads write `errcode` at the same time without synchronisation, which C and OpenMP leave undefined. In practice the code returned depends on which thread writes last, so it can change from run to run and with the thread count.

Within a pipe, `evalPipeReactions()` ([msxchem.c:519](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L519)) returns at the first failure, before the segments upstream of it:

```c
// src/solver/msxchem.c, evalPipeReactions()
            if ( ierr < 0 ) return 
                ERR_INTEGRATOR;
    ...
    // --- compute new equilibrium concentrations within segment

        errcode = MSXchem_equil(LINK, k, TheSeg->c);
        if ( errcode ) return errcode;
```

and `evalPipeEquil()` ([msxchem.c:759](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L759)) returns `ERR_NEWTON` without copying Newton's iterate back, so the segment keeps its old values.

**Tank reactions do not have this problem.** The tank loop that follows runs on one thread and returns at the first non-zero code ([msxchem.c:323-324](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L323-L324)), so a tank's 513 or 514 stops the run. Equilibria computed outside the reaction step are a different matter: the water leaving a junction (`sourceInput()` and `findnodequal()`, [msxqual.c:1108](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1108), [1506](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1506) and [1519](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1519)), tank mixing ([msxtank.c:83](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxtank.c#L83), [185-186](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxtank.c#L185-L186)) and the initial segments ([msxqual.c:769](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L769), [797](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L797)) ignore `MSXchem_equil()`'s return code, so a failure there leaves the node's or tank's equilibrium species unsolved without an error. FIX-01 does not change those calls.

## How to reproduce

A reservoir feeds three junctions through three pipes in a line, P1, P2 and P3, for 6 hours with a 5-minute quality step (72 steps), with this reaction file:

```
[OPTIONS]
  AREA_UNITS FT2
  RATE_UNITS HR
  SOLVER     RK5
  TIMESTEP   300

[SPECIES]
  BULK A  MG
  BULK B  MG

[COEFFICIENTS]
  PARAMETER P 1.0

[PARAMETERS]
  PIPE P1 P 0.0

[PIPES]
  RATE  A  0
  EQUIL B  P*B - 1

[TANKS]
  RATE  A  0
  EQUIL B  B - 1

[QUALITY]
  GLOBAL A 1.0
  GLOBAL B 1.0
```

In P1, where P = 0, the equilibrium reads −1 = 0. It has no solution, Newton's Jacobian is 0, and `newton_solve()` reports a singular Jacobian at every step. In P2 and P3 the equilibrium is solved (B = 1).

- **Without the fix**, at one thread, `MSXstep` runs all 72 steps and returns 0 every time. B in P1 stays at its initial value, which was never solved for: P1's error is overwritten by P2's and P3's success.
- **With the fix**, the first `MSXstep` returns 514.

A test program, `FIX-01_test.c`, with its input files, will be added to this folder.

## The fix

```diff
 // --- examine each link
+//     (the largest error code found is returned whatever the number
+//     of threads, as the order in which links are done may vary)
+
 #pragma omp parallel
 {
+    int ierr;
     #pragma omp for private(k)
     for (k = 1; k <= MSX.Nobjects[LINK]; k++)
     {
 ...
-         errcode = evalPipeReactions(k, dt);
-        //if (errcode) return errcode;
+        // --- compute pipe reactions
+
+        ierr = evalPipeReactions(k, dt);
+        if (ierr)
+        {
+            #pragma omp critical
+            {
+                if (ierr > errcode) errcode = ierr;
+            }
+        }
     }
 }
     if (errcode) return errcode;
```

`ierr` is declared inside the parallel region, so each thread has its own. A pipe that succeeds writes nothing to the shared `errcode`; a pipe that fails merges its code into it inside a critical section, keeping the largest. The largest of a set of codes does not depend on the order in which they are found, so the same code is returned at any thread count and with any schedule: 514 if an equilibrium failed in some pipe in that step, otherwise 513 if an integration did. A `max` reduction would do the same, but it needs OpenMP 3.1, and MSVC supports only OpenMP 2.0. The critical section is entered only when a pipe fails, so a run without errors does not pay for it.

Unlike MSX 1.1, the loop does not stop at the first error, since neither `return` nor `break` can leave an OpenMP loop: the other pipes are still reacted in that step, and `MSXchem_react()` then returns the error before reacting the tanks. The run stops either way.

The bit-identical series builds on this change: [BIT-03](../../1-bit-identical/BIT-03-thread-state-without-tls/) rewrites the same loop, and [BIT-13](../../1-bit-identical/BIT-13-dynamic-omp-schedules/) gives it a dynamic schedule, which is safe because the code returned no longer depends on which thread does which pipe.

## Results with the fix

Results are identical on every benchmark case: none of them has an integration or equilibrium failure, so every pipe's code is 0, and the change only affects what is returned when one is not.

<!-- measured:FIX-01 -->
Each table compares 85a303d unpatched ("before") with FIX-01 on its own ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 12.8 | 12.7 | 1.01x | 3.25 | 3.22 | 1.01x | yes |
| Net6, chlorine bulk + wall | 11.2 | 11.2 | 1.00x | 3.52 | 2.89 | 1.22x | yes |
| KY8, chlorine + dispersion | 10.6 | 10.7 | 0.99x | 2.06 | 2.20 | 0.94x | yes |
| Richmond, bacterial regrowth | 15.2 | 15.1 | 1.00x | 3.29 | 3.26 | 1.01x | yes |
| Net3, chloramine decay | 11.4 | 11.6 | 0.99x | 3.01 | 3.14 | 0.96x | yes |
| Net3, arsenic adsorption | 2.59 | 2.58 | 1.00x | 0.702 | 0.656 | 1.07x | yes |
| MSX example (4 nodes) | 0.214 | 0.214 | 1.00x | 0.144 | 0.144 | 1.00x | yes |
| **Median** | | | **1.00x** | | | **1.01x** | |

To measure it yourself:

```sh
tools/try.py FIX-01
```
<!-- /measured -->
