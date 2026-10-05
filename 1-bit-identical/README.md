# Bit-identical changes

[All changes](../README.md)

Each of these 17 groups of changes makes EPANET-MSX do the same floating-point operations, in the same order, as EPANET-MSX at [85a303d](https://github.com/USEPA/EPANETMSX/commit/85a303dca05859389eced63fabd5ea145c096333). After every group, on all nine benchmark cases, every concentration of every species at every node and link after every step is the same as before, in step mode at 1 and 8 threads, in read mode, and in solve mode, where the binary output file and the report are also byte-for-byte the same; and so it is built without OpenMP. [verification.md](../verification.md) has the table.

"Bit-identical" means on the same platform and compiler. MSX's results already differ in their last digits between, for example, an arm64 build that uses fused multiply-add and an x86-64 build that does not, and the official Windows build compiles with `/fp:fast`. These changes do not alter that.

The numerical methods are unchanged: the same Lagrangian transport, the same integrators (Euler, RK5, ROS2), the same Newton solver for equilibria, the same dispersion model. The time was going into the work around the math: an expression interpreter that re-evaluated terms recursively in every segment of every pipe at every step, per-thread variables that cost a function call on each access, identical segments integrated one by one, threads waiting on a lock, and files read and written one value or one byte at a time.

The groups form one series, applied in order on top of [FIX-01 and FIX-02](../3-bug-fixes/README.md): each is written against the tree that the groups before it produce, and its measurements are of that group added to all the ones before it. A group merges the changes that touch the same code for the same reason; its write-up goes through them step by step. [benchmarking.md](../benchmarking.md#applying-the-patches) explains how to apply them.

| ID | Change | Area | Measured, this change alone |
|---|---|---|---|
| [BIT-01](BIT-01-build-defaults/) | Build optimised, with OpenMP on macOS, when following the README | Build | <!-- summary:BIT-01 -->no optimisation to `-O3`: 1.84x median; no OpenMP to 8 threads: 3.54x median<!-- /summary --> |
| [BIT-02](BIT-02-terms-evaluated-once/) | Evaluate each term and formula once per rate evaluation, from flat expressions | Chemistry | <!-- summary:BIT-02 -->2.50x median, up to 3.00x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-03](BIT-03-thread-state-without-tls/) | Read per-thread chemistry and solver state once | Chemistry, threads | <!-- summary:BIT-03 -->within noise on these cases<!-- /summary --> |
| [BIT-04](BIT-04-pipe-invariant-cache/) | Cache terms that depend only on hydraulics, parameters and constants | Chemistry | <!-- summary:BIT-04 -->up to 3.39x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-05](BIT-05-interpreter-dispatch/) | Fewer, cheaper interpreter dispatches | Chemistry | <!-- summary:BIT-05 -->1.45x median, up to 2.27x (Net3, chloramine decay)<!-- /summary --> |
| [BIT-06](BIT-06-identical-segments-once/) | React a pipe's identical segments once | Chemistry | <!-- summary:BIT-06 -->1.15x median, up to 5.49x (BWSN2, two-source chlorine)<!-- /summary --> |
| [BIT-07](BIT-07-solver-shortcuts/) | Skip solver work whose result is known | Chemistry | <!-- summary:BIT-07 -->up to 1.05x (Net3, chloramine decay)<!-- /summary --> |
| [BIT-08](BIT-08-euler-lanes/) | Evaluate Euler rates for eight segments at once | Chemistry | <!-- summary:BIT-08 -->up to 1.23x (KY8, chlorine + dispersion)<!-- /summary --> |
| [BIT-09](BIT-09-segment-advection/) | Wall-species shift in one pass, new segments only when added, one allocation each | Transport | <!-- summary:BIT-09 -->1.09x median, up to 1.31x (MSX example (4 nodes))<!-- /summary --> |
| [BIT-10](BIT-10-transport-plan-prefetch/) | List each node's links once per hydraulic step and prefetch their segments | Transport | <!-- summary:BIT-10 -->up to 1.08x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-11](BIT-11-dispersion-mass-without-locks/) | Sum dispersed mass per link without locks, in link order | Dispersion, threads | <!-- summary:BIT-11 -->at 8 threads up to 1.60x (KY8, chlorine + dispersion)<!-- /summary --> |
| [BIT-12](BIT-12-dispersion-solve/) | Factor once, solve into the segments, keep coefficients and segment lists | Dispersion | <!-- summary:BIT-12 -->up to 1.67x (KY8, chlorine + dispersion); at 8 threads up to 1.42x (KY8, chlorine + dispersion)<!-- /summary --> |
| [BIT-13](BIT-13-dynamic-omp-schedules/) | Hand pipes to threads dynamically in the reaction and dispersion loops | Threads | <!-- summary:BIT-13 -->at 8 threads up to 1.37x (Net3, chloramine decay)<!-- /summary --> |
| [BIT-14](BIT-14-report-and-output-file/) | Read the report's results and copy the output file in blocks; format numbers without printf | Output | <!-- summary:BIT-14 -->output-heavy cases, one thread: BWSN2 solve mode 3.70x, Net3 chloramine solve mode 2.01x<!-- /summary --> |
| [BIT-15](BIT-15-link-averages-once/) | Average each link's segments once for all species | Output, toolkit | <!-- summary:BIT-15 -->output-heavy cases, one thread: BWSN2 read mode 1.27x, BWSN2 solve mode 1.22x<!-- /summary --> |
| [BIT-16](BIT-16-epanet-savehydfile-block-copy/) | EPANET 2.2: copy the hydraulics file in blocks | EPANET 2.2 | <!-- summary:BIT-16 -->MSXsolveH 3.35x median, up to 3.95x (Net6, chlorine bulk + wall); whole run up to 1.26x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-17](BIT-17-compact-segments/) | Copy every pipe's segments into contiguous memory (more memory) | Transport, memory | <!-- summary:BIT-17 -->up to 1.38x (KY8, chlorine + dispersion); at 8 threads 1.07x median, up to 1.16x (Richmond, bacterial regrowth)<!-- /summary --> |

