Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 1 interleaved runs; 2026-10-05 16:51 to 2026-10-05 16:58, load average 8.44 at the start and 20.3 at the end.

### step mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 12.8 | 0.757 | 0.757 | 16.87x | 16.87x | **no**: near |
| Net6, chlorine bulk + wall | 11.3 | 0.523 | 0.506 | 21.60x | 22.31x | **no**: near |
| KY8, chlorine + dispersion | 10.6 | 0.535 | 0.397 | 19.75x | 26.58x | **no**: near |
| Richmond, bacterial regrowth | 15.3 | 0.712 | 0.599 | 21.46x | 25.49x | **no**: near |
| Net3, chloramine decay | 11.5 | 1.26 | 0.884 | 9.12x | 12.97x | **no**: near |
| Net3, arsenic adsorption | 2.58 | 0.444 | 0.411 | 5.81x | 6.28x | **no**: near |
| MSX example (4 nodes) | 0.215 | 64.1 ms | 64.0 ms | 3.35x | 3.36x | **no**: near |
| **Median** |  |  |  | **16.87x** | **16.87x** | |

### step mode, 2 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 7.64 | 0.566 | 0.535 | 13.50x | 14.29x | **no**: near |
| Net6, chlorine bulk + wall | 6.41 | 0.401 | 0.392 | 15.98x | 16.34x | **no**: near |
| KY8, chlorine + dispersion | 5.64 | 0.321 | 0.254 | 17.54x | 22.22x | **no**: near |
| Richmond, bacterial regrowth | 9.00 | 0.400 | 0.346 | 22.50x | 26.00x | **no**: near |
| Net3, chloramine decay | 6.64 | 0.655 | 0.462 | 10.13x | 14.38x | **no**: near |
| Net3, arsenic adsorption | 1.49 | 0.268 | 0.238 | 5.53x | 6.23x | **no**: near |
| MSX example (4 nodes) | 0.181 | 50.0 ms | 49.2 ms | 3.61x | 3.67x | **no**: near |
| **Median** |  |  |  | **13.50x** | **14.38x** | |

### step mode, 4 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 5.23 | 0.410 | 0.402 | 12.75x | 13.02x | **no**: near |
| Net6, chlorine bulk + wall | 3.93 | 0.373 | 0.356 | 10.54x | 11.05x | **no**: near |
| KY8, chlorine + dispersion | 3.26 | 0.237 | 0.195 | 13.79x | 16.71x | **no**: near |
| Richmond, bacterial regrowth | 5.68 | 0.246 | 0.222 | 23.11x | 25.58x | **no**: near |
| Net3, chloramine decay | 3.77 | 0.392 | 0.284 | 9.63x | 13.26x | **no**: near |
| Net3, arsenic adsorption | 0.894 | 0.155 | 0.153 | 5.76x | 5.85x | **no**: near |
| MSX example (4 nodes) | 0.129 | 50.2 ms | 49.5 ms | 2.57x | 2.60x | **no**: near |
| **Median** |  |  |  | **10.54x** | **13.02x** | |

### step mode, 6 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 3.85 | 0.370 | 0.361 | 10.41x | 10.66x | **no**: near |
| Net6, chlorine bulk + wall | 3.27 | 0.380 | 0.362 | 8.60x | 9.04x | **no**: near |
| KY8, chlorine + dispersion | 2.45 | 0.206 | 0.178 | 11.91x | 13.76x | **no**: near |
| Richmond, bacterial regrowth | 4.02 | 0.222 | 0.182 | 18.11x | 22.12x | **no**: near |
| Net3, chloramine decay | 4.15 | 0.333 | 0.237 | 12.46x | 17.53x | **no**: near |
| Net3, arsenic adsorption | 0.818 | 0.181 | 0.153 | 4.51x | 5.35x | **no**: near |
| MSX example (4 nodes) | 0.138 | 59.8 ms | 60.3 ms | 2.32x | 2.30x | **no**: near |
| **Median** |  |  |  | **10.41x** | **10.66x** | |

### step mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 3.46 | 0.368 | 0.399 | 9.41x | 8.69x | **no**: near |
| Net6, chlorine bulk + wall | 3.00 | 0.383 | 0.366 | 7.83x | 8.18x | **no**: near |
| KY8, chlorine + dispersion | 2.00 | 0.209 | 0.176 | 9.54x | 11.33x | **no**: near |
| Richmond, bacterial regrowth | 3.36 | 0.194 | 0.173 | 17.27x | 19.37x | **no**: near |
| Net3, chloramine decay | 2.93 | 0.277 | 0.201 | 10.57x | 14.52x | **no**: near |
| Net3, arsenic adsorption | 0.684 | 0.146 | 0.161 | 4.69x | 4.25x | **no**: near |
| MSX example (4 nodes) | 0.148 | 65.4 ms | 63.1 ms | 2.27x | 2.35x | **no**: near |
| **Median** |  |  |  | **9.41x** | **8.69x** | |

### step mode, 10 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 3.35 | 0.332 | 0.365 | 10.08x | 9.19x | **no**: near |
| Net6, chlorine bulk + wall | 2.86 | 0.398 | 0.395 | 7.18x | 7.23x | **no**: near |
| KY8, chlorine + dispersion | 2.77 | 0.224 | 0.194 | 12.38x | 14.25x | **no**: near |
| Richmond, bacterial regrowth | 3.26 | 0.185 | 0.172 | 17.57x | 18.94x | **no**: near |
| Net3, chloramine decay | 2.86 | 0.273 | 0.206 | 10.45x | 13.84x | **no**: near |
| Net3, arsenic adsorption | 0.675 | 0.158 | 0.147 | 4.27x | 4.58x | **no**: near |
| MSX example (4 nodes) | 0.154 | 72.1 ms | 72.8 ms | 2.14x | 2.12x | **no**: near |
| **Median** |  |  |  | **10.08x** | **9.19x** | |
