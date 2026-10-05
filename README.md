# Faster EPANET-MSX without changing the math

Oct 5, 2026 · @Luke

## Summary

On seven test cases built from the reaction systems in the EPANET-MSX manual, the 17 groups of bit-identical changes here make the median case **TBD faster with one thread and TBD faster with eight**, and every concentration at every step, the binary output file and the report are **bit-for-bit the same** as before. Three near-identical changes take the median to **TBD and TBD**; they move results by less than the unpatched code already varies between platforms. With threads, the patched code is TBD faster than the unpatched code on one thread in the median case (TBD-TBD). Three bug fixes found on the way come first in the series; they leave every benchmark result unchanged.

The numerical methods are unchanged: the same Lagrangian transport, the same integrators (Euler, RK5, ROS2), the same Newton solver for equilibria, the same dispersion model. The time was going into the work around the math:

- **The expression interpreter re-did work.** Every `[TERMS]` entry was evaluated again each time it was referenced, recursively, in every segment of every pipe at every step, including terms such as `Re^0.88` that change only when the hydraulics do. Two-thirds to three-quarters of the unpatched run time was the interpreter.
- **Identical segments were integrated one by one.** Every pipe starts as 100 segments of the same water, and many stay identical, but each was integrated on its own, every step. On BWSN2 that was most of what was left after the interpreter was fixed.
- **Per-thread variables were expensive.** OpenMP's `threadprivate` variables cost a function call on each access in a shared library on macOS (12-18 % of the time).
- **Threads waited on each other.** A lock taken twice per pipe in the dispersion code stopped the dispersion case from getting faster beyond four threads, and the reaction loop gave each thread an equal number of pipes rather than an equal amount of work.
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
tools/try.py bit near --quick        # 85a303d against the patches, on this machine
```

[reproducing.md](reproducing.md) goes through each claim, and [benchmarking.md](benchmarking.md) explains the tools.

## Headline numbers

The figures are the median speed-up per case over the seven main cases, each build against the unpatched code at the same thread count, so no single case can inflate them. Times are whole runs: opening the files, hydraulics and water quality. <!-- machine -->-<!-- /machine -->.

<!-- headline -->
<!-- /headline -->

**These tables come from one quick pass** (`QUICK=1 tools/run-all.sh`: one timed run per build, on a machine in use, with the load average recorded), so single values can be a few per cent off at one thread and more at eight. `tools/run-all.sh` remakes every table as the best of 5 interleaved runs (about 6 hours), and `tools/update-docs.py` writes them into these pages.

Per case, step mode:

<!-- permodel -->
<!-- /permodel -->

TBD: sentence on smallest/largest gains.

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

Two more cases report every node, link and species every 5 minutes, to measure the output code ([BIT-14](1-bit-identical/BIT-14-report-and-output-file/), [BIT-15](1-bit-identical/BIT-15-link-averages-once/)), and two larger real-world networks run with three kinds of reactions each ([below](#larger-networks)).

## How this is organised

| Folder | |
|---|---|
| [1-bit-identical/](1-bit-identical/README.md) | 17 groups of changes that leave every result byte-for-byte the same: `BIT-01` to `BIT-17` |
| [2-near-identical/](2-near-identical/README.md) | 3 changes that move results by rounding, by less than MSX already varies between platforms: `NEAR-01` to `NEAR-03` |
| [3-bug-fixes/](3-bug-fixes/README.md) | 3 bugs found on the way, fixed without changing any benchmark result: `FIX-01` to `FIX-03`; and the bugs found but not yet written up |
| [models/](models/README.md) | The networks, the reaction files and `cases.json`; `private/` for your own |
| [tools/](benchmarking.md#scripts) | Scripts to build, time and compare MSX |
| [results/](results/README.md) | The measurements behind every table here |
| `msx` | Submodule: EPANET-MSX at 85a303d |

Each folder has a write-up (`README.md`): what was slow, what the change does (step by step where a group merges several changes), why the results are unchanged or how far they move, its measurements, and what was tried and not kept. It also has the patch, `<ID>.patch`, whose header says what it changes, what it requires and whether its results are identical. The patches form one series: FIX-01 to FIX-03 first, then BIT-01 to BIT-17, each on top of the ones before it, then NEAR-01 to NEAR-03, each of which applies on its own. [BIT-16](1-bit-identical/BIT-16-epanet-savehydfile-block-copy/) is a patch to the EPANET2.2 submodule; all the others are patches to MSX.

## Bit-identical changes (17)

Each group performs the same floating-point operations in the same order. Every concentration of every species at every node and link after every step, the binary output file and the report are byte-for-byte unchanged after every group, on all nine cases, at 1 and 8 threads and built without OpenMP. [The category page](1-bit-identical/README.md) describes each group in a paragraph. "Measured" is that group added to the ones before it, whole runs, step mode, one thread unless stated.

<!-- bit-index -->
| ID | What changes | Area | Measured, this change alone |
|---|---|---|---|
| [BIT-01](1-bit-identical/BIT-01-build-defaults/) | Release build by default; find Homebrew's libomp on macOS | Build | <!-- summary:BIT-01 -->build options; see build flavours<!-- /summary --> |
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
| [BIT-14](1-bit-identical/BIT-14-report-and-output-file/) | Report and output file in blocks; numbers formatted without printf | Output and report files | <!-- summary:BIT-14 -->within noise on these cases<!-- /summary --> |
| [BIT-15](1-bit-identical/BIT-15-link-averages-once/) | One segment walk per link when saving results and in MSXgetqual | Output and toolkit | <!-- summary:BIT-15 -->up to 1.07x (KY8, chlorine + dispersion); at 8 threads 1.06x median, up to 1.11x (BWSN2, two-source chlorine)<!-- /summary --> |
| [BIT-16](1-bit-identical/BIT-16-epanet-savehydfile-block-copy/) | EN_savehydfile copies the hydraulics file 64 KB at a time | EPANET 2.2 | <!-- summary:BIT-16 -->MSXsolveH 3.35x median, up to 3.95x (Net6, chlorine bulk + wall); whole run up to 1.26x (Net6, chlorine bulk + wall)<!-- /summary --> |
| [BIT-17](1-bit-identical/BIT-17-compact-segments/) | Segments copied into contiguous memory once per hydraulic step (more memory) | Transport | <!-- summary:BIT-17 -->up to 1.38x (KY8, chlorine + dispersion); at 8 threads 1.07x median, up to 1.16x (Richmond, bacterial regrowth)<!-- /summary --> |
<!-- /bit-index -->

## Near-identical changes (3)

**These change results**, at the level of rounding, by less than the unpatched code's own results already differ between platforms (built with and without fused multiply-add, and for x86-64). Each was judged on its own, on top of the bit-identical series. [The category page](2-near-identical/README.md) explains how "within tolerance" was decided, shows how much the unpatched code varies between platforms, and has the acceptance table and its limitations.

<!-- near-index -->
| ID | What changes | Area | Measured, this change alone |
|---|---|---|---|
| [NEAR-01](2-near-identical/NEAR-01-reassociate-expressions/) | Regroup rate expressions so more of each is cached per pipe | Chemistry (expression interpreter) | <!-- summary:NEAR-01 -->1.03x median, up to 1.14x (Richmond, bacterial regrowth)<!-- /summary --> |
| [NEAR-02](2-near-identical/NEAR-02-forward-difference-jacobians/) | One forward-difference Jacobian helper for ROS2 and Newton's method | Chemistry (integrator and equilibrium solver) | <!-- summary:NEAR-02 -->up to 1.43x (Net3, chloramine decay); at 8 threads up to 1.38x (Net3, chloramine decay)<!-- /summary --> |
| [NEAR-03](2-near-identical/NEAR-03-dispersion-pivot-chain/) | Dispersion pivots as ratios of determinants, solved while built | Dispersion | <!-- summary:NEAR-03 -->up to 1.34x (KY8, chlorine + dispersion)<!-- /summary --> |
<!-- /near-index -->

## Bug fixes (3)

These come first in the series. Each applies on its own to 85a303d and leaves every benchmark result unchanged. [The category page](3-bug-fixes/README.md) also lists two bugs fixed as part of a performance change and the bugs found but not yet written up.

<!-- fix-index -->
| ID | What changes | Area | Measured, this change alone |
|---|---|---|---|
| [FIX-01](3-bug-fixes/FIX-01-reaction-loop-error-race/) | A failed pipe's error code is no longer overwritten by later pipes | Chemistry (reaction loop, multithreading) | <!-- summary:FIX-01 -->no change beyond noise (1.00x median at one thread)<!-- /summary --> |
| [FIX-02](3-bug-fixes/FIX-02-zero-flow-segment-leak/) | Links without flow no longer take a segment that is never returned | Transport (pipe segments) | <!-- summary:FIX-02 -->no change beyond noise (1.01x median at one thread)<!-- /summary --> |
| [FIX-03](3-bug-fixes/FIX-03-tempfile-descriptor-leak/) | Close the descriptor mkstemp opens for each temporary file name | Files (temporary files) | <!-- summary:FIX-03 -->no change beyond noise (1.00x median at one thread)<!-- /summary --> |
<!-- /fix-index -->

**FIX-01 can stop a model that appears to run today.** With it, a model whose equilibrium or integration fails in some pipes stops with error 513 or 514 instead of reporting concentrations that were never solved. The error is real; the unpatched code was losing it. It happened on one of the two utility models below.

## Multithreading

MSX parallelises three things with OpenMP: the reaction loop over pipes (`MSXchem_react`), the two loops over pipes in the dispersion code, and, with [BIT-15](1-bit-identical/BIT-15-link-averages-once/), the averaging of link concentrations when results are saved. Everything else runs on one thread: reading hydraulics, moving water through the nodes in topological order (sequential by nature), tanks, and EPANET's own hydraulics.

**What was in the way:**

- **No threads at all on macOS** ([BIT-01](1-bit-identical/BIT-01-build-defaults/)): CMake does not find Homebrew's keg-only libomp, so the library is built single-threaded.
- **Per-thread variables cost a call on every access** ([BIT-03](1-bit-identical/BIT-03-thread-state-without-tls/)): in a shared library on macOS, each access to a `threadprivate` variable goes through `_tlv_get_addr`, and the chemistry and the three integrators touched them in their innermost loops (12-18 % of all samples). With BIT-02 and BIT-03 the OpenMP build at one thread is as fast as a build without OpenMP; unpatched it was about 8 % slower.
- **A lock taken twice per pipe in the dispersion code** ([BIT-11](1-bit-identical/BIT-11-dispersion-mass-without-locks/)): every thread added its pipes' dispersed mass to one total inside `#pragma omp critical`. At 8 threads the main thread spent three-quarters of `segqual_update` waiting for the lock. This, not the chemistry, is why the KY8 case stopped getting faster beyond 4 threads. Summing per pipe in pipe order also makes the mass balance the same at any thread count.
- **Equal numbers of pipes, unequal work** ([BIT-13](1-bit-identical/BIT-13-dynamic-omp-schedules/)): the loops used OpenMP's default static schedule, but the work per pipe is proportional to its number of water parcels, from 1 to over 300, and two of an M1 Pro's ten cores are slower efficiency cores. A dynamic schedule hands out a few pipes at a time.
- **A data race on the reaction loop's error code** ([FIX-01](3-bug-fixes/FIX-01-reaction-loop-error-race/)): every thread wrote the shared `errcode`, so an error in one pipe could be overwritten by the next pipe's success.