[BIT-17](BIT-17-compact-segments/) trades 30-80 % more peak memory on the larger cases for speed, and can be left out. The groups before it change peak memory by a few megabytes at most. BIT-01, BIT-08, BIT-14, BIT-15, BIT-16 and BIT-17 can each be left out without breaking anything that follows. BIT-07 and BIT-13 can be left out of the bit-identical series, but NEAR-02 and NEAR-03 are written on top of them. Leaving out any other group stops a later one from applying.

<!-- bit-paragraphs -->
## Build

### BIT-01: Build optimised, with OpenMP on macOS, when following the README

The README's `cmake -B build .` then `cmake --build build --config Release` compiles MSX and EPANET without optimisation under the Makefile and Ninja generators, which ignore `--config`; and on macOS, CMake does not find Homebrew's keg-only libomp, so the library runs on one thread. Release becomes the default build type for single-configuration generators, and CMake looks for libomp where Homebrew installs it. Only `CMakeLists.txt` files change, and the two halves can be taken separately.

[Write-up, measurements and patch](BIT-01-build-defaults/)

## Chemistry: the expression interpreter and the integrators

### BIT-02: Evaluate each term and formula once per rate evaluation, from flat expressions

Two-thirds to three-quarters of the unpatched run was the expression interpreter, mostly re-doing work: every reference to a `[TERMS]` entry or a formula species evaluated it again, recursively, and every variable was fetched through a callback. Expressions are now flat blocks, and each set of expressions computes the terms and formulas it needs once, in dependency order, into an array that the expressions read directly. On the way, a cycle of formula species, which crashed MSX with a stack overflow, becomes error 506 at `MSXopen` (interpreted chemistry).

