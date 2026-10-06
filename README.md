# Faster EPANET-MSX without changing the math

Oct 5, 2026 · @Luke

## Summary

On seven test cases built from the reaction systems in the EPANET-MSX manual, the 17 groups of bit-identical changes here make the median case **<!-- hl:bit1 -->15.7x<!-- /hl:bit1 --> faster with one thread and <!-- hl:bit8 -->9.1x<!-- /hl:bit8 --> faster with eight**, and every concentration at every step, the binary output file and the report are **bit-for-bit the same** as before. Three near-identical changes take the median to **<!-- hl:near1 -->17.0x<!-- /hl:near1 --> and <!-- hl:near8 -->10.7x<!-- /hl:near8 -->**; they move results at the level of rounding, about as much as the unpatched code already varies between platforms (at the limit of the acceptance rule on one case). Even on one thread, the patched code with every change is <!-- hl:near1v8 -->4.5x<!-- /hl:near1v8 --> faster in the median case than the unpatched code on eight threads (<!-- hl:near1v8range -->1.7-6.3x<!-- /hl:near1v8range -->; <!-- hl:bit1v8 -->4.2x<!-- /hl:bit1v8 --> with the bit-identical changes alone). Three bug fixes found on the way come first in the series; they leave every benchmark result unchanged.

The numerical methods are unchanged: the same Lagrangian transport, the same integrators (Euler, RK5, ROS2), the same Newton solver for equilibria, the same dispersion model. The time was going into the work around the math:

- **The expression interpreter re-did work.** Every `[TERMS]` entry was evaluated again each time it was referenced, recursively, in every segment of every pipe at every step, including terms such as `Re^0.88` that change only when the hydraulics do. About two-thirds to three-quarters of the unpatched run time was the interpreter.
- **Identical segments were integrated one by one.** Every pipe starts as 100 segments of the same water, and many stay identical, but each was integrated on its own, every step. On BWSN2 that was most of what was left after the interpreter was fixed.
- **Per-thread variables were expensive.** OpenMP's `threadprivate` variables cost a function call on each access in a shared library on macOS (12-18 % of the time).
- **Threads waited on each other.** A lock taken twice per pipe in the dispersion code, once the chemistry was fast, kept the dispersion case from getting faster beyond four threads, and the reaction loop gave each thread an equal number of pipes rather than an equal amount of work.
- **Files were read and written one value at a time**, and the hydraulics and output files were copied one byte at a time.
- **The build itself**: following the README with the default CMake generator compiles with no optimisation, and on macOS without OpenMP.

