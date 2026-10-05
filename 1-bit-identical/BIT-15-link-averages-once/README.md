# BIT-15: Average each link's segments once for all species

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Output and toolkit |
| **Results** | <!-- results:BIT-15 -->Identical to 85a303d in all 14 runs (9 cases; step and solve mode at 1 and 8 threads, read mode on the output-heavy cases, and built without OpenMP)<!-- /results --> |
| **Files** | `msxout.c`, `msxqual.c`, `msxtoolkit.c` (+180 / -6 lines) |
| **Patch** | [`BIT-15.patch`](BIT-15.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-14 ([the patches form one series](../../benchmarking.md#applying-the-patches)); it also applies to 85a303d on its own |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

A link's concentration is the volume-weighted average of its segments. `MSXqual_getLinkQual(k, m)` ([msxqual.c#L500](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L500)) computes it for one species by walking the link's list of segments, a pointer chase through memory. Two callers ask for every species of a link one at a time, so each list is walked once per species:

- **Saving results.** At every reporting time, `MSXout_saveResults` ([msxout.c#L141](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxout.c#L141)) saves every node, link and species to the scratch output file, whatever the `[REPORT]` section selects, and wrote each value with its own 4-byte `fwrite`, a locked library call ([#L164](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxout.c#L164), [#L172](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxout.c#L172)). Results are saved whenever anything is reported ([msxqual.c#L278-L279](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L278-L279)), so programs that step through a run pay for it too, not only `MSXsolveQ`. In a profile of the unpatched code on the BWSN2 output-heavy case, saving was 4.6 % of the quality phase, four fifths of it in segment walks and the rest in `fwrite`.
- **`MSXgetqual`.** Toolkit programs often read every species of every link after each step. Each `MSXgetqual(MSX_LINK, ...)` call walked the link's segments for one species ([msxtoolkit.c#L776](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxtoolkit.c#L776)).

## What the change does

Three steps:

1. **One walk per link and one write per period.** `MSXqual_getLinkQuals(k, c[])`, new at the end of `msxqual.c`, walks a link's segments once and accumulates the volume and every species' mass, in the original segment order, with the same fallback to the average of the two end nodes when the link holds no water. `MSXout_saveResults` fills a buffer with the whole period, in the file's order, and writes it with one `fwrite`. If the buffer cannot be allocated, the old loop runs. (`msxout.c` now includes `<stdlib.h>` on every platform, not only on Apple's.)

2. **Links in parallel.** With OpenMP and at least 1,000 links, the link loop of step 1 runs in parallel (`schedule(dynamic, 256)`). Each thread has its own scratch array and writes only its own links' slots of the buffer. Below 1,000 links, or without OpenMP, the loop is serial. The gain is modest, and only on large networks that report often.

3. **A per-step cache for `MSXgetqual`.** `MSXinit` and `MSXstep` advance a stamp. The first `MSXgetqual(MSX_LINK, k, ...)` for link k after the stamp changes computes all species of the link with `MSXqual_getLinkQuals` and records the stamp; later calls for that link in the same step return the saved values. Only the links a program reads are computed. The cache, (links + 1) × (species + 1) doubles, is allocated at the first link query and freed in `MSXclose`; if it cannot be allocated, the old code runs.

**The assumption behind step 3: concentrations change only in `MSXinit` and `MSXstep`.** That holds for every toolkit function today. `MSXsolveQ` goes through those two, and the `MSXset...` functions change inputs that take effect at the next `MSXinit` or step. A future function that changed segment or node concentrations directly would have to advance the stamp (`newQualStamp()` in `msxtoolkit.c`), or `MSXgetqual` would return the values from before the change. Also, `MSXgetqual` now writes to the cache, so two threads must not call it at the same time; the toolkit keeps one global project, and its other functions were not safe to call that way either.

Step 3 changes most for toolkit programs. Measured on its own when it was written, it took reading every node and link value after a step on BWSN2 from 6.7 ms to 4.2 ms with the benchmark case's two species, and from 41.9 ms to 7.4 ms with eight species. Step 1 helps every run that saves results, including programs that step through a run and read values, since they save too when anything is reported; step 2 shows only at several threads on the largest network.

## Why the results are unchanged

- Step 1: each species' sums are the same additions, over the segments in the same order, as in `MSXqual_getLinkQual`, and the divisions and the fallback are the same. In the disassembly, the per-species fused multiply-adds are the same operations; some are now vectorised across species, one species per lane, which changes none of them. The values are written in the same order, so the file is the same.
- Step 2: each link's values are computed exactly as in step 1, whatever thread computes them, and each lands in its own slot.
- Step 3: the saved values are those of step 1, and the stamp changes whenever concentrations can change. When the stamp wraps around, after 2<sup>32</sup> steps, the cache is cleared.

The benchmark cases are hashed after every step at 1 and 8 threads and built without OpenMP, and the output-heavy cases are also run reading every value with `MSXgetqual` after every step. Beyond them:

- the cache was checked with reads mixed between nodes, links and species, repeated reads of the same link, reading before `MSXinit`, and a second `MSXinit` without closing; a toolkit program that runs a network repeatedly gave the same hashes on two networks;
- the 18 report-heavy variants of the benchmark cases used for [BIT-14](../BIT-14-report-and-output-file/) (every node, link and species reported, hourly and every 5 minutes, the four statistic options, MSX's own report file) gave byte-identical binary output files and reports, at one thread and, for those dominated by output, at 8.

## Measured

<!-- measured:BIT-15 -->
Each table compares the series up to BIT-14 ("before") with BIT-15 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.02 | 0.975 | 1.05x | 0.474 | 0.428 | 1.11x | yes |
| Net6, chlorine bulk + wall | 0.843 | 0.839 | 1.01x | 0.774 | 0.768 | 1.01x | yes |
| KY8, chlorine + dispersion | 0.739 | 0.692 | 1.07x | 0.245 | 0.231 | 1.06x | yes |
| Richmond, bacterial regrowth | 0.736 | 0.731 | 1.01x | 0.214 | 0.194 | 1.10x | yes |
| Net3, chloramine decay | 1.27 | 1.26 | 1.01x | 0.286 | 0.289 | 0.99x | yes |
| Net3, arsenic adsorption | 0.441 | 0.443 | 1.00x | 0.168 | 0.155 | 1.09x | yes |
| MSX example (4 nodes) | 63.0 ms | 63.1 ms | 1.00x | 66.9 ms | 65.7 ms | 1.02x | yes |
| **Median** | | | **1.01x** | | | **1.06x** | |

To measure it yourself:

```sh
tools/try.py BIT-15 --against BIT-14
```
<!-- /measured -->

## Tried and not kept

- Computing every link's average at the first `MSXgetqual` of a step: programs that read a few links would pay for all of them.
- Interleaving the walks of several links' segment lists when saving, to overlap their memory accesses: what remains of the walks is at most about 6 % of the quality phase in the most output-heavy variant.
