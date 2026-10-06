Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 2 runs per build (a checked run and 1 timed); 2026-10-05 16:24 to 2026-10-05 16:25, load average 17.53 at the start and 11.32 at the end.

### step mode, 1 thread

| Case | bit (s) | only:NEAR-01 (s) | only:NEAR-02 (s) | only:NEAR-03 (s) | near (s) | only:NEAR-01 speed-up | only:NEAR-02 speed-up | only:NEAR-03 speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 0.777 | 0.748 | 0.762 | 0.778 | 0.758 | 1.04x | 1.02x | 1.00x | 1.03x | **no**: only:NEAR-01, near |
| Net6, chlorine bulk + wall | 0.528 | 0.511 | 0.513 | 0.526 | 0.502 | 1.03x | 1.03x | 1.01x | 1.05x | **no**: only:NEAR-01, near |
| KY8, chlorine + dispersion | 0.527 | 0.497 | 0.540 | 0.394 | 0.380 | 1.06x | 0.98x | 1.34x | 1.39x | **no**: only:NEAR-01, only:NEAR-03, near |
| Richmond, bacterial regrowth | 0.698 | 0.614 | 0.695 | 0.704 | 0.592 | 1.14x | 1.00x | 0.99x | 1.18x | **no**: only:NEAR-01, near |
| Net3, chloramine decay | 1.24 | 1.29 | 0.866 | 1.25 | 0.873 | 0.96x | 1.43x | 0.99x | 1.42x | **no**: only:NEAR-02, near |
| Net3, arsenic adsorption | 0.434 | 0.431 | 0.434 | 0.441 | 0.411 | 1.01x | 1.00x | 0.98x | 1.05x | **no**: only:NEAR-01, near |
| MSX example (4 nodes) | 62.8 ms | 63.9 ms | 63.2 ms | 63.5 ms | 62.5 ms | 0.98x | 0.99x | 0.99x | 1.00x | **no**: only:NEAR-01, near |
| **Median** |  |  |  |  |  | **1.03x** | **1.00x** | **0.99x** | **1.05x** | |

### step mode, 8 threads

| Case | bit (s) | only:NEAR-01 (s) | only:NEAR-02 (s) | only:NEAR-03 (s) | near (s) | only:NEAR-01 speed-up | only:NEAR-02 speed-up | only:NEAR-03 speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 0.341 | 0.359 | 0.346 | 0.339 | 0.329 | 0.95x | 0.99x | 1.01x | 1.04x | **no**: only:NEAR-01, near |
| Net6, chlorine bulk + wall | 0.387 | 0.387 | 0.377 | 0.369 | 0.400 | 1.00x | 1.03x | 1.05x | 0.97x | **no**: only:NEAR-01, near |
| KY8, chlorine + dispersion | 0.197 | 0.188 | 0.211 | 0.205 | 0.177 | 1.04x | 0.93x | 0.96x | 1.11x | **no**: only:NEAR-01, only:NEAR-03, near |
| Richmond, bacterial regrowth | 0.171 | 0.162 | 0.185 | 0.176 | 0.160 | 1.06x | 0.92x | 0.97x | 1.07x | **no**: only:NEAR-01, near |
| Net3, chloramine decay | 0.270 | 0.273 | 0.196 | 0.269 | 0.201 | 0.99x | 1.38x | 1.00x | 1.34x | **no**: only:NEAR-02, near |
| Net3, arsenic adsorption | 0.145 | 0.140 | 0.147 | 0.153 | 0.141 | 1.04x | 0.99x | 0.95x | 1.03x | **no**: only:NEAR-01, near |
| MSX example (4 nodes) | 67.5 ms | 67.6 ms | 67.3 ms | 67.3 ms | 63.1 ms | 1.00x | 1.00x | 1.00x | 1.07x | **no**: only:NEAR-01, near |
| **Median** |  |  |  |  |  | **1.00x** | **0.99x** | **1.00x** | **1.07x** | |
