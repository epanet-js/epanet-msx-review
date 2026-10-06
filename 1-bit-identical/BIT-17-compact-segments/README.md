# BIT-17: Copy every pipe's segments into contiguous memory (more memory)

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Transport (memory layout) |
| **Results** | <!-- results:BIT-17 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxqual.c` (+84 / -0 lines) |
| **Patch** | [`BIT-17.patch`](BIT-17.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-16 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | BIT-09 (named in the patch header). It relies on [BIT-09](../BIT-09-segment-advection/)'s one-block segments to be correct ([see below](#why-the-results-are-unchanged)), so it must not be applied without BIT-09 |
| **Also fixes** | none |

**Optional: this group trades memory for speed.** Peak memory grows by 30-80 % on the larger cases ([below](#memory)), while the groups before it change peak memory by at most a few megabytes on these cases. It is last in the series so that it can be left out.

## What was slow

Segments are recycled through a last-in, first-out free list: a segment that has left a pipe goes to the head of the list ([msxqual.c:1463](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1463)), and the next segment a pipe needs is the most recently freed one ([msxqual.c:1893](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1893)). At time 0 each pipe's 100 segments ([msxqual.c:773](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L773)) lie one after the other, but as the run goes on each chain is made of segments that other pipes freed at other times, scattered across the pool: up to about 200 MB on BWSN2, which has about 1.5 million segments.

Every step walks every chain: in the reaction pass, and in the dispersion code and the wall-species shift where a model has them. Once the chemistry is fast, these walks wait on memory more than they compute, because the segments of a chain are scattered and each may have to come from main memory.

## What the change does

- A second memory pool is created at `MSXqual_open`.
- Each time a new hydraulic solution has been read, `compactSegs()` copies every pipe's and tank's chain, from its downstream end, into the spare pool, one `memcpy` per segment. It sets each copy's `c`, `lastc`, `prev` and `next` pointers and each link's and tank's first and last segment, empties the free list (whose segments are in the old pool), and swaps the pools; the old one is reset and reused at the next copy. It does not run at time 0, when `initSegs()` has just laid the segments out in order.
- If memory runs out part way through, it stops with every chain still wholly in one pool or the other, keeps both pools, and the run ends with error 501 (out of memory), as for any other allocation failure.
- Both pools are freed at `MSXqual_close`.

The copy itself cost 0.006-0.023 s per run on these cases when the change was written. After it, each pipe's segments lie in memory in the order the reaction pass and the dispersion code walk them.

### Memory

The spare pool holds a second copy of the segments' memory, so peak memory grows by roughly the size of the segment pool. Peak memory (maximum resident set size, one thread, step mode), without and with this group, measured when the change was written:

| Case | Without (MB) | With (MB) |
| --- | ---: | ---: |
| BWSN2, two-source chlorine | 193 | 265 |
| Net6, chlorine bulk + wall | 48 | 87 |
| KY8, chlorine + dispersion | 26 | 36 |
| Richmond, bacterial regrowth | 23 | 30 |
| Net3, chloramine decay | 9 | 9 |
| Net3, arsenic adsorption | 11 | 12 |
| MSX example (4 nodes) | 7 | 8 |

## Why the results are unchanged

- **Contents are copied bit for bit.** Each segment is copied whole with `memcpy`, and each chain keeps its order and its number of segments; only addresses change. The free list is emptied, so new segments come fresh from the new pool, and which memory a segment occupies never affects a result (see [BIT-09](../BIT-09-segment-advection/#why-the-results-are-unchanged)).
- **No segment pointer survives the copy.** The copy runs inside `MSXqual_step`, between the transport of one hydraulic period and the next. At that point `NewSeg[]` is empty ([BIT-09](../BIT-09-segment-advection/) takes a new segment only when one is added, and hands it over in the same step), the chemistry holds a segment pointer only during its reaction pass, and the dispersion code's per-link segment lists ([BIT-12](../BIT-12-dispersion-solve/)) are rebuilt by `dispersion_pipe()` at every step before they are read.
- **It needs BIT-09's one-block segments.** The copy moves `sizeof(struct Sseg) + 2*(nspecies+1)*sizeof(double)` bytes from the segment's address. That includes the segment's concentrations `c[]` and `lastc[]` only because BIT-09 allocates the segment and its two arrays as one block; with the three separate allocations of the unpatched code, the arrays are usually right after the segment but not always (not when a block of the pool runs out between them), and the copy would then read whatever lies there.
- The copy rebuilds each `next` pointer from the `prev` chain. This also clears a stale `next` that `MSXtank_mix3()` leaves on a FIFO tank's first segment ([msxtank.c:274](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxtank.c#L274)), which nothing reads.

Tanks' segments are copied too, so the development check on Net3 with its tanks set to two-compartment, FIFO and LIFO mixing, which no benchmark case uses, matters here: with the arsenic and chloramine reaction systems, the concentrations at every step, the binary output file and the report were the same.

## Measured

<!-- measured:BIT-17 -->
Each table compares the series up to BIT-16 ("before") with BIT-17 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 0.903 | 0.761 | 1.19x | 0.343 | 0.336 | 1.02x | yes |
| Net6, chlorine bulk + wall | 0.666 | 0.545 | 1.22x | 0.500 | 0.467 | 1.07x | yes |
| KY8, chlorine + dispersion | 0.729 | 0.530 | 1.38x | 0.222 | 0.203 | 1.09x | yes |
| Richmond, bacterial regrowth | 0.697 | 0.693 | 1.01x | 0.207 | 0.179 | 1.16x | yes |
| Net3, chloramine decay | 1.25 | 1.25 | 1.01x | 0.276 | 0.278 | 0.99x | yes |
| Net3, arsenic adsorption | 0.437 | 0.441 | 0.99x | 0.155 | 0.142 | 1.10x | yes |
| MSX example (4 nodes) | 62.7 ms | 62.9 ms | 1.00x | 66.3 ms | 65.7 ms | 1.01x | yes |
| **Median** | | | **1.01x** | | | **1.07x** | |

To measure it yourself:

```sh
tools/try.py BIT-17 --against BIT-16
```
<!-- /measured -->

## Tried and not kept

- **Re-using a pipe's own released segment for its next new segment**, to keep a pipe's segments close together without a copy: on Net6 the reaction pass was 3-6 % faster on average, but the best runs were within noise. The copy did better.
- **Segments aligned to 64-byte cache lines**: no gain, and 20 % more peak memory.
