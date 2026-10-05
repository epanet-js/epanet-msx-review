# Verification

[All changes](README.md)

How each patch was checked, from the measurement runs in [results/](results/README.md): `series.json` and `near-series.json` (step mode), `verify-solve.json` (solve mode), `verify-output.json` (the output-heavy cases in step and read mode) and `verify-noomp.json` (every build without OpenMP).

After each patch, every case was run and its results compared with those of 85a303d, unpatched, built the same way:

- **Step** and **read** mode: a hash of every node's and every link's concentration of every species after every step, read with `MSXgetqual` as 64-bit values.
- **Solve** mode, as `runepanetmsx` runs: the same hash, plus the MD5 of the binary output file and of the report, without EPANET's date and time stamps.
- **No OpenMP**: the patch built without OpenMP, step mode, one thread, against 85a303d built with OpenMP.

A cell gives the number of runs whose results are byte-for-byte the same as 85a303d's, out of the runs made: 9 cases (the 7 main cases and the 2 output-heavy ones) in step and solve mode, the 2 output-heavy cases in read mode. BIT-01 changes only the CMake files, so its build is the same library as FIX-01 and FIX-02 together; it is listed for completeness. Each `only:NEAR-NN` is the bit-identical series plus that change alone, and `near` is all three.

<!-- verification -->
| Patch | Step, 1 thread | Step, 8 threads | Solve, 1 thread | Solve, 8 threads | Read, 1 thread | Read, 8 threads | No OpenMP, 1 thread |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [FIX-01](3-bug-fixes/FIX-01-reaction-loop-error-race/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [FIX-02](3-bug-fixes/FIX-02-zero-flow-segment-leak/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [FIX-03](3-bug-fixes/FIX-03-tempfile-descriptor-leak/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-01](1-bit-identical/BIT-01-build-defaults/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-02](1-bit-identical/BIT-02-terms-evaluated-once/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-03](1-bit-identical/BIT-03-thread-state-without-tls/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-04](1-bit-identical/BIT-04-pipe-invariant-cache/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-05](1-bit-identical/BIT-05-interpreter-dispatch/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-06](1-bit-identical/BIT-06-identical-segments-once/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-07](1-bit-identical/BIT-07-solver-shortcuts/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-08](1-bit-identical/BIT-08-euler-lanes/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-09](1-bit-identical/BIT-09-segment-advection/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-10](1-bit-identical/BIT-10-transport-plan-prefetch/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-11](1-bit-identical/BIT-11-dispersion-mass-without-locks/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-12](1-bit-identical/BIT-12-dispersion-solve/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-13](1-bit-identical/BIT-13-dynamic-omp-schedules/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-14](1-bit-identical/BIT-14-report-and-output-file/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-15](1-bit-identical/BIT-15-link-averages-once/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-16](1-bit-identical/BIT-16-epanet-savehydfile-block-copy/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [BIT-17](1-bit-identical/BIT-17-compact-segments/) | 9/9 | 9/9 | 9/9 | 9/9 | 2/2 | 2/2 | 9/9 |
| [only:NEAR-01](2-near-identical/NEAR-01-reassociate-expressions/) | 3/9 | 3/9 | 3/9 | 3/9 | 2/2 | 2/2 | 3/9 |
| [only:NEAR-02](2-near-identical/NEAR-02-forward-difference-jacobians/) | 7/9 | 7/9 | 7/9 | 7/9 | 1/2 | 1/2 | 7/9 |
| [only:NEAR-03](2-near-identical/NEAR-03-dispersion-pivot-chain/) | 8/9 | 8/9 | 8/9 | 8/9 | 2/2 | 2/2 | 8/9 |
| `near` | 1/9 | 1/9 | 1/9 | 1/9 | 1/2 | 1/2 | 1/9 |
<!-- /verification -->

For the near-identical changes, how far the results move, and why that is acceptable, is in [the acceptance table](2-near-identical/README.md#the-acceptance-table). Their results do not depend on the thread count either: each gives the same bits at 1, 8 and 10 threads and built without OpenMP ([the thread check](2-near-identical/README.md#results-do-not-depend-on-the-thread-count)).

Not covered by the table:

- **The bugs the fixes are about.** FIX-01, FIX-02 and FIX-03 leave the benchmark results unchanged; each fix's README describes how its bug was reproduced. Their test programs are not yet in the repository.
- **The larger networks and the utility models**, which were checked with a single run at 1 and 8 threads in step mode: see [the README](README.md#larger-networks).
- **Newer MSX.** [status.md](status.md) records whether the bit-identical patches still leave the results of the latest `dev` unchanged.
