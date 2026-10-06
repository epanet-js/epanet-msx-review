Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); `-O3 -DNDEBUG`, OpenMP; best of 0 interleaved runs (one checked run); 2026-10-06 00:15 to 2026-10-06 00:40, load average 10.95 at the start and 27.42 at the end.

### step mode, 1 thread

| Case | bit (s) | near (s) | near speed-up | Identical |
| --- | ---: | ---: | ---: | --- |
| NW Model 12 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | 15.5 | 19.9 | 0.78x | yes |
| NW Model 12 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | 36.4 | 26.8 | 1.36x | **no**: near |
| NW Model 12 h, parallel second-order chlorine decay, two source waters blending (RK5) | 17.2 | 17.2 | 1.00x | yes |
| NW Model 12 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | 40.3 | 55.5 | 0.73x | **no**: near |
| NW Model 12 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | 80.2 | 52.5 | 1.53x | **no**: near |
| NW Model 12 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | 166 | 163 | 1.02x | yes |
| NW Model 12 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | 112 | 99.0 | 1.14x | **no**: near |
| BWSN2 6 h, chlorine (two reactants, temperature, wall) with THM and HAA (RK5) | 11.0 | 10.4 | 1.06x | yes |
| BWSN2 6 h, bacterial regrowth in bulk and biofilm with THM formation (RK5) | 17.9 | 16.7 | 1.08x | **no**: near |
| BWSN2 6 h, parallel second-order chlorine decay, two source waters blending (RK5) | 13.4 | 13.3 | 1.01x | yes |
| BWSN2 6 h, water temperature from heat exchange with the soil driving chlorine decay (RK5) | 31.2 | 30.6 | 1.02x | **no**: near |
| BWSN2 6 h, microbial intrusion: chlorine demand and inactivation of four organisms (ROS2) | 43.6 | 32.1 | 1.36x | **no**: near |
| BWSN2 6 h, PODDS discolouration: shear-driven erosion and regeneration (RK5, 60 s) | 77.5 | 86.6 | 0.89x | yes |
| BWSN2 6 h, VCDM discolouration: 17 material strength bands (Euler, 60 s) | 63.9 | 57.5 | 1.11x | **no**: near |
| **Median** |  |  | **1.04x** | |