TBD: where it stands now (scaling numbers).

### Thread scaling

Whole runs, seconds, step mode. "Unpatched" is 85a303d built with OpenMP; macOS users following its README got the 1-thread column whatever their thread count, because OpenMP was not found.

<!-- scaling -->
<!-- /scaling -->

### Build flavours

One thread, whole runs, seconds. `-O0` is what a plain `cmake -B build .` with the Makefile generator compiles ([BIT-01](1-bit-identical/BIT-01-build-defaults/)).

<!-- flavours -->
<!-- /flavours -->

## Output-heavy cases

Every node, link and species reported every 5 minutes. **solve** runs as `runepanetmsx` does (`MSXreport`, `MSXsaveoutfile`); **read** reads every node and link value with `MSXgetqual` after every step, as many toolkit programs do. Whole runs and the report-and-save phase, seconds.

<!-- output -->
<!-- /output -->

TBD: output sentence.

## Larger networks

Two public networks with three kinds of reactions each: L-Town (the BattLeDIM 2020 network, 905 pipes, 24 hours of its 5-minute demand patterns) and the NW Model (a 9,979-pipe system with pumps and rules, 12 hours), each with the manual's chlorine bulk and wall decay (Euler), bacterial regrowth (RK5) and chloramine decomposition (ROS2), with sources at the networks' reservoirs (`--cases real`). Whole runs, step mode, one checked run each.

