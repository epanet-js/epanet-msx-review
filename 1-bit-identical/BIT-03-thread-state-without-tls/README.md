# BIT-03: Read per-thread chemistry and solver state once

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Chemistry and its solvers (multithreading) |
| **Results** | <!-- results:BIT-03 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxchem.c`, `msxutils.c`, `msxutils.h`, `newton.c`, `newton.h`, `rk5.c`, `rk5.h`, `ros2.c`, `ros2.h` (+304 / -228 lines) |
| **Patch** | [`BIT-03.patch`](BIT-03.patch), applied after FIX-01, FIX-02, BIT-01 and BIT-02 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | [FIX-01](../../3-bug-fixes/FIX-01-reaction-loop-error-race/): it rewrites the reaction loop in `MSXchem_react` that FIX-01 changes, and does not apply without it |
| **Also fixes** | none |

## What was slow

The chemistry keeps its working state in global variables marked `#pragma omp threadprivate`, so that each OpenMP thread has its own copy: the current segment, link, node and tank, the concentration vectors and the hydraulic variables ([msxchem.c:61](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L61)), and the work arrays of each solver ([rk5.c:31](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/rk5.c#L31), [ros2.c:28](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/ros2.c#L28), [newton.c:24](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/newton.c#L24)).

In a shared library on macOS, every access to such a variable is a call to the thread-local-variable thunk `_tlv_get_addr`: 12-18 % of all samples in the profiles of the unpatched code. The RK5, ROS2 and Newton solvers read their thread-local struct again inside their loops, after every derivative call. This is why the unpatched code built with OpenMP ran 5-9 % slower on one thread than the same code built without OpenMP.

[BIT-02](../BIT-02-terms-evaluated-once/) already removed most of this traffic along with the variable callback. What is left is the state itself, read in the innermost loops.

## What the change does

- One `threadprivate` pointer per thread, `Chem`, points to a `ChemState` struct that holds the thread's state. It is read once per thread per `MSXchem_react` (or per `MSXchem_equil` call) and passed down as an argument.
- It reaches the derivative and equilibrium callbacks through a new `void *data` argument of `rk5_integrate`, `ros2_integrate`, `newton_solve` and `jacobian`. These are internal functions, and `msxchem.c` is their only caller.
- The solvers copy their thread-local work struct into local variables once per call.
- As before, each thread's state is allocated in the parallel region of `MSXchem_open`.

With BIT-02, this removes the cost that the OpenMP build had against a build without OpenMP on one thread, on the cases whose time is in the chemistry. The dispersion code keeps thread-local arrays of its own ([msxdispersion.c:33](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxdispersion.c#L33)), which this change does not touch, so the KY8 dispersion case keeps part of that cost.

The cost of thread-local access was measured on macOS only. How much it costs elsewhere depends on the platform and on how the library is linked, so the gain there may differ.

## Why the results are unchanged

No arithmetic expression changes, only where the state is kept and how it is reached, so the compiler forms the same fused multiply-adds. Without OpenMP, `threadprivate` is ignored and `Chem` is an ordinary static variable, as the old globals were.

Beyond the benchmark cases at 1 and 8 threads, the change was checked in a build without OpenMP and with the compiled-chemistry option (`COMPILER`), whose functions are reached through the same callbacks.

## Measured

<!-- measured:BIT-03 -->
Each table compares the series up to BIT-02 ("before") with BIT-03 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 9.09 | 8.90 | 1.02x | 2.54 | 2.42 | 1.05x | yes |
| Net6, chlorine bulk + wall | 3.68 | 3.64 | 1.01x | 1.55 | 1.70 | 0.91x | yes |
| KY8, chlorine + dispersion | 3.88 | 3.98 | 0.98x | 1.09 | 1.13 | 0.97x | yes |
| Richmond, bacterial regrowth | 6.00 | 5.92 | 1.01x | 1.46 | 1.39 | 1.05x | yes |
| Net3, chloramine decay | 4.18 | 4.12 | 1.01x | 1.10 | 1.11 | 0.99x | yes |
| Net3, arsenic adsorption | 1.33 | 1.30 | 1.03x | 0.414 | 0.403 | 1.03x | yes |
| MSX example (4 nodes) | 0.138 | 0.136 | 1.02x | 0.106 | 0.105 | 1.01x | yes |
| **Median** | | | **1.01x** | | | **1.01x** | |

To measure it yourself:

```sh
tools/try.py BIT-03 --against BIT-02
```
<!-- /measured -->

## Tried and not kept

None.
