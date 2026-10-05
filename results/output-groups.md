Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 1 interleaved runs; 2026-10-05 16:25 to 2026-10-05 16:30, load average 10.5 at the start and 8.87 at the end.

### solve mode, 1 thread

| Case | base (s) | BIT-13 (s) | BIT-14 (s) | BIT-15 (s) | BIT-16 (s) | BIT-13 speed-up | BIT-14 speed-up | BIT-15 speed-up | BIT-16 speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | 10.4 | 10.8 | 2.91 | 2.38 | 1.51 | 0.96x | 3.56x | 4.35x | 6.88x | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | 13.2 | 2.86 | 1.42 | 1.35 | 1.34 | 4.61x | 9.27x | 9.78x | 9.82x | yes |
| **Median** |  |  |  |  |  | **2.79x** | **6.42x** | **7.07x** | **8.35x** | |

### solve mode, 8 threads

| Case | base (s) | BIT-13 (s) | BIT-14 (s) | BIT-15 (s) | BIT-16 (s) | BIT-13 speed-up | BIT-14 speed-up | BIT-15 speed-up | BIT-16 speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | 9.67 | 8.42 | 2.06 | 1.54 | 0.847 | 1.15x | 4.70x | 6.27x | 11.41x | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | 4.49 | 1.82 | 0.434 | 0.367 | 0.341 | 2.46x | 10.35x | 12.23x | 13.16x | yes |
| **Median** |  |  |  |  |  | **1.80x** | **7.53x** | **9.25x** | **12.28x** | |

### read mode, 1 thread

| Case | base (s) | BIT-13 (s) | BIT-14 (s) | BIT-15 (s) | BIT-16 (s) | BIT-13 speed-up | BIT-14 speed-up | BIT-15 speed-up | BIT-16 speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | 3.92 | 2.58 | 2.70 | 2.13 | 1.42 | 1.52x | 1.45x | 1.84x | 2.76x | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | 11.6 | 1.42 | 1.47 | 1.32 | 1.30 | 8.19x | 7.93x | 8.84x | 8.97x | yes |
| **Median** |  |  |  |  |  | **4.86x** | **4.69x** | **5.34x** | **5.87x** | |

### read mode, 8 threads

| Case | base (s) | BIT-13 (s) | BIT-14 (s) | BIT-15 (s) | BIT-16 (s) | BIT-13 speed-up | BIT-14 speed-up | BIT-15 speed-up | BIT-16 speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | 2.61 | 2.28 | 2.48 | 1.60 | 0.822 | 1.15x | 1.06x | 1.63x | 3.18x | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | 3.42 | 0.477 | 0.477 | 0.362 | 0.363 | 7.18x | 7.18x | 9.46x | 9.43x | yes |
| **Median** |  |  |  |  |  | **4.16x** | **4.12x** | **5.54x** | **6.31x** | |