[Write-up, measurements and patch](BIT-02-terms-evaluated-once/)

### BIT-03: Read per-thread chemistry and solver state once

The chemistry and its three solvers kept their working state in OpenMP `threadprivate` globals, and in a shared library on macOS every access to one is a function call: 12-18 % of the unpatched run. Each thread's state is now one struct, looked up once per call and passed down to the solvers and their callbacks. With BIT-02, this removes the cost that the OpenMP build had against a build without OpenMP on one thread.

[Write-up, measurements and patch](BIT-03-thread-state-without-tls/)

### BIT-04: Cache terms that depend only on hydraulics, parameters and constants

Terms such as `Re^0.88`, and parts of rate expressions such as `(4/D)*Kw*Kf/(Kw+Kf)`, depend only on a pipe's hydraulics, parameters and constants, yet were computed again for every segment at every step. They are now found when the file is opened and computed once per pipe, and again only when one of their inputs changes, bit for bit.

[Write-up, measurements and patch](BIT-04-pipe-invariant-cache/)

### BIT-05: Fewer, cheaper interpreter dispatches

After BIT-04, most of the chemistry time is the interpreter's dispatch: one pass through a `switch` per token. Number and variable operands are now merged into the operators that use them, each set of expressions runs as one program, each operation jumps directly to the next (with GCC and Clang), and expressions are rewritten with exact identities into forms that need fewer operations.

[Write-up, measurements and patch](BIT-05-interpreter-dispatch/)

### BIT-06: React a pipe's identical segments once

Every pipe starts as 100 segments with the same concentrations, and many stay identical until they leave the pipe: 96 % of BWSN2's segment-steps repeat the segment before. Each was integrated on its own. A run of segments whose concentrations and integration step are equal bit for bit is now integrated once and the results copied: same water, same pipe and same reactions give the same bits. On BWSN2 this is the largest gain in the series.

[Write-up, measurements and patch](BIT-06-identical-segments-once/)

### BIT-07: Skip solver work whose result is known

The Newton solver computed `pow(10, -numsig)` on every call; it is now computed once. ROS2's Jacobian evaluated the rates twice for every rate species, including species that no rate uses, whose column is all zeros (alkalinity in the chloramine model); without full coupling, those columns are now set to zero without evaluating anything, which is what the old code computed.

[Write-up, measurements and patch](BIT-07-solver-shortcuts/)

### BIT-08: Evaluate Euler rates for eight segments at once

With the Euler integrator a segment's reaction is one evaluation of a short rate program, and the cost was the work around it. For Euler models without equilibrium or formula species, the program now runs for eight segments at a time, each operation across the eight in a loop the compiler vectorises; each segment's arithmetic is unchanged.

[Write-up, measurements and patch](BIT-08-euler-lanes/)

## Transport: segments and nodes

### BIT-09: Wall-species shift in one pass, new segments only when added, one allocation each

In models with wall species, `shiftSegWallQual()` restarted its search from the pipe's upstream end for every segment, so its cost grew with the square of a pipe's segments, and every pipe starts with 100. And at every step `advectSegs()` took a new segment from the pool for every link with flow, usually only to put it straight back. The shift is now one pass, a segment is taken only when one is added to a pipe, and a segment and its two concentration arrays are one allocation.

[Write-up, measurements and patch](BIT-09-segment-advection/)

### BIT-10: List each node's links once per hydraulic step and prefetch their segments

The serial loop that moves water through the nodes walked each node's adjacency list twice and added up its outflow again at every quality step, although flows change only at hydraulic steps, and it waited on memory for each pipe's end segments. Each node's inflow and outflow links and its outflow rate are now listed once per hydraulic step, in the same order, and the loop prefetches the segments of the node two places ahead in topological order.

[Write-up, measurements and patch](BIT-10-transport-plan-prefetch/)

### BIT-17: Copy every pipe's segments into contiguous memory (more memory)