Every change has its own folder with a write-up, its measurements and a patch against EPANET-MSX at [85a303d](https://github.com/USEPA/EPANETMSX/commit/85a303dca05859389eced63fabd5ea145c096333) (the head of `main`, with its EPANET2.2 submodule at 1e2fc3d). The scripts in [tools/](benchmarking.md#scripts) build MSX with any part of the series and time it, so you can check every number here:

- on **MSX 85a303d**, the version the patches were written against;
- **with the patches**, one group at a time or all together;
- on **the latest MSX**, or any pull request, to see whether the patches still apply and still leave results unchanged ([status.md](status.md));
- on **your own models**, which you put in a folder that git ignores, and report back without sharing them ([see below](#your-own-models)).

```sh
git clone --recurse-submodules https://github.com/epanet-js/epanet-msx-review.git
cd epanet-msx-review
tools/try.py bit near --quick        # 85a303d against the patches, on this machine (the near-identical
                                     # verdicts need numpy, and build the platform samples the first time)
```

[reproducing.md](reproducing.md) goes through each claim, and [benchmarking.md](benchmarking.md) explains the tools.

## Headline numbers

The figures are the median speed-up per case over the seven main cases, each build against the unpatched code at the same thread count, so no single case can inflate them. Times are whole runs: opening the files, hydraulics and water quality. <!-- machine -->Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG` with OpenMP, measured 2026-10-05<!-- /machine -->.

<!-- headline -->
| How MSX is run | Median, bit-identical | Median, plus near-identical | Range, bit-identical | Range, plus near-identical |
| --- | ---: | ---: | ---: | ---: |
| Step (`MSXstep` loop), 1 thread | 15.72x | 16.98x | 3.38x-21.42x | 3.39x-26.83x |
| Step (`MSXstep` loop), 8 threads | 9.07x | 10.65x | 2.06x-16.74x | 2.07x-19.65x |
| Step (`MSXstep` loop), all cores (default) | 9.84x | 9.49x | 2.03x-20.00x | 2.11x-19.86x |
| Solve (as `runepanetmsx`), 1 thread | 16.89x | 16.99x | 3.41x-21.54x | 3.47x-25.30x |
| Solve (as `runepanetmsx`), 8 threads | 9.01x | 9.10x | 2.22x-19.40x | 2.20x-20.63x |
| Solve (as `runepanetmsx`), all cores (default) | 10.11x | 10.90x | 2.09x-118.99x | 2.10x-132.15x |
<!-- /headline -->

**These tables come from one quick pass** (`QUICK=1 tools/run-all.sh`: one timed run per build, on a machine in use, with the load average recorded), so single values can be a few per cent off at one thread and more at eight. `tools/run-all.sh` remakes every table as the best of a checked run and 5 timed runs, interleaved (about 6 hours), and `tools/update-docs.py` writes them into these pages. One value in this pass is not noise: in solve mode with all 10 cores, while the machine was busy (load average about 18), the unpatched KY8 dispersion case took 30-35 s, against 8 s on 8 threads in the same pass and about 2.4 s on 8 threads in step mode. The solve-mode rows at 8 threads and all cores were measured while the machine was busy (load average 18 rising to 35) and are the least reliable here. Its dispersion code takes a lock twice per pipe ([BIT-11](1-bit-identical/BIT-11-dispersion-mass-without-locks/)), and the likely cause is that when the system takes a core away from the thread holding the lock, every other thread waits for it; the patched builds, which take no lock there, ran normally in the same minutes. That is the top of the range in the last row.

Per case, step mode, seconds: each build on one and on eight threads, then the patched code with every change against the unpatched code on eight threads, first with the patched code on one thread and then on eight. The headline table above compares builds at the same thread count.

<!-- permodel -->
| Case | Unpatched, 1 thread (s) | Unpatched, 8 threads | Bit-identical, 1 thread | Bit-identical, 8 threads | Plus near-identical, 1 thread | Plus near-identical, 8 threads | Near-identical on 1 thread against unpatched on 8 | Near-identical against unpatched, both on 8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BWSN2, two-source chlorine | 13.1 | 3.46 | 0.831 | 0.335 | 0.770 | 0.324 | 4.49x | 10.65x |
| Net6, chlorine bulk + wall | 10.9 | 2.90 | 0.510 | 0.372 | 0.498 | 0.377 | 5.83x | 7.69x |
| KY8, chlorine + dispersion | 10.1 | 2.40 | 0.520 | 0.264 | 0.378 | 0.192 | 6.33x | 12.45x |
| Richmond, bacterial regrowth | 15.5 | 3.27 | 0.728 | 0.196 | 0.607 | 0.167 | 5.39x | 19.65x |
| Net3, chloramine decay | 11.5 | 2.89 | 1.25 | 0.277 | 0.878 | 0.199 | 3.29x | 14.54x |
| Net3, arsenic adsorption | 2.58 | 0.678 | 0.438 | 0.148 | 0.411 | 0.139 | 1.65x | 4.88x |
| MSX example (4 nodes) | 0.214 | 0.137 | 63.2 ms | 66.3 ms | 63.0 ms | 66.2 ms | 2.17x | 2.07x |
| **Median** | | | | | | | **4.49x** | **10.65x** |
<!-- /permodel -->

<!-- hl:extremes -->At one thread the bit-identical gain is smallest on MSX example (4 nodes) (3.38x) and Net3, arsenic adsorption (5.90x), and largest on Net6, chlorine bulk + wall (21.42x) and Richmond, bacterial regrowth (21.32x).<!-- /hl:extremes -->

## Test cases

The seven main cases pair public networks with the reaction systems of the MSX manual's examples ([models/README.md](models/README.md) has their origin, licences and edits):

| Case | Network | Reactions | Integrator | What it exercises |
|---|---|---|---|---|
| BWSN2, two-source chlorine | BWSN2, 14,822 pipes | Manual listing 5.1 | RK5 | A large network with cheap chemistry |
| Net6, chlorine bulk + wall | Net6, 3,829 pipes, 32 tanks | Listing 5.2 without dispersion | Euler | Terms with `pow`, many tanks |
| KY8, chlorine + dispersion | KY8, 1,614 pipes | Listing 5.2 | Euler | Dispersion |
| Richmond, bacterial regrowth | Richmond, 949 pipes | Listing 5.4 | RK5 | Wall species, terms, formulas |
| Net3, chloramine decay | Net3, 117 pipes | Listing 5.5 | ROS2 | 14 species, 6 equilibria, 13 terms |
| Net3, arsenic adsorption | Net3 | Listing 5.3 | RK5 | Wall species, an equilibrium |
| MSX example | The manual's 4-node network | Section 3 | RK5 | A tiny network |

Two more cases report every node, link and species every 5 minutes, to measure the output code ([BIT-14](1-bit-identical/BIT-14-report-and-output-file/), [BIT-15](1-bit-identical/BIT-15-link-averages-once/)), two stress cases exercise water age and full coupling ([below](#stress-cases)), and two larger real-world networks run with three kinds of reactions each ([below](#larger-networks)).

## How this is organised

| Folder | |
|---|---|
| [1-bit-identical/](1-bit-identical/README.md) | 17 groups of changes that leave every result byte-for-byte the same: `BIT-01` to `BIT-17` |
| [2-near-identical/](2-near-identical/README.md) | 3 changes that move results by rounding, about as much as MSX already varies between platforms: `NEAR-01` to `NEAR-03` |
| [3-bug-fixes/](3-bug-fixes/README.md) | 3 bugs found on the way, fixed without changing any benchmark result: `FIX-01` to `FIX-03`; and the bugs found but not yet written up |
| [models/](models/README.md) | The networks, the reaction files and `cases.json`; `private/` for your own |
| [tools/](benchmarking.md#scripts) | Scripts to build, time and compare MSX |
| [results/](results/README.md) | The measurements behind every table here |
| `msx` | Submodule: EPANET-MSX at 85a303d |

Each folder has a write-up (`README.md`): what was slow, what the change does (step by step where a group merges several changes), why the results are unchanged or how far they move, its measurements, and what was tried and not kept. It also has the patch, `<ID>.patch`, whose header says what it changes, what it requires and whether its results are identical. The patches form one series: FIX-01 to FIX-03 first, each of which applies on its own; then BIT-01 to BIT-17, built on FIX-01 and FIX-02, each on top of the ones before it; then NEAR-01 to NEAR-03, each of which applies on its own after BIT-17. [BIT-16](1-bit-identical/BIT-16-epanet-savehydfile-block-copy/) is a patch to the EPANET2.2 submodule; all the others are patches to MSX.

## Bit-identical changes (17)

Each group performs the same floating-point operations in the same order. Every concentration of every species at every node and link after every step, the binary output file and the report are byte-for-byte unchanged after every group, on all nine cases, at 1 and 8 threads and built without OpenMP. [The category page](1-bit-identical/README.md) describes each group in a paragraph. "Measured" is that group added to the ones before it, whole runs, step mode, one thread unless stated.

<!-- bit-index -->
| ID | What changes | Area | Measured, this change alone |
|---|---|---|---|
| [BIT-01](1-bit-identical/BIT-01-build-defaults/) | Release build by default; find Homebrew's libomp on macOS | Build | <!-- summary:BIT-01 -->no optimisation to `-O3`: 1.84x median; OpenMP found on macOS: the unpatched code on 8 threads 3.54x faster than without OpenMP (median)<!-- /summary --> |
| [BIT-02](1-bit-identical/BIT-02-terms-evaluated-once/) | Terms and formulas evaluated once per rate evaluation, not per reference | Chemistry | <!-- summary:BIT-02 -->2.50x median, up to 3.00x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-03](1-bit-identical/BIT-03-thread-state-without-tls/) | Thread-local chemistry and solver state looked up once per call | Chemistry, threads | <!-- summary:BIT-03 -->within noise on these cases<!-- /summary --> |
| [BIT-04](1-bit-identical/BIT-04-pipe-invariant-cache/) | Terms and sub-expressions that depend only on hydraulics, cached per pipe | Chemistry | <!-- summary:BIT-04 -->up to 3.39x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-05](1-bit-identical/BIT-05-interpreter-dispatch/) | Fused operands, joined programs, threaded dispatch and exact expression rewrites | Chemistry | <!-- summary:BIT-05 -->1.45x median, up to 2.27x (Net3, chloramine decay)<!-- /summary --> |
| [BIT-06](1-bit-identical/BIT-06-identical-segments-once/) | Runs of bit-identical segments integrated once, the results copied | Chemistry | <!-- summary:BIT-06 -->1.15x median, up to 5.49x (BWSN2, two-source chlorine)<!-- /summary --> |
| [BIT-07](1-bit-identical/BIT-07-solver-shortcuts/) | Newton tolerance computed once; all-zero ROS2 Jacobian columns skipped | Chemistry | <!-- summary:BIT-07 -->up to 1.05x (Net3, chloramine decay)<!-- /summary --> |
| [BIT-08](1-bit-identical/BIT-08-euler-lanes/) | Euler rate program run for eight segments per dispatch | Chemistry | <!-- summary:BIT-08 -->up to 1.23x (KY8, chlorine + dispersion)<!-- /summary --> |
| [BIT-09](1-bit-identical/BIT-09-segment-advection/) | Wall-species shift in one pass; new segments only when one is added | Transport | <!-- summary:BIT-09 -->1.09x median, up to 1.31x (MSX example (4 nodes))<!-- /summary --> |
| [BIT-10](1-bit-identical/BIT-10-transport-plan-prefetch/) | Each node's links listed once per hydraulic step; end segments prefetched | Transport | <!-- summary:BIT-10 -->up to 1.08x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-11](1-bit-identical/BIT-11-dispersion-mass-without-locks/) | Dispersed mass summed per pipe after the loop, without locks | Dispersion | <!-- summary:BIT-11 -->at 8 threads up to 1.60x (KY8, chlorine + dispersion)<!-- /summary --> |
| [BIT-12](1-bit-identical/BIT-12-dispersion-solve/) | One factorisation per pipe, solved into segments; coefficients and segment lists kept | Dispersion | <!-- summary:BIT-12 -->up to 1.67x (KY8, chlorine + dispersion); at 8 threads up to 1.42x (KY8, chlorine + dispersion)<!-- /summary --> |
| [BIT-13](1-bit-identical/BIT-13-dynamic-omp-schedules/) | Dynamic OpenMP schedules for the pipe reaction and dispersion loops | Multithreading | <!-- summary:BIT-13 -->at 8 threads up to 1.37x (Net3, chloramine decay)<!-- /summary --> |
| [BIT-14](1-bit-identical/BIT-14-report-and-output-file/) | Report and output file in blocks; numbers formatted without printf | Output and report files | <!-- summary:BIT-14 -->output-heavy cases, one thread: BWSN2 solve mode 3.70x, Net3 chloramine solve mode 2.01x<!-- /summary --> |
| [BIT-15](1-bit-identical/BIT-15-link-averages-once/) | One segment walk per link when saving results and in MSXgetqual | Output and toolkit | <!-- summary:BIT-15 -->output-heavy cases, one thread: BWSN2 read mode 1.27x, BWSN2 solve mode 1.22x<!-- /summary --> |
| [BIT-16](1-bit-identical/BIT-16-epanet-savehydfile-block-copy/) | EN_savehydfile copies the hydraulics file 64 KB at a time | EPANET 2.2 | <!-- summary:BIT-16 -->MSXsolveH 3.35x median, up to 3.95x (Net6, chlorine bulk + wall); whole run up to 1.26x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-17](1-bit-identical/BIT-17-compact-segments/) | Segments copied into contiguous memory once per hydraulic step (more memory) | Transport | <!-- summary:BIT-17 -->up to 1.38x (KY8, chlorine + dispersion); at 8 threads 1.07x median, up to 1.16x (Richmond, bacterial regrowth)<!-- /summary --> |
<!-- /bit-index -->

## Near-identical changes (3)

**These change results**, at the level of rounding: within tolerance where the unpatched code's own results agree between platforms (built with and without fused multiply-add, and for x86-64), and within twice the platforms' spread where they do not; NEAR-01 is at that limit on Net3 arsenic. Each was judged on its own, on top of the bit-identical series. [The category page](2-near-identical/README.md) explains how "within tolerance" was decided, shows how much the unpatched code varies between platforms, and has the acceptance table and its limitations.

<!-- near-index -->
| ID | What changes | Area | Measured, this change alone |
|---|---|---|---|
| [NEAR-01](2-near-identical/NEAR-01-reassociate-expressions/) | Regroup rate expressions so more of each is cached per pipe | Chemistry (expression interpreter) | <!-- summary:NEAR-01 -->1.03x median, up to 1.14x (Richmond, bacterial regrowth)<!-- /summary --> |
| [NEAR-02](2-near-identical/NEAR-02-forward-difference-jacobians/) | One forward-difference Jacobian helper for ROS2 and Newton's method | Chemistry (integrator and equilibrium solver) | <!-- summary:NEAR-02 -->up to 1.43x (Net3, chloramine decay); at 8 threads up to 1.38x (Net3, chloramine decay)<!-- /summary --> |
| [NEAR-03](2-near-identical/NEAR-03-dispersion-pivot-chain/) | Dispersion pivots as ratios of determinants, solved while built | Dispersion | <!-- summary:NEAR-03 -->up to 1.34x (KY8, chlorine + dispersion)<!-- /summary --> |
<!-- /near-index -->

## Bug fixes (3)

These come first in the series. Each applies on its own to 85a303d and leaves every benchmark result unchanged. [The category page](3-bug-fixes/README.md) also lists three bugs fixed as part of a performance change and the bugs found but not yet written up.

<!-- fix-index -->
| ID | What changes | Area | Measured, this change alone |
|---|---|---|---|
| [FIX-01](3-bug-fixes/FIX-01-reaction-loop-error-race/) | A failed pipe's error code is no longer overwritten by later pipes | Chemistry (reaction loop, multithreading) | <!-- summary:FIX-01 -->no change beyond noise (1.00x median at one thread)<!-- /summary --> |
| [FIX-02](3-bug-fixes/FIX-02-zero-flow-segment-leak/) | Links without flow no longer take a segment that is never returned | Transport (pipe segments) | <!-- summary:FIX-02 -->no change beyond noise (1.01x median at one thread)<!-- /summary --> |
| [FIX-03](3-bug-fixes/FIX-03-tempfile-descriptor-leak/) | Close the descriptor mkstemp opens for each temporary file name | Files (temporary files) | <!-- summary:FIX-03 -->no change beyond noise (1.00x median at one thread)<!-- /summary --> |
<!-- /fix-index -->

**FIX-01 can stop a model that appears to run today.** With it, a model whose equilibrium or integration fails in some pipes stops with error 513 or 514 instead of reporting concentrations that were never solved. The error is real; the unpatched code was losing it. It happened on one of the utility models below.

## Multithreading

MSX parallelises three things with OpenMP: the reaction loop over pipes (`MSXchem_react`), the two loops over pipes in the dispersion code, and, with [BIT-15](1-bit-identical/BIT-15-link-averages-once/), the averaging of link concentrations when results are saved. Everything else runs on one thread: reading hydraulics, moving water through the nodes in topological order (sequential by nature), tanks, and EPANET's own hydraulics.

**What was in the way:**

- **No threads at all on macOS** ([BIT-01](1-bit-identical/BIT-01-build-defaults/)): CMake does not find Homebrew's keg-only libomp, so the library is built single-threaded.
- **Per-thread variables cost a call on every access** ([BIT-03](1-bit-identical/BIT-03-thread-state-without-tls/)): in a shared library on macOS, each access to a `threadprivate` variable goes through `_tlv_get_addr`, and the chemistry and the three integrators touched them in their innermost loops (12-18 % of all samples). Unpatched, the OpenMP build at one thread was 5-9 % slower than a build without OpenMP; with BIT-02 and BIT-03 the gap is within a few per cent ([build flavours](#build-flavours)).
- **A lock taken twice per pipe in the dispersion code** ([BIT-11](1-bit-identical/BIT-11-dispersion-mass-without-locks/)): every thread added its pipes' dispersed mass to one total inside `#pragma omp critical`. At 8 threads the main thread spent three-quarters of `segqual_update` waiting for the lock. Once the chemistry was fast, this, not the chemistry, is what kept the KY8 case from getting faster beyond 4 threads. Summing per pipe in pipe order also makes the mass balance the same at any thread count.
- **Equal numbers of pipes, unequal work** ([BIT-13](1-bit-identical/BIT-13-dynamic-omp-schedules/)): the loops used OpenMP's default static schedule, but the work per pipe is proportional to its number of water parcels, from 1 to over 300, and two of an M1 Pro's ten cores are slower efficiency cores. A dynamic schedule hands out a few pipes at a time.
- **A data race on the reaction loop's error code** ([FIX-01](3-bug-fixes/FIX-01-reaction-loop-error-race/)): every thread wrote the shared `errcode`, so an error in one pipe could be overwritten by the next pipe's success.

**Where it stands now.** <!-- hl:scaling -->From one to eight threads the bit-identical build speeds up 4.5x on Net3, chloramine decay and 3.7x on Richmond, bacterial regrowth, against 3.9x and 4.6x for the unpatched code. Where the chemistry is now cheap it scales less, because the serial parts (moving water through the nodes, tanks, hydraulics) are a larger share: 1.4x on Net6, chlorine bulk + wall and 1.0x on MSX example (4 nodes).<!-- /hl:scaling --> With the dynamic schedules, 8 and 10 threads give much the same times; OpenMP uses every core by default (10 on an M1 Pro, two of them efficiency cores).

### Thread scaling

Whole runs, seconds, step mode. "Unpatched" is 85a303d built with OpenMP and `-O3`. macOS users following its README got neither: no optimisation and no threads, the `-O0` column of [the build flavours](#build-flavours) whatever their thread count.

<!-- scaling -->
| Case | Build | 1 thr | 2 thr | 4 thr | 6 thr | 8 thr | 10 thr |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BWSN2, two-source chlorine | unpatched | 12.8 | 7.64 | 5.23 | 3.85 | 3.46 | 3.35 |
| BWSN2, two-source chlorine | bit-identical | 0.757 | 0.566 | 0.410 | 0.370 | 0.368 | 0.332 |
| BWSN2, two-source chlorine | plus near-identical | 0.757 | 0.535 | 0.402 | 0.361 | 0.399 | 0.365 |
| Net6, chlorine bulk + wall | unpatched | 11.3 | 6.41 | 3.93 | 3.27 | 3.00 | 2.86 |
| Net6, chlorine bulk + wall | bit-identical | 0.523 | 0.401 | 0.373 | 0.380 | 0.383 | 0.398 |
| Net6, chlorine bulk + wall | plus near-identical | 0.506 | 0.392 | 0.356 | 0.362 | 0.366 | 0.395 |
| KY8, chlorine + dispersion | unpatched | 10.6 | 5.64 | 3.26 | 2.45 | 2.00 | 2.77 |
| KY8, chlorine + dispersion | bit-identical | 0.535 | 0.321 | 0.237 | 0.206 | 0.209 | 0.224 |
| KY8, chlorine + dispersion | plus near-identical | 0.397 | 0.254 | 0.195 | 0.178 | 0.176 | 0.194 |
| Richmond, bacterial regrowth | unpatched | 15.3 | 9.00 | 5.68 | 4.02 | 3.36 | 3.26 |
| Richmond, bacterial regrowth | bit-identical | 0.712 | 0.400 | 0.246 | 0.222 | 0.194 | 0.185 |
| Richmond, bacterial regrowth | plus near-identical | 0.599 | 0.346 | 0.222 | 0.182 | 0.173 | 0.172 |
| Net3, chloramine decay | unpatched | 11.5 | 6.64 | 3.77 | 4.15 | 2.93 | 2.86 |
| Net3, chloramine decay | bit-identical | 1.26 | 0.655 | 0.392 | 0.333 | 0.277 | 0.273 |
| Net3, chloramine decay | plus near-identical | 0.884 | 0.462 | 0.284 | 0.237 | 0.201 | 0.206 |
| Net3, arsenic adsorption | unpatched | 2.58 | 1.49 | 0.894 | 0.818 | 0.684 | 0.675 |
| Net3, arsenic adsorption | bit-identical | 0.444 | 0.268 | 0.155 | 0.181 | 0.146 | 0.158 |
| Net3, arsenic adsorption | plus near-identical | 0.411 | 0.238 | 0.153 | 0.153 | 0.161 | 0.147 |
| MSX example (4 nodes) | unpatched | 0.215 | 0.181 | 0.129 | 0.138 | 0.148 | 0.154 |
| MSX example (4 nodes) | bit-identical | 64.1 ms | 50.0 ms | 50.2 ms | 59.8 ms | 65.4 ms | 72.1 ms |
| MSX example (4 nodes) | plus near-identical | 64.0 ms | 49.2 ms | 49.5 ms | 60.3 ms | 63.1 ms | 72.8 ms |

Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 8.4 at the start and 20.3 at the end; measured 2026-10-05.
<!-- /scaling -->

### Build flavours

One thread, whole runs, seconds. `-O0` is what a plain `cmake -B build .` with the Makefile generator compiles ([BIT-01](1-bit-identical/BIT-01-build-defaults/)).

<!-- flavours -->
| Case | `-O0` (plain `cmake`) | `-O3`, OpenMP (unpatched) | `-O3`, no OpenMP | Bit-identical, no OpenMP | Bit-identical, OpenMP | Plus near-identical, no OpenMP | Plus near-identical, OpenMP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BWSN2, two-source chlorine | 23.3 | 12.7 | 11.8 | 0.739 | 0.737 | 0.721 | 0.737 |
| Net6, chlorine bulk + wall | 20.3 | 10.9 | 10.3 | 0.508 | 0.533 | 0.495 | 0.506 |
| KY8, chlorine + dispersion | 18.7 | 10.1 | 9.56 | 0.487 | 0.523 | 0.377 | 0.381 |
| Richmond, bacterial regrowth | 26.3 | 15.1 | 14.4 | 0.710 | 0.706 | 0.586 | 0.603 |
| Net3, chloramine decay | 19.7 | 11.3 | 10.4 | 1.26 | 1.24 | 0.878 | 0.876 |
| Net3, arsenic adsorption | 4.77 | 2.55 | 2.36 | 0.431 | 0.436 | 0.407 | 0.408 |
| MSX example (4 nodes) | 0.417 | 0.213 | 0.198 | 62.4 ms | 63.0 ms | 60.8 ms | 61.9 ms |

One thread. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 6.5 at the start and 8.4 at the end; measured 2026-10-05.
<!-- /flavours -->

## Output-heavy cases

Every node, link and species reported every 5 minutes. **solve** runs as `runepanetmsx` does (`MSXreport`, `MSXsaveoutfile`); **read** reads every node and link value with `MSXgetqual` after every step, as many toolkit programs do. Whole runs and the report-and-save phase, seconds.

<!-- output -->
| Case | Mode | Threads | Unpatched (s) | Bit-identical | Plus near-identical | Speed-up | Report and save, unpatched | Bit-identical | Identical |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | solve | 1 | 10.2 | 1.31 | 1.41 | 7.22x | 6.66 | 0.304 | yes |
| BWSN2, 2 species, every node and link every 5 min | solve | 8 | 8.79 | 1.00 | 0.963 | 9.13x | 6.59 | 0.304 | yes |
| BWSN2, 2 species, every node and link every 5 min | read | 1 | 3.89 | 1.14 | 1.15 | 3.39x |  |  | yes |
| BWSN2, 2 species, every node and link every 5 min | read | 8 | 2.62 | 0.807 | 0.797 | 3.29x |  |  | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | solve | 1 | 12.8 | 1.29 | 0.933 | 13.68x | 1.38 | 33.2 ms | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | solve | 8 | 4.31 | 0.327 | 0.260 | 16.59x | 1.35 | 40.3 ms | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | read | 1 | 11.5 | 1.25 | 0.901 | 12.76x |  |  | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | read | 8 | 3.06 | 0.302 | 0.233 | 13.12x |  |  | yes |

Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; solve and read mode, best of two runs per build (a checked run and a timed run); load average 12.9 at the start and 6.5 at the end; measured 2026-10-05.
<!-- /output -->

Most of the gain in solve mode on BWSN2 is [BIT-14](1-bit-identical/BIT-14-report-and-output-file/): reading the results back for the report in blocks, and formatting them without `printf`, takes the report-and-save phase from several seconds to a few tenths of a second (the last two columns). In read mode, [BIT-15](1-bit-identical/BIT-15-link-averages-once/) lets `MSXgetqual` average each link's segments once for all species. On Net3 chloramine, with 14 species and a small network, the chemistry still dominates, so the gain follows the main cases.

## Stress cases

Two more public cases exercise paths the main cases do not (`--cases stress`). **Water age** keeps water parcels from merging, because neighbouring parcels never have the same age, so the number of segments grows through the run and moving water through the network becomes the main cost: BWSN2 for 48 hours, with water age and the share of the water from each of its two reservoirs. **Full coupling** (`COUPLING FULL`) solves the equilibria again inside every derivative evaluation, the heaviest chemistry path in MSX: Net3 chloramine as in the main case, with full coupling. One checked run per build, in the same layout as the per-case table above; solve mode was checked too.

<!-- stress -->
| Case | Unpatched, 1 thread (s) | Unpatched, 8 threads | Bit-identical, 1 thread | Bit-identical, 8 threads | Plus near-identical, 1 thread | Plus near-identical, 8 threads | Near-identical on 1 thread against unpatched on 8 | Near-identical against unpatched, both on 8 | Bit-identical results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | 22.9 | 9.07 | 4.50 | 2.30 | 4.46 | 3.65 | 2.03x | 2.48x | identical |
| Net3, chloramine decay with full coupling (ROS2) | 41.1 | 11.0 | 7.14 | 1.49 | 3.29 | 0.730 | 3.34x | 15.09x | identical |
| **Median** | | | | | | | **2.69x** | **8.78x** | |

Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, one checked and timed run per build; load average 10.3 at the start and 9.9 at the end; measured 2026-10-05.
<!-- /stress -->

Every build gave identical results on both cases in step and solve mode, and the near-identical changes pass the acceptance rule on both ([the near-identical page](2-near-identical/README.md#the-stress-cases)). Full coupling gains most from [NEAR-02](2-near-identical/NEAR-02-forward-difference-jacobians/), whose forward-difference Jacobian runs inside every derivative evaluation there. Water age gains least: its rates are a constant, so the chemistry changes have little to save, and what remains is moving water through the nodes, which runs on one thread. The near-identical changes do not touch that case's arithmetic (its results are bit for bit those of the bit-identical build), so the difference between them at 8 threads is noise.

## Larger networks

Two public networks with three kinds of reactions each, in the same layout as the per-case table above: L-Town (the BattLeDIM 2020 network, 905 pipes, 24 hours of its 5-minute demand patterns) and the NW Model (a 9,979-pipe system with pumps and rules, 12 hours), each with the manual's chlorine bulk and wall decay (Euler), bacterial regrowth (RK5) and chloramine decomposition (ROS2), with sources at the networks' reservoirs (`--cases real`). Whole runs, step mode, one checked run each.

<!-- real -->
| Case | Unpatched, 1 thread (s) | Unpatched, 8 threads | Bit-identical, 1 thread | Bit-identical, 8 threads | Plus near-identical, 1 thread | Plus near-identical, 8 threads | Near-identical on 1 thread against unpatched on 8 | Near-identical against unpatched, both on 8 | Bit-identical results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | 3.54 | 1.35 | 0.258 | 0.281 | 0.223 | 0.294 | 6.06x | 4.59x | identical |
| L-Town 24 h, bacterial regrowth (RK5) | 5.77 | 1.65 | 0.911 | 0.260 | 0.768 | 0.262 | 2.15x | 6.31x | identical |
| L-Town 24 h, chloramine decay (ROS2) | 51.0 | 10.6 | 5.56 | 1.07 | 3.93 | 0.807 | 2.70x | 13.16x | identical |
| NW Model 12 h, chlorine bulk + wall (Euler) | 65.4 | 14.0 | 1.93 | 0.964 | 1.86 | 0.952 | 7.52x | 14.71x | identical |
| NW Model 12 h, bacterial regrowth (RK5) | 134 | 26.6 | 13.7 | 2.90 | 11.7 | 2.81 | 2.28x | 9.49x | identical |
| NW Model 12 h, chloramine decay (ROS2) | 690 | 118 | 21.5 | 5.31 | 15.5 | 3.92 | 7.62x | 30.12x | identical |
| **Median** | | | | | | | **4.38x** | **11.32x** | |

Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, one checked and timed run per build; load average 6.0 at the start and 9.8 at the end; measured 2026-10-05.
<!-- /real -->

**Four utility models** that cannot be published were run the same way, for 24 hours each. Utility models 1 and 2 have several thousand pipes and run the same three kinds of reactions as the networks above. Utility models 3 and 4 have tens of thousands of pipes and run chlorine decay and water age, which on networks this size stresses the transport and memory more than the chemistry. They are not in the repository; the table below comes from `tools/bench.py --cases private`, which labels them without names.

<!-- private -->
| Case | Unpatched, 1 thread (s) | Unpatched, 8 threads | Bit-identical, 1 thread | Bit-identical, 8 threads | Plus near-identical, 1 thread | Plus near-identical, 8 threads | Near-identical on 1 thread against unpatched on 8 | Near-identical against unpatched, both on 8 | Bit-identical results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Utility model 1, bacterial regrowth (RK5) | 108 | 41.1 | 8.61 | 2.39 | 7.41 | 2.28 | 5.55x | 17.99x | identical |
| Utility model 1, chloramine (ROS2) | 525 | 180 | 7.72 | 3.08 | 6.01 | 2.64 | 30.01x | 68.31x | identical |
| Utility model 1, chlorine (Euler) | 50.8 | 22.8 | 2.12 | 1.50 | 2.15 | 1.51 | 10.62x | 15.13x | identical |
| Utility model 2, bacterial regrowth (RK5) | 117 | 44.3 | 8.68 | 3.46 | 6.76 | 3.01 | 6.56x | 14.73x | identical |
| Utility model 2, chloramine (ROS2) | 699 | 155 | 26.0 | 3.69 | 14.8 | 2.83 | 10.44x | 54.64x | identical |
| Utility model 2, chlorine (Euler) | 57.7 | 16.7 | 1.35 | 0.625 | 1.34 | 0.638 | 12.45x | 26.14x | identical |
| Utility model 3, chlorine (Euler) | 518 | 138 | 32.5 | 18.3 | 28.0 | 18.1 | 4.91x | 7.61x | identical |
| Utility model 3, water age (Euler) | 41.9 | 32.5 | 13.3 | 11.9 | 14.1 | 11.9 | 2.30x | 2.74x | identical |
| Utility model 4, chlorine (Euler) | 250 | 78.5 | 13.6 | 5.53 | 13.1 | 5.22 | 6.00x | 15.05x | identical |
| Utility model 4, water age (Euler) | 9.98 | 7.11 | 2.94 | 2.19 | 3.03 | 2.25 | 2.34x | 3.16x | identical |
| **Median** | | | | | | | **6.28x** | **15.09x** | |

Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, one checked and timed run per build; load average 25.0 at the start and 13.0 at the end; measured 2026-10-05.
<!-- /private -->

<!-- hl:private -->The bit-identical builds gave the unpatched results bit for bit in every run. Even on one thread, the code with every change was 6.3x faster than the unpatched code on eight threads (median over the 10 cases), and 15.1x faster with both on eight threads.<!-- /hl:private --> The chloramine files used here set pH and alkalinity where water enters the network, as `tools/private-reactions.py` now does; an earlier file for one of the models did not, the equilibria had no solution in the water entering there, and with [FIX-01](3-bug-fixes/FIX-01-reaction-loop-error-race/) that run stopped with error 514, an error the unpatched code had been losing.

Water age gains least on Utility models 3 and 4. The unpatched code was already fast there, because a water-age rate is one addition per segment, so what is left is mostly EPANET's own hydraulics (about a third of the patched run on the largest model) and moving water through the nodes, which runs on one thread. Chlorine decay, whose Sherwood-number terms the interpreter used to recompute in every segment, gains as much as on the public networks.

## Published reaction models

The manual's reaction systems are not the most demanding ones in use. Seven more models were written from published papers ([models/literature.md](models/literature.md) gives the sources, equations and assumptions):
- chlorine with THM and HAA formation (Fisher 2023);
- bacterial regrowth in the water and the biofilm with THM formation (Abhijith et al. 2021);
- two-reactant chlorine decay with two source waters that blend (the parallel second-order model);
- water temperature from heat exchange with the soil, driving chlorine decay (Blokker et al. 2024);
- a microbial intrusion, with its chlorine demand and the inactivation of four organisms;
- the University of Sheffield's PODDS and VCDM discolouration models.

They correspond in purpose to the example models InfoWater MSX ships (DBP, PSM, Temperature, INACTIVATION, Turbidity), whose formulations are not public. They use paths the manual's systems do not: wall species driven by the wall shear stress, `STEP()` switches, timed `MASS` sources, a temperature species that sets the other rates, and up to 20 species in every pipe. An eighth case runs the manual's chlorine decay with dispersion on BWSN2, which before only the small KY8 case did. The seven models on L-Town 24 h and dispersion on BWSN2 6 h (`--cases literature`), one checked run per build:

<!-- literature -->
| Case | Unpatched, 1 thread (s) | Unpatched, 8 threads | Bit-identical, 1 thread | Bit-identical, 8 threads | Plus near-identical, 1 thread | Plus near-identical, 8 threads | Near-identical on 1 thread against unpatched on 8 | Near-identical against unpatched, both on 8 | Bit-identical results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| L-Town 24 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | 33.2 | 8.09 | 1.41 | 0.540 | 1.34 | 0.481 | 6.04x | 16.83x | identical |
| L-Town 24 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | 81.8 | 20.2 | 2.18 | 0.723 | 1.92 | 0.475 | 10.49x | 42.50x | identical |
| L-Town 24 h, parallel second-order chlorine decay, two source waters blending (RK5) | 128 | 32.6 | 1.75 | 1.03 | 1.67 | 0.951 | 19.49x | 34.33x | identical |
| L-Town 24 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | 121 | 32.2 | 3.26 | 1.13 | 3.45 | 0.956 | 9.35x | 33.71x | identical |
| L-Town 24 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | 96.9 | 18.7 | 7.16 | 1.46 | 5.19 | 1.23 | 3.61x | 15.18x | identical |
| L-Town 24 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | 136 | 31.1 | 11.5 | 2.61 | 11.6 | 2.62 | 2.67x | 11.85x | identical |
| L-Town 24 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | 187 | 48.8 | 8.41 | 2.82 | 8.11 | 2.69 | 6.02x | 18.15x | identical |
| BWSN2 6 h, chlorine bulk and wall decay with dispersion (Euler, 60 s) | 135 | 28.0 | 7.55 | 2.42 | 6.05 | 2.22 | 4.63x | 12.61x | identical |
| **Median** | | | | | | | **6.03x** | **17.49x** | |

Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, one checked and timed run per build; load average 10.4 at the start and 7.8 at the end; measured 2026-10-05.
<!-- /literature -->

<!-- hl:literature -->The bit-identical builds gave the unpatched results bit for bit in every run. On one thread they were 23x faster than the unpatched code (median over the 8 cases; from 12x to 73x). With the near-identical changes, one thread was 6.0x faster than the unpatched code on eight threads, and 17.5x faster with both on eight threads.<!-- /hl:literature -->

**On the two larger public networks** (`--cases literature-large`), NW Model 12 h and BWSN2 6 h, the same seven models were written by `tools/private-reactions.py --kinds literature` ([how](models/literature.md#on-other-networks)). There the unpatched code ran on 8 threads only: on one thread it took 567 s for the first model on NW Model, and would take hours for all fourteen. The two comparisons that matter, near-identical on one thread against unpatched on eight, and both on eight, need only its 8-thread runs.

<!-- literature-large -->
| Case | Unpatched, 1 thread (s) | Unpatched, 8 threads | Bit-identical, 1 thread | Bit-identical, 8 threads | Plus near-identical, 1 thread | Plus near-identical, 8 threads | Near-identical on 1 thread against unpatched on 8 | Near-identical against unpatched, both on 8 | Bit-identical results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| NW Model 12 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | - | 147 | 15.5 | 2.93 | 19.9 | 3.25 | 7.41x | 45.31x | identical |
| NW Model 12 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | - | 250 | 36.4 | 5.59 | 26.8 | 5.15 | 9.34x | 48.58x | identical |
| NW Model 12 h, parallel second-order chlorine decay, two source waters blending (RK5) | - | 516 | 17.2 | 4.86 | 17.2 | 4.58 | 29.98x | 112.60x | identical |
| NW Model 12 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | - | 362 | 40.3 | 6.68 | 55.5 | 8.50 | 6.52x | 42.59x | identical |
| NW Model 12 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | - | 240 | 80.2 | 10.1 | 52.5 | 8.79 | 4.57x | 27.26x | identical |
| NW Model 12 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | - | 497 | 166 | 52.7 | 163 | 56.4 | 3.05x | 8.81x | identical |
| NW Model 12 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | - | 527 | 112 | 54.5 | 99.0 | 50.6 | 5.32x | 10.42x | identical |
| BWSN2 6 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | - | 142 | 11.0 | 2.36 | 10.4 | 2.20 | 13.59x | 64.49x | identical |
| BWSN2 6 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | - | 240 | 17.9 | 4.77 | 16.7 | 4.49 | 14.39x | 53.35x | identical |
| BWSN2 6 h, parallel second-order chlorine decay, two source waters blending (RK5) | - | 437 | 13.4 | 1.93 | 13.3 | 1.90 | 32.94x | 229.85x | identical |
| BWSN2 6 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | - | 340 | 31.2 | 3.98 | 30.6 | 4.33 | 11.11x | 78.40x | identical |
| BWSN2 6 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | - | 261 | 43.6 | 8.98 | 32.1 | 6.44 | 8.13x | 40.54x | identical |
| BWSN2 6 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | - | 362 | 77.5 | 22.2 | 86.6 | 22.4 | 4.18x | 16.17x | identical |
| BWSN2 6 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | - | 330 | 63.9 | 21.6 | 57.5 | 23.1 | 5.73x | 14.31x | identical |
| **Median** | | | | | | | **7.77x** | **43.95x** | |

Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, one checked and timed run per build; load average 9.7 at the start and 10.9 at the end; measured 2026-10-06.
<!-- /literature-large -->

**On the utility models**, the same way: all seven models on Utility models 1 and 2. On Utility model 3, the largest, only DBP and the intrusion model were run, on 8 threads, before the run was stopped (the unpatched code took 19 and 35 minutes for them); Utility model 4 was not run.

<!-- private-literature -->
| Case | Unpatched, 1 thread (s) | Unpatched, 8 threads | Bit-identical, 1 thread | Bit-identical, 8 threads | Plus near-identical, 1 thread | Plus near-identical, 8 threads | Near-identical on 1 thread against unpatched on 8 | Near-identical against unpatched, both on 8 | Bit-identical results |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Utility model 1, chlorine with THM and HAA (RK5) | - | 121 | 9.25 | 2.30 | 9.20 | 2.40 | 13.12x | 50.27x | identical |
| Utility model 1, regrowth with THM (RK5) | - | 314 | 16.2 | 8.37 | 15.2 | 8.08 | 20.74x | 38.91x | identical |
| Utility model 1, two-reactant chlorine (RK5) | - | 479 | 11.0 | 2.49 | 10.6 | 2.51 | 45.37x | 190.64x | identical |
| Utility model 1, temperature and chlorine (RK5) | - | 444 | 22.8 | 3.95 | 24.4 | 4.49 | 18.19x | 98.97x | identical |
| Utility model 1, intrusion and inactivation (ROS2) | - | 191 | 36.3 | 6.13 | 27.6 | 5.04 | 6.93x | 37.97x | identical |
| Utility model 1, PODDS discolouration (RK5) | - | 656 | 97.8 | 24.0 | 97.9 | 24.5 | 6.70x | 26.78x | identical |
| Utility model 1, VCDM discolouration (Euler) | - | 934 | 89.7 | 33.0 | 87.8 | 30.1 | 10.64x | 31.01x | identical |
| Utility model 2, chlorine with THM and HAA (RK5) | - | 94.0 | 8.17 | 1.49 | 8.21 | 1.52 | 11.44x | 61.78x | identical |
| Utility model 2, regrowth with THM (RK5) | - | 243 | 16.6 | 2.78 | 15.3 | 2.57 | 15.82x | 94.29x | identical |
| Utility model 2, two-reactant chlorine (RK5) | - | 357 | 9.88 | 1.70 | 9.98 | 1.72 | 35.79x | 208.22x | identical |
| Utility model 2, temperature and chlorine (RK5) | - | 348 | 23.3 | 3.40 | 24.4 | 3.86 | 14.27x | 90.11x | identical |
| Utility model 2, intrusion and inactivation (ROS2) | - | 186 | 34.2 | 5.44 | 24.8 | 4.01 | 7.52x | 46.44x | identical |
| Utility model 2, PODDS discolouration (RK5) | - | 429 | 76.5 | 15.6 | 76.8 | 15.7 | 5.59x | 27.37x | identical |
| Utility model 2, VCDM discolouration (Euler) | - | 608 | 75.0 | 22.1 | 73.4 | 24.2 | 8.29x | 25.18x | identical |
| Utility model 3, chlorine with THM and HAA (RK5) | - | 1,114 | - | 39.9 | - | 41.1 | - | 27.13x | identical |
| Utility model 3, intrusion and inactivation (ROS2) | - | 2,081 | - | 127 | - | 98.6 | - | 21.10x | identical |
| **Median** | | | | | | | **12.28x** | **42.67x** | |

Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, one checked and timed run per build; load average 27.1 at the start and 9.5 at the end; measured 2026-10-06. The runs that follow: load average 12.0 at the start and 16.2 at the end.
<!-- /private-literature -->

The bit-identical builds gave the unpatched results bit for bit in every run of these models with the unpatched code, on every network (on the larger networks, the 8-thread runs). On one thread, the near-identical build was a median 8 times faster than the unpatched code on eight threads on NW Model and BWSN2, and 12 times on the utility models, against 6 times on L-Town. With both on eight threads it was 44, 43 and 17 times faster. The two-reactant chlorine model gains most (30 to 45 times on one thread against the unpatched code on eight, on the larger networks) and PODDS least (3 to 7 times), but every one of the 38 cases gained.

These are single runs on a machine in use. During the NW Model and BWSN2 runs, other work pushed the load average as high as 135 at times. The unpatched 8-thread runs, minutes long, were the most exposed to it: NW Model DBP took 147 s here, against 95 s at a load average of 7 in an earlier, stopped run. So the 8-thread speed-ups on these two networks are probably overstated, by up to about half. The utility-model runs saw load averages up to 30. `tools/run-all.sh literature-large private-literature` measures them again; differences of 20 to 30 % between the bit-identical and near-identical builds, either way, are noise here.

The near-identical results differ slightly from the unpatched ones on most of these cases, as they do on the main cases. Unlike the main cases, they have not been judged against [the acceptance rule](2-near-identical/README.md#how-within-tolerance-was-decided) here; `tools/run-all.sh yardstick-literature` does that on the L-Town cases (about an hour).

## Your own models

The public networks can only say so much. Put your own network and reaction files in [`models/private/`](models/private/README.md), which git ignores, and run:

```sh
tools/private-reactions.py models/private/town.inp      # if you have no reaction files: chlorine, bacteria, chloramine
tools/try.py bit near --cases private
```

It times 85a303d and the patched builds on your models, checks whether the results are identical (and judges them against the tolerance rule where they are not), and prints a summary that names the models only `Private model 1`, `Private model 2`, ... Please open an issue with it, especially if a bit-identical build changes your results or a model gets slower.

## Newer versions of EPANET-MSX

[status.md](status.md) records the last comparison with upstream EPANET-MSX. On 5 October 2026, against `dev` at [f11bf1d](https://github.com/USEPA/EPANETMSX/commit/f11bf1d0310c74f64ccbe2c4984edbf59459833c) (five commits after 85a303d: CMake changes for MSVC, a fix in `msxout.c`, and a new temporary-file routine from PR [#21](https://github.com/USEPA/EPANETMSX/pull/21)):

- every patch applies except [FIX-03](3-bug-fixes/FIX-03-tempfile-descriptor-leak/), whose leak `dev` fixed another way in PR #21; [BIT-15](1-bit-identical/BIT-15-link-averages-once/) applies after an automatic three-way merge;
- with the bit-identical patches, `dev`'s results are unchanged in all 21 runs (the 7 main cases, step mode at 1 and 8 threads and solve mode), and `dev`'s own results are the same as 85a303d's;
- `dev` by itself runs at the same speed as 85a303d, so the gains above carry over.

Of the two open pull requests, every patch applies on top of [#28](https://github.com/USEPA/EPANETMSX/pull/28) (reactions with no rate species), and the series stops at BIT-02 on [#29](https://github.com/USEPA/EPANETMSX/pull/29) (cross-compiler compatibility: `f()` to `f(void)`, functions made `static`, in 19 files), which touches the same lines; if #29 is merged, the series needs rebasing on it.

To check again, or to check a pull request before it is merged:

```sh
tools/check.py              # the dev branch as it is on GitHub now
tools/check.py pull/28      # a pull request
tools/check.py --prs        # also: how far the series applies to each open pull request
```

## How the results were checked

For every group in the series, on all nine cases, the patched build was compared with the unpatched one:

- **step mode, 1 and 8 threads, and read mode:** a hash of every node's and every link's concentration of every species after every step (`MSXgetqual`, 64-bit values);
- **solve mode, 1 and 8 threads:** the same hash, plus the MD5 of the binary output file and of the report (EPANET's date and time stamps removed);
- **built without OpenMP**, step mode.

<!-- hl:verify -->Every one of the 20 fixes and bit-identical groups gave results identical to 85a303d's in all of its 49 runs: the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP.<!-- /hl:verify --> [verification.md](verification.md) has the table. The unpatched code itself gives the same concentrations at any thread count. During development each area was checked further:

- *Chemistry:* a model on Net3 in six variants (Euler, RK5 and ROS2, each with full and no coupling) covering terms that use formulas, formulas that use formulas, tank expressions that use hydraulic variables, every math function, and a NaN inside a cached sub-expression; a program that calls `MSXsetconstant` and `MSXsetparameter` part way through a run and then runs `MSXinit` again; and the compiled-chemistry option.
- *Transport:* Net3 with two-compartment, FIFO and LIFO tanks, which no benchmark case uses.
- *Dispersion:* five more dispersion cases (two species, a fixed coefficient, junction sources, setpoint and mass boosters), at 1 and 8 threads and without OpenMP (the dispersed mass at 1, 2, 4 and 8 threads), and with fused multiply-add turned off against the unpatched code built the same way.
- *Output:* 18 report-heavy variants: every node, link and species, hourly and 5-minute reporting, the four statistic options, and MSX's own report file.

The models and programs of these development checks are not in this repository; what is in it are the benchmark cases and the runs in [results/](results/README.md), which anyone can repeat.

**Behaviour changes, in error cases only:** with FIX-01 the largest error code is returned when several pipes fail in one step, and errors that were lost now stop the run; with BIT-02 a cycle of formula species or terms is error 506 instead of a crash; with BIT-09, running out of memory for segments is error 501 instead of a write through a null pointer; and BIT-12 allocates per-pipe arrays during a run, so a run can also stop with error 501 there if memory runs out. [BIT-15](1-bit-identical/BIT-15-link-averages-once/) assumes concentrations change only in `MSXinit` and `MSXstep`, which is true of every toolkit function today.

The patches were written by four agents working in parallel, each on its own area, and integrated into one series; all timings here were then measured together on one machine, an Apple M1 Pro (8 performance and 2 efficiency cores) that was in use at the time (an editor, a browser, a video call and, at times, another program's test suite), which is why the 8-thread numbers vary more than the 1-thread ones.

## What was tried and dropped

Besides the experiments in each change's folder, these were measured or examined and left out.

**They would change results** (the numerical method, or the order of floating-point operations beyond what the near-identical rule accepts):

- *Fewer initial segments.* At the start of a run every pipe is cut into 100 segments (`initSegs`). With [BIT-06](1-bit-identical/BIT-06-identical-segments-once/) identical segments are reacted once, which removes most of that cost; using fewer segments, or merging them more eagerly, would change the results.
- *Multiplying by the reciprocal* of the tridiagonal pivot in the dispersion solve, or of other divisors: changes the last bits, and was no faster than [NEAR-03](2-near-identical/NEAR-03-dispersion-pivot-chain/).
- *A better fill-reducing ordering* (EPANET 2.2's `genmmd`) for the dispersion matrix: a different elimination order changes rounding, and the nodal solve is about 1-2 % of the dispersion case.
- *Simplified Newton*, and *Newton's update from f(x)*: see [the near-identical page](2-near-identical/README.md#tried-and-rejected).

**No measurable gain, or not worth the complexity:**

- Reusing the derivative at the start of each RK5 call: it would need a stored derivative and its full input state per segment, and is valid only when nothing about the segment changed.
- Reusing f(y) in ROS2's first stage: the premise does not hold (the Jacobian is evaluated at y ± ε, not at y).
- A register-based interpreter, or instructions for "variable op variable": at most about 15 % fewer dispatches for a rewrite.
- Compressed (CSR) adjacency arrays: after [BIT-10](1-bit-identical/BIT-10-transport-plan-prefetch/) the adjacency lists are walked once per hydraulic step, not every quality step.
- Parallel transport: moving water through the nodes level by level, taking each pipe's outflow in parallel, or running tank reactions in parallel; each cost more in synchronisation than it saved ([BIT-10](1-bit-identical/BIT-10-transport-plan-prefetch/), [BIT-13](1-bit-identical/BIT-13-dynamic-omp-schedules/)).
- Compiler options: link-time optimisation was not pursued; `-ffast-math` changes results, and the Windows Release build already uses `/fp:fast` ([3-bug-fixes](3-bug-fixes/README.md#found-not-yet-written-up)).

**Not attempted:** EPANET's own hydraulic solver. MSX spends little time there on these cases: with [BIT-16](1-bit-identical/BIT-16-epanet-savehydfile-block-copy/), `MSXsolveH` is <!-- hl:solveh -->0.1-13 % of a run with the bit-identical changes, one thread (Net6, chlorine bulk + wall: 13 %)<!-- /hl:solveh -->. [epanet-performance](https://github.com/epanet-js/epanet-performance) covers EPANET 2.3.

## Licence

The write-ups, scripts and patches in this repository are released by Iterating Inc. under the [MIT licence](LICENSE), the same licence as EPANET-MSX, so the patches can be merged freely. The `msx` submodule is EPANET-MSX itself, under its own licence. The network files in `models/inp/` remain under their publishers' terms ([models/README.md](models/README.md)).
