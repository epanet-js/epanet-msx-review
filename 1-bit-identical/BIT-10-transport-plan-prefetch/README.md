# BIT-10: List each node's links once per hydraulic step and prefetch their segments

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Transport (node loop) |
| **Results** | <!-- results:BIT-10 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxqual.c` (+140 / -39 lines) |
| **Patch** | [`BIT-10.patch`](BIT-10.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-09 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

After the reactions and [the advection step](../BIT-09-segment-advection/), `topological_transport()` ([msxqual.c:1254](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1254)) moves the water through the network one node at a time, in topological order, on one thread: it takes in the water leaving the links that flow into the node, mixes it, and sends it into the links that flow out. For every node at every quality step it:

- walked the node's adjacency list, a linked list of separately allocated entries, twice: once for the links flowing in ([msxqual.c:1274](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1274)) and once for the links flowing out ([msxqual.c:1305](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1305)), reading each link's flow direction, end nodes and flow;
- added up the node's outflow rate again from the links' flows and its demand ([msxqual.c:1289](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1289), [msxqual.c:1295](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1295));
- cleared two arrays ([msxqual.c:1270](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1270)), one of which, `SourceIn`, `sourceInput()` clears itself before using it ([msxqual.c:1100](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L1100)).

Flows, demands and flow directions change only when a new hydraulic solution is read ([msxqual.c:372](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxqual.c#L372)). On these cases the hydraulic time step is an hour (shorter when a control acts or a tank fills or empties) and the quality step 1 to 6 minutes, so 10 to 60 quality steps in a row repeated the same work.

Beyond that, the loop waits on memory. In a profile of the node loop on BWSN2 (chemistry turned off, inlining off), 46 % of the time was `evalnodeinflow()`, most of it the first touch of each pipe's leading segment, and 16 % `evalnodeoutflow()`, which touches the pipe's last segment; 17 % was `findnodequal()` (half of that `MSXchem_equil`), and about 20 % the two adjacency walks and the two clears. BWSN2's segments are spread over up to about 200 MB, and the reaction pass that runs just before has evicted them from the cache. With threads it is worse: the reaction pass runs on all cores, so each pipe's segments are left in the cache of the core that reacted them.

## What the change does

Two steps, in `msxqual.c`. In the node loop each saves time on its own, but most of the gain in whole runs comes from step 2, and mostly at eight threads. Step 1 is also what makes step 2 cheap: the links of a node further down the order are a slice of an array, not a list to walk.

1. **A transport plan.** `buildTransportPlan()` runs each time a new hydraulic solution has been read, after the nodes have been re-sorted if flow directions changed. For each node, in topological order, it records the links with flow into it and the links with flow out of it, each in adjacency-list order, and its outflow rate: `fabs(Q[k])` summed over the links not flowing into it, in adjacency-list order, plus `fmax(0, D)` for a junction. `topological_transport()` then streams through these arrays and computes the outflow volume as `PlanVolOut[j]*dt`. Links without flow are left out of the lists, since `evalnodeinflow()` and `evalnodeoutflow()` do nothing for them; their zero flow is still added to the outflow sum. The redundant clear of `SourceIn` is removed. Building the plan costs at most about 0.005 s per run. In the node loop alone, timed when this step was written: BWSN2 0.178 s to 0.165 s per run, Net6 0.144 s to 0.111 s, KY8 0.033 s to 0.027 s (one thread).

2. **Prefetching.** Before handling the j-th node, the loop asks the processor (`__builtin_prefetch`) to start fetching what node j+2 will touch: the leading segment of each link flowing into it and the last segment of each link flowing out of it, two 64-byte cache lines each. A `PREFETCH` macro makes this a no-op on compilers without the builtin. Two nodes ahead was chosen from the node loop on BWSN2 with the chemistry turned off (three runs each):

   | Nodes ahead | Node loop, s per run |
   |---|---|
   | 0 (no prefetch) | 0.141, 0.149, 0.160 |
   | 2 | 0.098, 0.101, 0.101 |
   | 4 | 0.096, 0.101, 0.106 |
   | 8 | 0.101, 0.102, 0.128 |

   In the node loop alone, timed when this step was written: BWSN2 0.163 s to 0.125 s per run and KY8 0.026 s to 0.021 s at one thread; with the faster chemistry at eight threads, BWSN2 0.159 s to 0.119 s and Net6 0.197 s to 0.135 s.

## Why the results are unchanged

- **The same links, in the same order.** Each node takes in its inflows in adjacency-list order, mixes, and sends water into its outflows in adjacency-list order, as before. The only links left out of the lists are those without flow, for which `evalnodeinflow()` moves no volume and `evalnodeoutflow()` returns at once.
- **The same outflow sum.** The outflow rate is the same terms, zeros included, added in the same order, then multiplied by `dt` once, as before.
- **Rebuilt whenever its inputs can change.** Flows, demands and flow directions are set only when a hydraulic solution is read (`getHydVars()`, then `initSegs()` or `flowdirchanged()`), and the topological order only by `sortNodes()` right after; no toolkit function sets any of them. The plan is rebuilt at that point, before the first transport step of each hydraulic period.
- **The removed clear was redundant.** `SourceIn` is read only by `sourceInput()` and `addSource()`, after `sourceInput()` has set it to zero.
- **A prefetch is only a hint** to the processor: it changes no value.

Beyond the benchmark cases, the transport changes were checked during development on Net3 with its tanks set to two-compartment, FIFO and LIFO mixing, which no benchmark case uses, with the arsenic and chloramine reaction systems: the same concentrations at every step, and the same binary output file and report.

## Measured

<!-- measured:BIT-10 -->
Each table compares the series up to BIT-09 ("before") with BIT-10 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.08 | 1.00 | 1.07x | 0.563 | 0.516 | 1.09x | yes |
| Net6, chlorine bulk + wall | 0.825 | 0.764 | 1.08x | 0.725 | 0.671 | 1.08x | yes |
| KY8, chlorine + dispersion | 1.13 | 1.11 | 1.01x | 0.546 | 0.577 | 0.95x | yes |
| Richmond, bacterial regrowth | 0.730 | 0.737 | 0.99x | 0.261 | 0.240 | 1.09x | yes |
| Net3, chloramine decay | 1.25 | 1.29 | 0.97x | 0.446 | 0.442 | 1.01x | yes |
| Net3, arsenic adsorption | 0.441 | 0.456 | 0.97x | 0.185 | 0.193 | 0.96x | yes |
| MSX example (4 nodes) | 64.1 ms | 62.7 ms | 1.02x | 60.1 ms | 56.5 ms | 1.06x | yes |
| **Median** | | | **1.01x** | | | **1.06x** | |

To measure it yourself:

```sh
tools/try.py BIT-10 --against BIT-09
```
<!-- /measured -->

## Tried and not kept

- **Moving water through the nodes in parallel, level by level** (examined, not built). Nodes at the same depth of the topological order could be handled at the same time, with a barrier between levels. BWSN2's 12,527 nodes form 336 levels, of which only 61-74 have 64 nodes or more; Net6's 3,356 nodes form 254 levels, none with 64; KY8 has 156 levels for 1,332 nodes, Richmond 64 for 872 and Net3 30-38 for 97. One barrier per level per step, at 1-2 µs each, would cost about as much as Net6's whole serial node loop.
- **Taking each pipe's outflow in parallel before the serial node loop** (bit-identical: the volumes and masses were recorded, and added in the original order afterwards). The node loop got slower: at four threads with the faster chemistry, Net6 0.136 s to 0.186 s per run, KY8 0.019 s to 0.028 s and Richmond 0.020 s to 0.024 s; at eight threads, Net6 0.197 s to 0.313 s. Prefetching (step 2) hides the same memory waits on one thread.
- **Compressed (CSR) adjacency arrays**: within noise, because with the plan the adjacency lists are walked once per hydraulic step, not at every quality step.
- Looked at and left as too small on these cases: passing the outflow of a pump or valve, which has no volume, straight to the next node instead of through a segment; the remaining per-node clear of `MassIn`; the allocations in `sortNodes()`; and `flowdirchanged()`.
