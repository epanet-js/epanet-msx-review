# BIT-09: Wall-species shift in one pass, new segments only when added, one allocation each

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Transport (pipe segments) |
| **Results** | <!-- results:BIT-09 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxqual.c` (+127 / -89 lines) |
| **Patch** | [`BIT-09.patch`](BIT-09.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-08 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | [FIX-02](../../3-bug-fixes/FIX-02-zero-flow-segment-leak/): step 2 rewrites the zero-flow test that FIX-02 adds to `advectSegs()`, and keeps its effect (a link without flow takes no segment), so the patch applies only on top of it |
| **Also fixes** | A write through a null pointer when the memory pool runs out: the run now stops with error 501 ([below](#why-the-results-are-unchanged)) |

## What was slow

Water moves through each pipe as a chain of segments, parcels of water with a volume and a concentration per species. At every quality step, after the reactions, `advectSegs()` ([msxqual.c:866](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L866)) prepares the segment that may enter each link at its upstream end and, when the model has wall species, recomputes the wall concentrations of every segment for the position it will move to. Then the node loop moves the water ([BIT-10](../BIT-10-transport-plan-prefetch/)).

In the profiles of the unpatched code the whole transport is under 3 % of the water-quality time at one thread (11 % on the four-node MSX example), hidden behind the chemistry. Once the chemistry is fast (BIT-02 to BIT-08) that is no longer so, least of all with threads, since the transport runs on one thread: with the faster chemistry, it was about half of Net6's water-quality time at eight threads in the development measurements (0.35 s of 0.65 s). Three things in this step cost more than they needed to:

- **The wall-species shift was quadratic.** `shiftSegWallQual()` ([msxqual.c:984](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L984)) finds, for each segment, which of the current segments will lie alongside it once the water has moved. For every segment it restarted that search from the pipe's upstream end ([msxqual.c:1030](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1030)), adding up the same volumes again: about n²/2 steps for a pipe of n segments, and every pipe starts with 100 ([msxqual.c:773](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L773)). It runs for every pipe with flow at every step in the three cases with wall species (Richmond, Net3 arsenic and the MSX example), and its loops tested every species' type.
- **A new segment for every link, every step.** `advectSegs()` took a segment from the pool and zeroed its concentrations for every link with flow ([msxqual.c:887](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L887)), with or without wall species. Usually the water entering the pipe is merged into its last segment (the same quality within tolerance, or the pipe already holds the maximum number of segments), and `evalnodeoutflow()` then put the new segment straight back on the free list ([msxqual.c:1389](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1389)). In the cases without wall species this was all the advection step did.
- **Three allocations per segment.** `MSXqual_getFreeSeg()` made one allocation for the segment, one for its concentrations `c[]` and one for their previous values `lastc[]` ([msxqual.c:1903](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1903)). BWSN2 sets up about 1.5 million segments at time 0.

## What the change does

Three steps, all in `msxqual.c`. Step 2 carries most of the gain on the cases without wall species, step 1 on the cases with them; step 3 is small on its own.

1. **The wall-species shift in one pass.** The search for the next segment starts where the search for the one before stopped. The segment `seg2` that ended one search is the first whose cumulative volume from the upstream end, `vsum`, reaches the segment's future end `vend`; the next segment's future start is that same `vend`, and every segment before `seg2` has `vsum < vend`, so it can neither contribute to the next search nor end it. So `seg2` and `vsum` carry over from one segment to the next, with a flag saying whether `seg2`'s volume is already in `vsum`; if a search runs off the end of the chain, so does the next. A list of the wall species, made at `MSXqual_open`, replaces the per-species type tests in `getNewSegWallQual()` and `shiftSegWallQual()`. Timed on its own when it was written, the advection step went from 0.094 s to 0.038 s per run on Richmond, from 0.062 s to 0.009 s on Net3 arsenic and from 0.023 s to 0.0015 s on the MSX example.

2. **A new segment only when one is added.** `advectSegs()` now returns at once unless the model has wall species, and then works only on pipes with flow: there the new segment's wall concentrations must be computed from the segments it displaces before any segment moves. Every other link's `NewSeg[k]` stays empty, and `evalnodeoutflow()` takes a segment from the pool only when it adds one to the pipe, with `MSXqual_getFreeSeg(v, upnodequal)` and its wall species set to zero: exactly what the old new segment held. A list of the bulk species replaces the `type == BULK` tests. On the cases without wall species the advection step disappears (it took 0.081 s per run on BWSN2, 0.059 s on Net6 and 0.015 s on KY8), and when this step was written, the transport as a whole fell by about a quarter on those cases.

3. **One allocation per segment.** `MSXqual_getFreeSeg()` makes one allocation of `sizeof(struct Sseg) + 2*(nspecies+1)*sizeof(double)` bytes, and `c` and `lastc` point into it, so the chemistry and dispersion code are untouched. `sizeof(struct Sseg)` is 72 bytes on 64-bit platforms, a multiple of 8, so the arrays stay aligned. The pool hands out memory in order, so the three pieces were usually next to each other already; what changes is one call instead of three, and that a segment's data is now always one block, never split between two blocks of the pool. The gain is small (setting up BWSN2's segments at time 0 gets slightly faster), but [BIT-17](../BIT-17-compact-segments/) copies a segment with one `memcpy`, which is correct only because of this step.

## Why the results are unchanged

- **Step 1.** The same segments contribute to each segment's wall concentrations, in the same order, with the same `vsum` values: the same prefix sums, added in the same order. Zero-volume segments are skipped exactly as before, and each `seg2->c` is read at the same point relative to the writes to `seg1->c`.
- **Step 2.** Whether the inflow is merged into the last segment or added as a new one is decided by the same test ([msxqual.c:1371](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1371)), and the merge does the same arithmetic. An added segment holds what it held before: the bulk species at the upstream node's quality, the wall species as `advectSegs()` computed them for a pipe with wall species and zero otherwise, the volume `v` and an integration step of zero. Only which free memory it occupies differs, and no result depends on that: `MSXqual_getFreeSeg()` sets the volume, concentrations and step, `lastc` is written before it is read, and `prev` and `next` are set when the segment is linked.
- **Step 3.** Only where the memory comes from changes.

Beyond the benchmark cases, the transport changes were checked during development on Net3 with its tanks set to two-compartment, FIFO and LIFO mixing, which no benchmark case uses, with the arsenic reaction system (which has a wall species) and the chloramine one: the same concentrations at every step, and the same binary output file and report.

One error path behaves differently. When the memory pool cannot supply a segment, the unpatched `advectSegs()` leaves `NewSeg[k]` null and `evalnodeoutflow()` then writes through it ([msxqual.c:1363](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1363)). Now `evalnodeoutflow()` returns, and the run stops with error 501 (out of memory), as `MSXqual_step` intends.

## Measured

<!-- measured:BIT-09 -->
Each table compares the series up to BIT-08 ("before") with BIT-09 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.14 | 1.08 | 1.06x | 0.607 | 0.563 | 1.08x | yes |
| Net6, chlorine bulk + wall | 0.842 | 0.825 | 1.02x | 0.829 | 0.725 | 1.14x | yes |
| KY8, chlorine + dispersion | 1.28 | 1.13 | 1.13x | 0.505 | 0.546 | 0.93x | yes |
| Richmond, bacterial regrowth | 0.795 | 0.730 | 1.09x | 0.305 | 0.261 | 1.17x | yes |
| Net3, chloramine decay | 1.26 | 1.25 | 1.00x | 0.403 | 0.446 | 0.90x | yes |
| Net3, arsenic adsorption | 0.500 | 0.441 | 1.14x | 0.242 | 0.185 | 1.30x | yes |
| MSX example (4 nodes) | 84.2 ms | 64.1 ms | 1.31x | 83.4 ms | 60.1 ms | 1.39x | yes |
| **Median** | | | **1.09x** | | | **1.14x** | |

To measure it yourself:

```sh
tools/try.py BIT-09 --against BIT-08
```
<!-- /measured -->

## Tried and not kept

- **Advecting the wall species in parallel**, pipe by pipe (bit-identical). After step 1 the work per step is too small to share out. On Richmond, with the faster chemistry, the advection step went from 0.038 s to 0.031 s per run at 2 threads and from 0.029 s to 0.024 s at 4, but from 0.050 s to 0.054 s at 8; the serial node loop that follows got 0.004-0.006 s slower, because the segments were left in other cores' caches; and on Net3 arsenic the advection step took twice as long at 4 threads (0.017 s to 0.034 s).
- **Larger memory-pool blocks.** The pool allocates 64,000-byte blocks ([mempool.c:27](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/mempool.c#L27)), about 2,800 `malloc` calls for BWSN2's segments: too few to matter.
