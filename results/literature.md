Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 0 interleaved runs (one checked run); 2026-10-05 21:46 to 2026-10-05 22:08, load average 10.45 at the start and 7.77 at the end.

### step mode, 1 thread

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| L-Town 24 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | 33.2 | 1.41 | 1.34 | 23.54x | 24.75x | yes |
| L-Town 24 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | 81.8 | 2.18 | 1.92 | 37.59x | 42.58x | **no**: near |
| L-Town 24 h, parallel second-order chlorine decay, two source waters blending (RK5) | 128 | 1.75 | 1.67 | 72.85x | 76.19x | yes |
| L-Town 24 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | 121 | 3.26 | 3.45 | 37.15x | 35.14x | **no**: near |
| L-Town 24 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | 96.9 | 7.16 | 5.19 | 13.54x | 18.68x | **no**: near |
| L-Town 24 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | 136 | 11.5 | 11.6 | 11.83x | 11.74x | yes |
| L-Town 24 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | 187 | 8.41 | 8.11 | 22.27x | 23.09x | **no**: near |
| BWSN2 6 h, chlorine bulk and wall decay with dispersion (Euler, 60 s) | 135 | 7.55 | 6.05 | 17.93x | 22.39x | **no**: near |
| **Median** |  |  |  | **22.91x** | **23.92x** | |

### step mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| L-Town 24 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | 8.09 | 0.540 | 0.481 | 14.97x | 16.83x | yes |
| L-Town 24 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | 20.2 | 0.723 | 0.475 | 27.88x | 42.50x | **no**: near |
| L-Town 24 h, parallel second-order chlorine decay, two source waters blending (RK5) | 32.6 | 1.03 | 0.951 | 31.65x | 34.33x | yes |
| L-Town 24 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | 32.2 | 1.13 | 0.956 | 28.54x | 33.71x | **no**: near |
| L-Town 24 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | 18.7 | 1.46 | 1.23 | 12.79x | 15.18x | **no**: near |
| L-Town 24 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | 31.1 | 2.61 | 2.62 | 11.91x | 11.85x | yes |
| L-Town 24 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | 48.8 | 2.82 | 2.69 | 17.29x | 18.15x | **no**: near |
| BWSN2 6 h, chlorine bulk and wall decay with dispersion (Euler, 60 s) | 28.0 | 2.42 | 2.22 | 11.55x | 12.61x | **no**: near |
| **Median** |  |  |  | **16.13x** | **17.49x** | |
