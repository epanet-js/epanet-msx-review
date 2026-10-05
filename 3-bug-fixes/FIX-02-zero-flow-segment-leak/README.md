# FIX-02: Take no new segment for a link without flow

| | |
|---|---|
| **Category** | [Bug fix](../README.md): results are unchanged on every benchmark case |
| **Impact** | Memory grows through a run: one segment, with its two concentration arrays, for every link without flow at every quality step. About 107 bytes per such link per step with one species; about 70 MB per simulated week on Net6. The memory is reused only when the next run starts (`MSXinit`) and freed by `MSXclose`, so a long run on a network with many dead ends or closed links can run out of memory. Results are not affected. |
| **Reached from** | Any run with a link that has no flow in some step: dead ends, closed pipes and valves, idle pumps, and links whose flow is below 0.005 gpm, which MSX sets to zero; through `runepanetmsx` or the toolkit |
| **Where** | `advectSegs()` in [`src/solver/msxqual.c:887`](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L887) and `evalnodeoutflow()` in [`src/solver/msxqual.c:1356`](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1356) |
| **Since** | EPANET-MSX 2.0: commit [98d0af2](https://github.com/USEPA/EPANETMSX/commit/98d0af2b12b814fd240534e9a481adb764caf940) (2021), whose topological routing replaced `release()`. MSX 1.1's `release()` returned the segment to the pool for a link without flow. |
| **Results** | <!-- results:FIX-02 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxqual.c` (+10 / -0 lines) |
| **Patch** | [`FIX-02.patch`](FIX-02.patch), second in the series; it applies on its own to 85a303d ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | none |

## The problem

MSX moves water through each pipe as a chain of segments, taken from a pool and given back to it when they leave the pipe or are merged. At every quality step, `advectSegs()` takes a segment from the pool for every link, ready for the water that will enter the link's upstream end during the step. When the water then moves, `evalnodeoutflow()` either adds that segment to the link or, if the entering water is merged into the link's last segment, gives it back to the pool. For a link without flow it does neither: it returns before using the segment, and the next step's `advectSegs()` overwrites the pointer to it. The segment is lost to the pool for the rest of the run.

So the pool grows by one segment per zero-flow link per step. At first nothing shows: the pool keeps freed segments on a free list, and the first lost segments come from the surplus left as each pipe's 100 initial segments flush out. Once that surplus is used up, the pool takes new memory. On Net6 this is about 5 MB per 12 hours of simulation, about 70 MB per simulated week. The benchmark cases have 700 to 57,000 such link-steps per run, too few to matter in their short runs. The lost segments are never read, so results are not affected.

## Why it happens

`advectSegs()` takes the segment before it tests for flow:

```c
// src/solver/msxqual.c, advectSegs()
    for (k=1; k<=MSX.Nobjects[LINK]; k++)
    {
    // --- zero out WQ in new segment to be added at entrance of link

        for (m=1; m<=MSX.Nobjects[SPECIES]; m++) MSX.C1[m] = 0.0;

    // --- get a free segment to add to entrance of link

        MSX.NewSeg[k] = MSXqual_getFreeSeg(0.0, MSX.C1);

    // --- skip zero-length links (pumps & valves) & no-flow links

        if ( MSX.NewSeg[k] == NULL ||
             MSX.Link[(k)].len == 0.0 || MSX.Q[k] == 0.0 ) continue;
```

and `evalnodeoutflow()` returns for a link without flow before it uses the segment or gives it back:

```c
// src/solver/msxqual.c, evalnodeoutflow()
    // Find flow volume (v) released over time step
    v = fabs(MSX.Q[k]) * tstep;
    if (v == 0.0) return;
```

In MSX 1.1, `release()` did the same job and handled this case:

```c
    // --- ignore links with no flow

        if (MSX.Q[k] == 0.0)
        {
            MSXqual_removeSeg(NewSeg[k]);
            continue;
        }
```

The topological routing of MSX 2.0 replaced `release()` with `evalnodeoutflow()`, which dropped the call to `MSXqual_removeSeg()`.

A segment is a 72-byte structure plus two arrays of one `double` per species and one more, all from the pool: 104 bytes with one species, 107 measured with the pool's own overhead.

## How to reproduce

The reviewer's test network has a reservoir feeding a junction with a demand of 50 gpm, and 50 dead-end pipes, 100 ft long, from that junction to junctions without demand. It runs for 30 days with a 5-minute quality step and one species decaying at first order (RK5). The test measures the heap in use at day 10 and at day 30.

- **Without the fix**, the heap grows by 30.7 MB between day 10 and day 30: 107 bytes per dead-end pipe per quality step (50 pipes, 5,760 steps).
- **With the fix**, it does not grow.

A test program, `FIX-02_test.c`, with its input files, will be added to this folder.

## The fix

```diff
         for (m=1; m<=MSX.Nobjects[SPECIES]; m++) MSX.C1[m] = 0.0;
 
+    // --- a link with no flow releases no new segment over this time
+    //     step (evalnodeoutflow returns before using it), so don't take
+    //     one from the pool: it would never be returned to it
+
+        if ( MSX.Q[k] == 0.0 )
+        {
+            MSX.NewSeg[k] = NULL;
+            continue;
+        }
+
     // --- get a free segment to add to entrance of link
 
         MSX.NewSeg[k] = MSXqual_getFreeSeg(0.0, MSX.C1);
```

The test for no flow now comes before a segment is taken, and the link's `NewSeg[k]` is left empty. `evalnodeoutflow()` never reads it for such a link: its volume `v = |Q|·dt` is 0 exactly when `Q` is 0, and it returns before the first use. The wall-species work that followed was already skipped for links without flow. Giving the segment back in `evalnodeoutflow()`, as 1.1 did, would also work; not taking it is cheaper, and [BIT-09](../../1-bit-identical/BIT-09-segment-advection/) builds on it: it takes a new segment only when one is added to a pipe.

## Results with the fix

Results are identical on every benchmark case. The segment that is no longer taken was never read, and which memory a segment occupies never affects a result: `MSXqual_getFreeSeg()` sets its volume, concentrations and step size, `lastc` is written before it is read, and `prev` and `next` are set when the segment is linked. With the fix, the free list hands out segments in another order, and that is all.

<!-- measured:FIX-02 -->
Each table compares 85a303d unpatched ("before") with FIX-02 on its own ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 12.8 | 12.7 | 1.01x | 3.25 | 3.30 | 0.98x | yes |
| Net6, chlorine bulk + wall | 11.2 | 11.1 | 1.01x | 3.52 | 2.93 | 1.20x | yes |
| KY8, chlorine + dispersion | 10.6 | 10.6 | 1.01x | 2.06 | 1.99 | 1.03x | yes |
| Richmond, bacterial regrowth | 15.2 | 15.1 | 1.00x | 3.29 | 3.22 | 1.02x | yes |
| Net3, chloramine decay | 11.4 | 11.5 | 0.99x | 3.01 | 2.98 | 1.01x | yes |
| Net3, arsenic adsorption | 2.59 | 2.57 | 1.01x | 0.702 | 0.697 | 1.01x | yes |
| MSX example (4 nodes) | 0.214 | 0.212 | 1.01x | 0.144 | 0.145 | 1.00x | yes |
| **Median** | | | **1.01x** | | | **1.01x** | |

To measure it yourself:

```sh
tools/try.py FIX-02
```
<!-- /measured -->