Segments are recycled through a last-in, first-out free list, so each pipe's chain ends up scattered across memory, and every step walks every chain. Once per hydraulic step, every pipe's and tank's segments are now copied, in order, into a second memory pool. This is the one group that uses more memory, 30-80 % more at peak on the larger cases, so it comes last in the series and can be left out.

[Write-up, measurements and patch](BIT-17-compact-segments/)

## Dispersion and threads

### BIT-11: Sum dispersed mass per link without locks, in link order

`segqual_update()` added each pipe's dispersed mass to one shared total inside two `omp critical` sections per pipe; at 8 threads the main thread spent most of the function waiting for the lock, which, once the chemistry was fast, kept the KY8 dispersion case from getting faster beyond 4 threads. Each pipe now writes its two values to its own slots, and one thread adds them after the loop in pipe order, as a single thread did before. The dispersion term of the mass balance is then the same at any thread count; before, its last bits changed from run to run.

[Write-up, measurements and patch](BIT-11-dispersion-mass-without-locks/)

### BIT-12: Factor once, solve into the segments, keep coefficients and segment lists

For every dispersing pipe, species and quality step, `dispersion_pipe()` factored the same tridiagonal system three times, copied the three solutions into the segments in three more list walks, and recomputed the dispersion coefficient from unchanged hydraulics; `segqual_update()` then walked the list once more. The system is now factored once for its three right-hand sides and solved straight into the segments, the coefficient is kept while the pipe's flow, status and end heads are unchanged, and the segment pointers are kept for the second pass. Among the benchmark cases only KY8 uses dispersion.

[Write-up, measurements and patch](BIT-12-dispersion-solve/)

### BIT-13: Hand pipes to threads dynamically in the reaction and dispersion loops

The pipe reaction loop and the two dispersion loops gave each thread an equal block of pipes, but a pipe's work grows with its number of segments (1 to 335 on KY8), and two of an M1 Pro's ten cores are slower, so threads that finished early waited at the end of each loop. Pipes are now handed out a few at a time (`schedule(dynamic, 2)` for reactions, `schedule(dynamic, 8)` for dispersion). Each pipe's arithmetic is unchanged, and after FIX-01 and BIT-11 nothing in these loops depends on the order in which pipes are done.

[Write-up, measurements and patch](BIT-13-dynamic-omp-schedules/)

## Output, report and EPANET

### BIT-14: Read the report's results and copy the output file in blocks; format numbers without printf

`MSXreport` read every value back from the binary output file with its own `fseek` and 4-byte `fread`, built its lines with `strcat` and formatted every number with `sprintf`, and `MSXsaveoutfile` copied the file one byte at a time. Results are now read and copied in blocks, and the numbers are written by a small formatter that gives the same text, calling `sprintf` for values exactly on a rounding tie. The gain shows when many results are reported.

[Write-up, measurements and patch](BIT-14-report-and-output-file/)

### BIT-15: Average each link's segments once for all species

Saving a reporting period, and `MSXgetqual`, walked each link's segments once per species, and saving wrote every value with its own `fwrite`. A link's species are now averaged in one walk (in parallel on large networks when saving), each period is written with one `fwrite`, and `MSXgetqual` computes a link's species once per step. This assumes that concentrations change only in `MSXinit` and `MSXstep`, which is true of every toolkit function today.

[Write-up, measurements and patch](BIT-15-link-averages-once/)

### BIT-16: EPANET 2.2: copy the hydraulics file in blocks

`MSXsolveH` has EPANET copy its scratch hydraulics file with `ENsavehydfile`, which went one byte at a time with `fgetc`/`fputc` and took longer than solving the hydraulics. It now copies 64 KB at a time. This is a patch to the EPANET 2.2 submodule, not to MSX; OWA EPANET 2.3 has the same loop.

[Write-up, measurements and patch](BIT-16-epanet-savehydfile-block-copy/)
<!-- /bit-paragraphs -->
