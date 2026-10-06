Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 2 runs per build (a checked run and 1 timed); 2026-10-05 16:34 to 2026-10-05 16:39, load average 9.43 at the start and 12.93 at the end.

### solve mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 13.0 | 0.772 | 0.768 | 16.89x | 16.99x | **no**: near |
| Net6, chlorine bulk + wall | 11.6 | 0.536 | 0.515 | 21.54x | 22.45x | **no**: near |
| KY8, chlorine + dispersion | 11.2 | 0.634 | 0.441 | 17.62x | 25.30x | **no**: near |
| Richmond, bacterial regrowth | 15.5 | 0.720 | 0.616 | 21.47x | 25.08x | **no**: near |
| Net3, chloramine decay | 11.6 | 1.27 | 0.880 | 9.11x | 13.16x | **no**: near |
| Net3, arsenic adsorption | 2.61 | 0.450 | 0.420 | 5.82x | 6.23x | **no**: near |
| MSX example (4 nodes) | 0.216 | 63.2 ms | 62.2 ms | 3.41x | 3.47x | **no**: near |
| **Median** |  |  |  | **16.89x** | **16.99x** | |

### solve mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 3.37 | 0.347 | 0.370 | 9.70x | 9.10x | **no**: near |
| Net6, chlorine bulk + wall | 2.99 | 0.385 | 0.375 | 7.78x | 7.97x | **no**: near |
| KY8, chlorine + dispersion | 8.02 | 0.890 | 0.739 | 9.01x | 10.85x | **no**: near |
| Richmond, bacterial regrowth | 3.30 | 0.170 | 0.160 | 19.40x | 20.63x | **no**: near |
| Net3, chloramine decay | 2.92 | 0.271 | 0.203 | 10.76x | 14.33x | **no**: near |
| Net3, arsenic adsorption | 0.680 | 0.156 | 0.165 | 4.35x | 4.12x | **no**: near |
| MSX example (4 nodes) | 0.144 | 64.8 ms | 65.4 ms | 2.22x | 2.20x | **no**: near |
| **Median** |  |  |  | **9.01x** | **9.10x** | |

### solve mode, default threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 3.76 | 0.336 | 0.345 | 11.17x | 10.90x | **no**: near |
| Net6, chlorine bulk + wall | 3.30 | 0.452 | 0.406 | 7.30x | 8.12x | **no**: near |
| KY8, chlorine + dispersion | 29.7 | 0.250 | 0.225 | 118.99x | 132.15x | **no**: near |
| Richmond, bacterial regrowth | 3.29 | 0.173 | 0.162 | 18.99x | 20.28x | **no**: near |
| Net3, chloramine decay | 2.87 | 0.284 | 0.206 | 10.11x | 13.96x | **no**: near |
| Net3, arsenic adsorption | 0.644 | 0.150 | 0.148 | 4.28x | 4.34x | **no**: near |
| MSX example (4 nodes) | 0.152 | 72.4 ms | 72.2 ms | 2.09x | 2.10x | **no**: near |
| **Median** |  |  |  | **10.11x** | **10.90x** | |
