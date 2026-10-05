# BIT-16: EPANET 2.2: copy the hydraulics file in blocks

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | EPANET 2.2 |
| **Results** | <!-- results:BIT-16 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `SRC_engines/src/solver/epanet.c` in the EPANET 2.2 submodule (+10 / -2 lines) |
| **Patch** | [`BIT-16.patch`](BIT-16.patch), for the EPANET2.2 submodule ([USEPA/EPANET2.2](https://github.com/USEPA/EPANET2.2) at 1e2fc3d), not for MSX: its paths are relative to that repository. It comes after FIX-01, FIX-02 and BIT-01 to BIT-15 in the series ([the patches form one series](../../benchmarking.md#applying-the-patches)), and since it touches no MSX file it also applies on its own |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

`MSXsolveH` runs EPANET's `ENsolveH`, then `ENsavehydfile` to copy EPANET's scratch hydraulics file to the file MSX reads ([msxtoolkit.c#L149-L150](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxtoolkit.c#L149-L150)). `EN_savehydfile` copied it with `fgetc`/`fputc`, one locked library call per byte ([epanet.c#L621](https://github.com/USEPA/EPANET2.2/blob/1e2fc3d909c0df654ead95e6e98c3307ce1375b1/SRC_engines/src/solver/epanet.c#L621)).

In profiles of the unpatched code, the copy took longer than solving the hydraulics: on BWSN2 with hourly reporting, 0.081 s against 0.033 s for `ENsolveH`; with 5-minute reporting, 0.77 s against 0.11 s; on Net6, 0.215 s against 0.069 s. The file holds a record for every hydraulic time step, and EPANET takes a step at every reporting time, so it grows with frequent reporting. Once the water-quality simulation is fast, this copy is a visible part of a run.

## What the change does

`EN_savehydfile` copies through a 64 KB buffer with `fread`/`fwrite`. If the buffer cannot be allocated, the byte loop runs as before.

OWA EPANET 2.3 has the same byte-by-byte copy in `EN_savehydfile` ([epanet.c#L633 at 83e25bb](https://github.com/OpenWaterAnalytics/EPANET/blob/83e25bbe2b0b460803e71df03bc989afe9557ea3/src/epanet.c#L633)), so the same change applies there.

## Why the results are unchanged

The same bytes are copied, and both versions leave the scratch file positioned at its end. Return codes are unchanged.

## Measured

<!-- measured:BIT-16 -->
Each table compares the series up to BIT-15 ("before") with BIT-16 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 0.975 | 0.903 | 1.08x | 0.428 | 0.343 | 1.25x | yes |
| Net6, chlorine bulk + wall | 0.839 | 0.666 | 1.26x | 0.768 | 0.500 | 1.53x | yes |
| KY8, chlorine + dispersion | 0.692 | 0.729 | 0.95x | 0.231 | 0.222 | 1.04x | yes |
| Richmond, bacterial regrowth | 0.731 | 0.697 | 1.05x | 0.194 | 0.207 | 0.94x | yes |
| Net3, chloramine decay | 1.26 | 1.25 | 1.00x | 0.289 | 0.276 | 1.05x | yes |
| Net3, arsenic adsorption | 0.443 | 0.437 | 1.01x | 0.155 | 0.155 | 1.00x | yes |
| MSX example (4 nodes) | 63.1 ms | 62.7 ms | 1.01x | 65.7 ms | 66.3 ms | 0.99x | yes |
| **Median** | | | **1.01x** | | | **1.04x** | |

**Output-heavy cases**: every node, link and species reported every 5 minutes. Solve mode runs as `runepanetmsx` does; read mode reads every value with `MSXgetqual` after every step. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; solve and read mode, best of two runs per build (a checked run and a timed run); load average 10.5 at the start and 8.9 at the end; measured 2026-10-05.

| Case | Mode | Threads | Before (s) | After (s) | Speed-up | Report and save, before | After | Identical |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | solve | 1 | 2.38 | 1.51 | 1.58x | 0.290 | 0.287 | yes |
| BWSN2, 2 species, every node and link every 5 min | solve | 8 | 1.54 | 0.847 | 1.82x | 0.293 | 0.304 | yes |
| BWSN2, 2 species, every node and link every 5 min | read | 1 | 2.13 | 1.42 | 1.50x |  |  | yes |
| BWSN2, 2 species, every node and link every 5 min | read | 8 | 1.60 | 0.822 | 1.95x |  |  | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | solve | 1 | 1.35 | 1.34 | 1.00x | 34.8 ms | 34.1 ms | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | solve | 8 | 0.367 | 0.341 | 1.08x | 41.9 ms | 41.0 ms | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | read | 1 | 1.32 | 1.30 | 1.02x |  |  | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | read | 8 | 0.362 | 0.363 | 1.00x |  |  | yes |

**`MSXsolveH`** (EPANET's hydraulics and the copy of its file), one thread:

| Case | MSXsolveH before (s) | After (s) | Speed-up |
| --- | ---: | ---: | ---: |
| BWSN2, two-source chlorine | 0.109 | 32.6 ms | 3.35x |
| Net6, chlorine bulk + wall | 0.285 | 72.1 ms | 3.95x |
| KY8, chlorine + dispersion | 12.9 ms | 5.0 ms | 2.56x |
| Richmond, bacterial regrowth | 28.8 ms | 8.9 ms | 3.22x |
| Net3, chloramine decay | 4.0 ms | 1.1 ms | 3.65x |
| Net3, arsenic adsorption | 3.1 ms | 0.9 ms | 3.36x |
| MSX example (4 nodes) | 0.6 ms | 0.4 ms | 1.46x |
| **Median** | | | **3.35x** |

To measure it yourself:

```sh
tools/try.py BIT-16 --against BIT-15 --cases main,output --modes step,solve,read
# MSXsolveH is the H field of each run in the .json file it writes
```
<!-- /measured -->

## Tried and not kept

- Not copying at all: MSX cannot reach EPANET's scratch file through the EPANET 2.2 API, and writing its own hydraulics file from `ENget...` values would round them differently. So the copy stays, and is made fast.
