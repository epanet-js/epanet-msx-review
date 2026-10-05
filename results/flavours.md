Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 1 interleaved runs; 2026-10-05 16:42 to 2026-10-05 16:51, load average 6.52 at the start and 8.44 at the end.

### step mode, 1 thread

| Case | base (s) | base@O0 (s) | base@noomp (s) | bit@noomp (s) | bit (s) | near@noomp (s) | near (s) | base@O0 speed-up | base@noomp speed-up | bit@noomp speed-up | bit speed-up | near@noomp speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 12.7 | 23.3 | 11.8 | 0.739 | 0.737 | 0.721 | 0.737 | 0.54x | 1.07x | 17.12x | 17.17x | 17.55x | 17.19x | **no**: near@noomp, near |
| Net6, chlorine bulk + wall | 10.9 | 20.3 | 10.3 | 0.508 | 0.533 | 0.495 | 0.506 | 0.54x | 1.06x | 21.40x | 20.43x | 21.98x | 21.50x | **no**: near@noomp, near |
| KY8, chlorine + dispersion | 10.1 | 18.7 | 9.56 | 0.487 | 0.523 | 0.377 | 0.381 | 0.54x | 1.06x | 20.82x | 19.38x | 26.88x | 26.62x | **no**: near@noomp, near |
| Richmond, bacterial regrowth | 15.1 | 26.3 | 14.4 | 0.710 | 0.706 | 0.586 | 0.603 | 0.57x | 1.05x | 21.28x | 21.40x | 25.79x | 25.07x | **no**: near@noomp, near |
| Net3, chloramine decay | 11.3 | 19.7 | 10.4 | 1.26 | 1.24 | 0.878 | 0.876 | 0.58x | 1.09x | 8.97x | 9.13x | 12.93x | 12.96x | **no**: near@noomp, near |
| Net3, arsenic adsorption | 2.55 | 4.77 | 2.36 | 0.431 | 0.436 | 0.407 | 0.408 | 0.54x | 1.08x | 5.92x | 5.85x | 6.27x | 6.25x | **no**: near@noomp, near |
| MSX example (4 nodes) | 0.213 | 0.417 | 0.198 | 62.4 ms | 63.0 ms | 60.8 ms | 61.9 ms | 0.51x | 1.08x | 3.42x | 3.39x | 3.51x | 3.44x | **no**: near@noomp, near |
| **Median** |  |  |  |  |  |  |  | **0.54x** | **1.07x** | **17.12x** | **17.17x** | **17.55x** | **17.19x** | |
