Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 2 runs per build (a checked run and 1 timed); 2026-10-05 16:30 to 2026-10-05 16:34, load average 8.87 at the start and 9.43 at the end.

### step mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 13.1 | 0.831 | 0.770 | 15.72x | 16.98x | **no**: near |
| Net6, chlorine bulk + wall | 10.9 | 0.510 | 0.498 | 21.42x | 21.93x | **no**: near |
| KY8, chlorine + dispersion | 10.1 | 0.520 | 0.378 | 19.52x | 26.83x | **no**: near |
| Richmond, bacterial regrowth | 15.5 | 0.728 | 0.607 | 21.32x | 25.55x | **no**: near |
| Net3, chloramine decay | 11.5 | 1.25 | 0.878 | 9.17x | 13.05x | **no**: near |
| Net3, arsenic adsorption | 2.58 | 0.438 | 0.411 | 5.90x | 6.28x | **no**: near |
| MSX example (4 nodes) | 0.214 | 63.2 ms | 63.0 ms | 3.38x | 3.39x | **no**: near |
| **Median** |  |  |  | **15.72x** | **16.98x** | |

### step mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 3.46 | 0.335 | 0.324 | 10.32x | 10.65x | **no**: near |
| Net6, chlorine bulk + wall | 2.90 | 0.372 | 0.377 | 7.80x | 7.69x | **no**: near |
| KY8, chlorine + dispersion | 2.40 | 0.264 | 0.192 | 9.07x | 12.45x | **no**: near |
| Richmond, bacterial regrowth | 3.27 | 0.196 | 0.167 | 16.74x | 19.65x | **no**: near |
| Net3, chloramine decay | 2.89 | 0.277 | 0.199 | 10.41x | 14.54x | **no**: near |
| Net3, arsenic adsorption | 0.678 | 0.148 | 0.139 | 4.58x | 4.88x | **no**: near |
| MSX example (4 nodes) | 0.137 | 66.3 ms | 66.2 ms | 2.06x | 2.07x | **no**: near |
| **Median** |  |  |  | **9.07x** | **10.65x** | |

### step mode, default threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 3.26 | 0.332 | 0.344 | 9.84x | 9.49x | **no**: near |
| Net6, chlorine bulk + wall | 2.80 | 0.390 | 0.395 | 7.16x | 7.07x | **no**: near |
| KY8, chlorine + dispersion | 3.88 | 0.224 | 0.195 | 17.34x | 19.86x | **no**: near |
| Richmond, bacterial regrowth | 3.41 | 0.171 | 0.185 | 20.00x | 18.46x | **no**: near |
| Net3, chloramine decay | 2.81 | 0.264 | 0.203 | 10.65x | 13.85x | **no**: near |
| Net3, arsenic adsorption | 0.650 | 0.154 | 0.148 | 4.23x | 4.39x | **no**: near |
| MSX example (4 nodes) | 0.152 | 74.8 ms | 72.0 ms | 2.03x | 2.11x | **no**: near |
| **Median** |  |  |  | **9.84x** | **9.49x** | |
