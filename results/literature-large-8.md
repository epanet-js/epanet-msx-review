Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 0 interleaved runs (one checked run); 2026-10-05 22:22 to 2026-10-06 00:15, load average 9.65 at the start and 10.95 at the end.

### step mode, 8 threads

| Case | base (s) | bit (s) | near (s) | bit speed-up | near speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| NW Model 12 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | 147 | 2.93 | 3.25 | 50.22x | 45.31x | yes |
| NW Model 12 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | 250 | 5.59 | 5.15 | 44.75x | 48.58x | **no**: near |
| NW Model 12 h, parallel second-order chlorine decay, two source waters blending (RK5) | 516 | 4.86 | 4.58 | 106.15x | 112.60x | yes |
| NW Model 12 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | 362 | 6.68 | 8.50 | 54.18x | 42.59x | **no**: near |
| NW Model 12 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | 240 | 10.1 | 8.79 | 23.70x | 27.26x | **no**: near |
| NW Model 12 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | 497 | 52.7 | 56.4 | 9.42x | 8.81x | yes |
| NW Model 12 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | 527 | 54.5 | 50.6 | 9.67x | 10.42x | **no**: near |
| BWSN2 6 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | 142 | 2.36 | 2.20 | 60.03x | 64.49x | yes |
| BWSN2 6 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | 240 | 4.77 | 4.49 | 50.31x | 53.35x | **no**: near |
| BWSN2 6 h, parallel second-order chlorine decay, two source waters blending (RK5) | 437 | 1.93 | 1.90 | 226.51x | 229.85x | yes |
| BWSN2 6 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | 340 | 3.98 | 4.33 | 85.31x | 78.40x | **no**: near |
| BWSN2 6 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | 261 | 8.98 | 6.44 | 29.06x | 40.54x | **no**: near |
| BWSN2 6 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | 362 | 22.2 | 22.4 | 16.29x | 16.17x | yes |
| BWSN2 6 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | 330 | 21.6 | 23.1 | 15.25x | 14.31x | **no**: near |
| **Median** |  |  |  | **47.48x** | **43.95x** | |
