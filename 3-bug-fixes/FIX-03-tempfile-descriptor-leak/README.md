# FIX-03: Close the file descriptor that `mkstemp` opens

| | |
|---|---|
| **Category** | [Bug fix](../README.md): results are unchanged on every benchmark case |
| **Impact** | Every `MSXopen` leaks two file descriptors and every `MSXsolveH` one (and `MSXopen` one more with the `COMPILER` option). A program that runs one scenario after another in one process runs out of descriptors after about 80 scenarios at macOS's default limit of 256 open files, and its next `ENopen` or `MSXopen` cannot open its files. Results are not affected. |
| **Reached from** | The toolkit, on every system other than Windows: a program that opens and closes MSX projects many times in one process. `runepanetmsx` opens one project and exits, so it is not affected. |
| **Where** | `MSXutils_getTempName()` in [`src/solver/msxutils.c:72`](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxutils.c#L72) |
| **Since** | EPANET-MSX 1.1, the first commit of the repository (05a2d79, 2021) |
| **Results** | <!-- results:FIX-03 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `msxutils.c` (+8 / -1 lines) |
| **Patch** | [`FIX-03.patch`](FIX-03.patch), third in the series; it applies on its own to 85a303d, before or after the rest of the series ([the patches form one series](../../benchmarking.md#applying-the-patches)). It does not apply to upstream `dev`, which fixed the same leak another way (PR #21). |
| **Requires** | none |
| **Also fixes** | none |

## The problem

MSX keeps its hydraulic results and its binary output in scratch files, named by `MSXutils_getTempName()`. `MSXopen` names two (the output file and a temporary copy, [msxproj.c:312-313](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxproj.c#L312-L313)), `MSXsolveH` one (the hydraulics file, [msxtoolkit.c:144](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxtoolkit.c#L144)), and the `COMPILER` option one more ([msxcompiler.c:88](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxcompiler.c#L88)). On systems other than Windows, each name costs a file descriptor that is never closed.

A program that runs scenarios in a loop, opening, solving and closing a project each time, loses three descriptors per scenario. At macOS's default limit of 256 open files it runs out after about 80 scenarios; on Linux, whose default limit is usually 1,024, after about 340. From then on, opening any file in that process fails.

Each leaked descriptor also keeps its file's data on disk after `MSXclose` removes the file by name, until the process exits: on POSIX systems the space of a removed file is freed only when the last descriptor on it is closed. The leaked descriptors point at the scratch hydraulics and output files, so their space stays in use. This follows from how the files are opened; it was not measured.

## Why it happens

```c
// src/solver/msxutils.c, MSXutils_getTempName()
#else
    // --- use system function mkstemp() to create a temporary file name
    strcpy(s, "msxXXXXXX");
    mkstemp(s);
#endif
    return s;
```

`mkstemp()` does more than make a name: it creates the file and opens it, and returns the open descriptor. MSX wants only the name, and opens the file again by name later (with `fopen`, in `MSXout_open()` and EPANET's `ENsavehydfile()`). The returned descriptor is discarded, so it stays open until the process exits.

## How to reproduce

The reviewer's test opens, solves and closes a three-pipe model with one decaying species (`ENopen`, `MSXopen`, `MSXsolveH`, `MSXsolveQ`, `MSXclose`, `ENclose`) once, then 20 more times, and compares the lowest free file descriptor before and after the 20 cycles.

- **Without the fix**, it goes from 4 to 64: three descriptors per cycle.
- **With the fix**, it stays at 3.

A test program, `FIX-03_test.c`, with its input files, will be added to this folder.

## The fix

```diff
+#ifndef WINDOWS
+#include <unistd.h>
+#endif
+
 ...
     // --- use system function mkstemp() to create a temporary file name
+    //     (and close the descriptor it opens; the file is reopened by name)
+    int fd;
     strcpy(s, "msxXXXXXX");
-    mkstemp(s);
+    fd = mkstemp(s);
+    if ( fd >= 0 ) close(fd);
 #endif
```

The descriptor is closed at once. The file stays on disk under its unique name until MSX opens it, so the name is still reserved, which is the reason to use `mkstemp()` rather than `tmpnam()`. `close()` is declared in `<unistd.h>`, a POSIX header, so it is included on systems other than Windows only; the Windows branch, which uses `tmpnam()` and opens nothing, is unchanged. If `mkstemp()` fails it returns −1, and the code behaves as before.

Upstream `dev` has since replaced this function with a new routine for temporary files (PR #21), which fixes the same leak, so this patch does not apply there. [status.md](../../status.md) records which patches apply to the current `dev`.

## Results with the fix

Results are identical on every benchmark case: the same files are created under the same kind of name and opened the same way; only the extra descriptor is closed.

<!-- measured:FIX-03 -->
Each table compares 85a303d unpatched ("before") with FIX-03 on its own ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 12.8 | 12.8 | 1.00x | 3.25 | 3.01 | 1.08x | yes |
| Net6, chlorine bulk + wall | 11.2 | 11.1 | 1.00x | 3.52 | 3.01 | 1.17x | yes |
| KY8, chlorine + dispersion | 10.6 | 10.6 | 1.01x | 2.06 | 2.32 | 0.89x | yes |
| Richmond, bacterial regrowth | 15.2 | 15.1 | 1.00x | 3.29 | 3.39 | 0.97x | yes |
| Net3, chloramine decay | 11.4 | 11.5 | 0.99x | 3.01 | 2.95 | 1.02x | yes |
| Net3, arsenic adsorption | 2.59 | 2.59 | 1.00x | 0.702 | 0.676 | 1.04x | yes |
| MSX example (4 nodes) | 0.214 | 0.214 | 1.00x | 0.144 | 0.144 | 1.01x | yes |
| **Median** | | | **1.00x** | | | **1.02x** | |

To measure it yourself:

```sh
tools/try.py FIX-03
```
<!-- /measured -->