<!-- real -->
<!-- /real -->

**Two utility models** that cannot be published were run the same way, each with the same three kinds of reactions: Utility model 1 and Utility model 2, each with several thousand pipes, run for 24 hours. They are not in the repository; the tables below come from `tools/bench.py --cases private`, which labels them without names.

<!-- private -->
<!-- /private -->

TBD: utility sentence.

## Your own models

The public networks can only say so much. Put your own network and reaction files in [`models/private/`](models/private/README.md), which git ignores, and run:

```sh
tools/private-reactions.py models/private/town.inp      # if you have no reaction files: chlorine, bacteria, chloramine
tools/try.py bit near --cases private
```

It times 85a303d and the patched builds on your models, checks whether the results are identical (and judges them against the tolerance rule where they are not), and prints a summary that names the models only `Private model 1`, `Private model 2`, ... Please open an issue with it, especially if a bit-identical build changes your results or a model gets slower.

## Newer versions of EPANET-MSX

TBD from status.md.

## How the results were checked

For every group in the series, on all nine cases, the patched build was compared with the unpatched one:

- **step mode, 1 and 8 threads, and read mode:** a hash of every node's and every link's concentration of every species after every step (`MSXgetqual`, 64-bit values);
- **solve mode, 1 and 8 threads:** the same hash, plus the MD5 of the binary output file and of the report (EPANET's date and time stamps removed);
- **built without OpenMP**, step mode.

TBD: counts. [verification.md](verification.md) has the table. The unpatched code itself gives the same concentrations at any thread count. During development each area was checked further:

- *Chemistry:* a model on Net3 in six variants (Euler, RK5 and ROS2, each with full and no coupling) covering terms that use formulas, formulas that use formulas, tank expressions that use hydraulic variables, every math function, and a NaN inside a cached sub-expression; a program that calls `MSXsetconstant` and `MSXsetparameter` part way through a run and then runs `MSXinit` again; and the compiled-chemistry option.
- *Transport:* Net3 with two-compartment, FIFO and LIFO tanks, which no benchmark case uses.
- *Dispersion:* five more dispersion cases (two species, a fixed coefficient, junction sources, setpoint and mass boosters), at 1 and 8 threads and without OpenMP (the dispersed mass at 1, 2, 4 and 8 threads), and with fused multiply-add turned off against the unpatched code built the same way.
- *Output:* 18 report-heavy variants: every node, link and species, hourly and 5-minute reporting, the four statistic options, and MSX's own report file.

**Behaviour changes, in error cases only:** with FIX-01 the largest error code is returned when several pipes fail in one step, and errors that were lost now stop the run; with BIT-02 a cycle of formula species is error 506 instead of a crash. [BIT-15](1-bit-identical/BIT-15-link-averages-once/) assumes concentrations change only in `MSXinit` and `MSXstep`, which is true of every toolkit function today.

The patches were written by four agents working in parallel, each on its own area, and integrated into one series; all timings here were then measured together on one machine, an Apple M1 Pro (8 performance and 2 efficiency cores) that was in use at the time (an editor, a browser, a video call and, at times, another program's test suite), which is why the 8-thread numbers vary more than the 1-thread ones.

## What was tried and dropped

Besides the experiments in each change's folder, these were measured or examined and left out.

**They would change results** (the numerical method, or the order of floating-point operations beyond what the near-identical rule accepts):

- *Fewer initial segments.* At the start of a run every pipe is cut into 100 segments (`initSegs`). With [BIT-06](1-bit-identical/BIT-06-identical-segments-once/) identical segments are reacted once, which removes most of that cost; using fewer segments, or merging them more eagerly, would change the results.
- *Multiplying by the reciprocal* of the tridiagonal pivot in the dispersion solve, or of other divisors: changes the last bits, and was no faster than [NEAR-03](2-near-identical/NEAR-03-dispersion-pivot-chain/).
- *A better fill-reducing ordering* (EPANET 2.2's `genmmd`) for the dispersion matrix: a different elimination order changes rounding, and the nodal solve is about 1 % of the dispersion case.
- *Simplified Newton*, and *Newton's update from f(x)*: see [the near-identical page](2-near-identical/README.md#tried-and-rejected).

**No measurable gain, or not worth the complexity:**

- Reusing the derivative at the start of each RK5 call: it would need a stored derivative and its full input state per segment, and is valid only when nothing about the segment changed.
- Reusing f(y) in ROS2's first stage: the premise does not hold (the Jacobian is evaluated at y ± ε, not at y).
- A register-based interpreter, or instructions for "variable op variable": at most about 15 % fewer dispatches for a rewrite.
- Compressed (CSR) adjacency arrays: after [BIT-10](1-bit-identical/BIT-10-transport-plan-prefetch/) the adjacency lists are walked once per hydraulic step, not every quality step.
- Parallel transport: moving water through the nodes level by level, taking each pipe's outflow in parallel, or running tank reactions in parallel; each cost more in synchronisation than it saved ([BIT-10](1-bit-identical/BIT-10-transport-plan-prefetch/), [BIT-13](1-bit-identical/BIT-13-dynamic-omp-schedules/)).
- Compiler options: link-time optimisation was not pursued; `-ffast-math` changes results, and the Windows Release build already uses `/fp:fast` ([3-bug-fixes](3-bug-fixes/README.md#found-not-yet-written-up)).

**Not attempted:** EPANET's own hydraulic solver. MSX spends little time there on these cases: with [BIT-16](1-bit-identical/BIT-16-epanet-savehydfile-block-copy/), `MSXsolveH` is TBD of a patched run. [epanet-performance](https://github.com/epanet-js/epanet-performance) covers EPANET 2.3.

## Licence

The write-ups, scripts and patches in this repository are released by Iterating Inc. under the [MIT licence](LICENSE), the same licence as EPANET-MSX, so the patches can be merged freely. The `msx` submodule is EPANET-MSX itself, under its own licence. The network files in `models/inp/` remain under their publishers' terms ([models/README.md](models/README.md)).
