# BIT-14: Read the report's results and copy the output file in blocks; format numbers without printf

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Output and report files |
| **Results** | <!-- results:BIT-14 -->Identical to 85a303d in all 14 runs (9 cases; step and solve mode at 1 and 8 threads, read mode on the output-heavy cases, and built without OpenMP)<!-- /results --> |
| **Files** | `msxout.c`, `msxrpt.c`, `msxtoolkit.c` (+356 / -18 lines) |
| **Patch** | [`BIT-14.patch`](BIT-14.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-13 ([the patches form one series](../../benchmarking.md#applying-the-patches)); no earlier patch touches its files, so it also applies to 85a303d on its own |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

These costs grow with the number of results written. They are small on the main benchmark cases, which report a few nodes, and large when a model reports every node, link and species, as the two output-heavy cases do every 5 minutes.

- **Copying the output file.** `MSXsaveoutfile` ([msxtoolkit.c#L298](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxtoolkit.c#L298)) copied the scratch output file to the user's file with `fgetc`/`fputc`, one locked library call per byte: about 36 ns per byte, or 0.56 s for a 16 MB file.
- **Reading the results back one at a time.** `MSXreport` writes its tables from the binary output file. `writeNodeTable` and `writeLinkTable` read every value with `MSXout_getNodeQual` or `MSXout_getLinkQual` ([msxrpt.c#L271](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxrpt.c#L271), [#L302](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxrpt.c#L302)), each one `fseek` and one 4-byte `fread` ([msxout.c#L237-L238](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxout.c#L237-L238)). The output file is open for reading and writing (`"w+b"`), so every `fseek` discards the stream's buffer: one `lseek` system call and one 4 KB refill per value. In a profile of the unpatched code on the BWSN2 output-heavy case, `MSXreport` took 6 s, 80 % of it in `read` and `lseek`.
- **`strcat`.** Each value was formatted into a temporary string and appended to the line with `strcat` ([msxrpt.c#L273](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxrpt.c#L273)), which scans the growing line from its start every time: 4-8 % of `MSXreport`.
- **`sprintf`.** Once the reads are fixed, writing the report is mostly formatting numbers: in the profile, 71 % of `MSXrpt_write`'s samples were in `sprintf` (`__vfprintf`, `__dtoa`, locale handling and locking).

## What the change does

Four steps:

1. **Copy the output file in blocks.** `MSXsaveoutfile` copies through a 64 KB buffer with `fread`/`fwrite`. If the buffer cannot be allocated, the byte loop runs as before. Return codes are unchanged.

2. **Read the report's results in blocks.** A new `MSXout_getQualBlock()` reads one species' values for a run of consecutive nodes or links in one period, with one `fseek` and one `fread`. `msxrpt.c` allocates an 8 MB buffer for the length of `MSXreport`. Before a reported object's table is written, `loadBlock()` reads a block that starts at that object and extends over later reported objects while it fits, for every period and every reported species (wall species are skipped for nodes). A block stops at a gap of more than 1,024 unreported objects, so a sparse selection does not read the whole file. Values are then served from memory; they are read one at a time, as before, if the buffer cannot be allocated or one object's results do not fit in it. The statistics tables use the same blocks.

3. **Build report lines without `strcat`.** Each value is written straight to the end of the line, and the end is carried along.

4. **Format the numbers without `printf`.** Two small functions write the concentration columns (`"  %10.*f"`) and the time column (`"%4d:%02d"`). A reported value is a `float`, so for 0 to 6 decimals |c|·10<sup>p</sup> is exact in a `double`: a 24-bit significand times a power of ten of at most 14 significant bits. The function rounds that exact product to the nearest integer and writes its digits. When the product lies exactly halfway between two integers, it calls `sprintf`, so the C library's own rule for ties still decides. It also calls `sprintf` for precisions outside 0 to 6, for |c| ≥ 10<sup>9</sup>, for NaN and infinities, and for every value if the C library's decimal point is not a single character or `float` and `double` are not IEEE formats (checked once per report). Lines for MSX's own report file are written with `fputs` instead of `fprintf("  %s\n")`.

Step 2 carries most of the gain, and step 4 most of the rest. Measured on their own when they were written, on the BWSN2 output-heavy case, step 2 took `MSXreport` from 6.0 s to 0.8 s, and step 4 took the report-and-save phase from 0.81 s to 0.27 s. Steps 1 and 3 each saved less than 10 % of that phase. What remains is mostly EPANET's `ENwriteline`, one `fprintf` per line, when the tables go into EPANET's report file.

## Why the results are unchanged

- Step 1 copies the same bytes.
- Step 2 reads the same 4-byte values, from the offsets that `MSXout_getNodeQual` and `MSXout_getLinkQual` compute, and formats them in the same order. If a read came up short, which a complete output file never does, the missing values would be 0 instead of an uninitialised `float`.
- Step 3 writes the same text.
- Step 4: away from a tie, the nearest integer to the exact product is the only correctly rounded result, and it is what the C library prints. At a tie the C library decides, as it did before. Ties are left to it because the rule for them differs between C libraries (older Microsoft runtimes round them away from zero), and this way each platform's report is byte-identical to what it printed before. Negative values that round to zero, and -0.0, keep their minus sign, as `printf` prints them. A test program compared the function with `snprintf` on 70 million values: random `float` bit patterns, exact ties and their neighbours, decimal-looking values, ±0, NaN, infinities, large values, and precisions -1 to 9. There were no differences.

Beyond the benchmark cases, whose binary output file and report are compared byte for byte in solve mode, the report was checked on report-heavy variants of them. 18 variants, at one thread (and at 8 for those dominated by output): every node, link and species reported, hourly and every 5 minutes, each of the four statistics (average, minimum, maximum, range), MSX's own report file with page breaks, and up to 8 and 14 species. For step 4, 39 more: precisions 0 to 9 and mixed, the four statistic tables, MSX's own report file with page breaks, exact ties, negative values, and values from 10<sup>-7</sup> to 3·10<sup>9</sup>. Reports, binary output files and MSX report files were byte-identical in all of them.

## Measured

<!-- measured:BIT-14 -->
Each table compares the series up to BIT-13 ("before") with BIT-14 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 1.01 | 1.02 | 0.98x | 0.474 | 0.474 | 1.00x | yes |
| Net6, chlorine bulk + wall | 0.776 | 0.843 | 0.92x | 0.716 | 0.774 | 0.93x | yes |
| KY8, chlorine + dispersion | 0.750 | 0.739 | 1.01x | 0.242 | 0.245 | 0.99x | yes |
| Richmond, bacterial regrowth | 0.722 | 0.736 | 0.98x | 0.229 | 0.214 | 1.07x | yes |
| Net3, chloramine decay | 1.29 | 1.27 | 1.01x | 0.320 | 0.286 | 1.12x | yes |
| Net3, arsenic adsorption | 0.447 | 0.441 | 1.01x | 0.149 | 0.168 | 0.88x | yes |
| MSX example (4 nodes) | 63.4 ms | 63.0 ms | 1.01x | 66.4 ms | 66.9 ms | 0.99x | yes |
| **Median** | | | **1.01x** | | | **0.99x** | |

To measure it yourself:

```sh
tools/try.py BIT-14 --against BIT-13
```
<!-- /measured -->

## Tried and not kept

- A 64 KB buffer (`setvbuf`) for MSX's own report file: 3-8 % of the report phase, within noise.
- Restructuring the statistics pass: `getStatResults` ([msxout.c#L322](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxout.c#L322)) already reads a whole species block per period, so there was little to gain.
