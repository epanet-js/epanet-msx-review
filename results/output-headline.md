Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 2 runs per build (a checked run and 1 timed); 2026-10-05 16:39 to 2026-10-05 16:42, load average 12.93 at the start and 6.52 at the end.

### solve mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | 10.2 | 1.31 | 1.41 | 7.77x | 7.22x | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | 12.8 | 1.29 | 0.933 | 9.87x | 13.68x | **no**: near |
| **Median** |  |  |  | **8.82x** | **10.45x** | |

### solve mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | 8.79 | 1.00 | 0.963 | 8.79x | 9.13x | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | 4.31 | 0.327 | 0.260 | 13.17x | 16.59x | **no**: near |
| **Median** |  |  |  | **10.98x** | **12.86x** | |

### read mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | 3.89 | 1.14 | 1.15 | 3.42x | 3.39x | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | 11.5 | 1.25 | 0.901 | 9.18x | 12.76x | **no**: near |
| **Median** |  |  |  | **6.30x** | **8.08x** | |

### read mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, 2 species, every node and link every 5 min | 2.62 | 0.807 | 0.797 | 3.25x | 3.29x | yes |
| Net3 chloramine, 14 species, every node and link every 5 min | 3.06 | 0.302 | 0.233 | 10.11x | 13.12x | **no**: near |
| **Median** |  |  |  | **6.68x** | **8.20x** | |
