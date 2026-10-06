Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 1 runs per build (a checked run and 0 timed); 2026-10-05 19:28 to 2026-10-05 19:35, load average 10.28 at the start and 9.93 at the end.

### step mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | 22.9 | 4.50 | 4.46 | 5.09x | 5.14x | yes |
| Net3, chloramine decay with full coupling (ROS2) | 41.1 | 7.14 | 3.29 | 5.76x | 12.47x | **no**: near |
| **Median** |  |  |  | **5.43x** | **8.81x** | |

### step mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | 9.07 | 2.30 | 3.65 | 3.94x | 2.48x | yes |
| Net3, chloramine decay with full coupling (ROS2) | 11.0 | 1.49 | 0.730 | 7.37x | 15.09x | **no**: near |
| **Median** |  |  |  | **5.65x** | **8.78x** | |

### solve mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | 36.7 | 4.79 | 4.73 | 7.66x | 7.76x | yes |
| Net3, chloramine decay with full coupling (ROS2) | 41.5 | 7.17 | 3.30 | 5.79x | 12.58x | **no**: near |
| **Median** |  |  |  | **6.72x** | **10.17x** | |

### solve mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | 11.6 | 2.11 | 2.23 | 5.48x | 5.18x | yes |
| Net3, chloramine decay with full coupling (ROS2) | 10.6 | 1.54 | 0.700 | 6.89x | 15.17x | **no**: near |
| **Median** |  |  |  | **6.18x** | **10.17x** | |
