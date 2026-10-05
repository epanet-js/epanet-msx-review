Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 0 interleaved runs (one checked run); 2026-10-05 17:42 to 2026-10-05 18:04, load average 6.01 at the start and 9.81 at the end.

### step mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | 3.54 | 0.258 | 0.223 | 13.74x | 15.91x | **no**: near |
| L-Town 24 h, bacterial regrowth (RK5) | 5.77 | 0.911 | 0.768 | 6.33x | 7.51x | **no**: near |
| L-Town 24 h, chloramine decay (ROS2) | 51.0 | 5.56 | 3.93 | 9.16x | 12.96x | **no**: near |
| NW Model 12 h, chlorine bulk + wall (Euler) | 65.4 | 1.93 | 1.86 | 33.86x | 35.14x | **no**: near |
| NW Model 12 h, bacterial regrowth (RK5) | 134 | 13.7 | 11.7 | 9.80x | 11.49x | **no**: near |
| NW Model 12 h, chloramine decay (ROS2) | 690 | 21.5 | 15.5 | 32.09x | 44.48x | **no**: near |
| **Median** |  |  |  | **11.77x** | **14.43x** | |

### step mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | 1.35 | 0.281 | 0.294 | 4.80x | 4.59x | **no**: near |
| L-Town 24 h, bacterial regrowth (RK5) | 1.65 | 0.260 | 0.262 | 6.35x | 6.31x | **no**: near |
| L-Town 24 h, chloramine decay (ROS2) | 10.6 | 1.07 | 0.807 | 9.97x | 13.16x | **no**: near |
| NW Model 12 h, chlorine bulk + wall (Euler) | 14.0 | 0.964 | 0.952 | 14.53x | 14.71x | **no**: near |
| NW Model 12 h, bacterial regrowth (RK5) | 26.6 | 2.90 | 2.81 | 9.17x | 9.49x | **no**: near |
| NW Model 12 h, chloramine decay (ROS2) | 118 | 5.31 | 3.92 | 22.25x | 30.12x | **no**: near |
| **Median** |  |  |  | **9.57x** | **11.32x** | |
