Reference `base`; platform samples `base@nofma`, `base@fmafast`, `base@x86`; converged reference `bit@conv`. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), 2026-10-05. Every 6th step compared.

### Platform variation

Each sample against the reference: the verdict, then the species furthest from it relative to its tier-B limit, with its largest absolute difference (and the largest relative difference), its 99th percentile, and the most nodes and links beyond tier B for any species. Concentrations in the species' own units. Report: lines that differ, and how far printed values and the mass balance move.

| Case | FMA off | FMA across statements | x86-64 | Reports |
| --- | --- | --- | --- | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | A: CL2 max 7.2e-05 (rel 0.004), p99 2.4e-07 | IDENTICAL | A: CL2 max 7.1e-05 (rel 0.002), p99 2.2e-07 | FMA off: FAIL: report structure differs; FMA across statements: identical; x86-64: FAIL: report structure differs |
| L-Town 24 h, bacterial regrowth (RK5) | A: CL2 max 2.9e-05 (rel 6e-05), p99 5.2e-07 | IDENTICAL | A: CL2 max 3.9e-05 (rel 8e-05), p99 5.2e-07 | FMA off: FAIL: report structure differs; FMA across statements: identical; x86-64: FAIL: report structure differs |
| L-Town 24 h, chloramine decay (ROS2) | A: NH4 max 5e-08 (rel 8e-05), p99 6.8e-10 | IDENTICAL | FAIL: NH4 max 6.2e-08 (rel 0.0003), p99 6.7e-10, beyond B 1 | FMA off: FAIL: report structure differs; FMA across statements: identical; x86-64: FAIL: report structure differs |
| NW Model 12 h, chlorine bulk + wall (Euler) | FAIL: CL2 max 0.012 (rel 0.05), p99 7.4e-07, beyond B 3 | FAIL: CL2 max 0.012 (rel 0.05), p99 6.9e-07, beyond B 3 | FAIL: CL2 max 0.012 (rel 0.05), p99 7.7e-07, beyond B 3 | FMA off: 18 lines, ≤9.5e+03 last digit; FMA across statements: 14 lines, ≤9.5e+03 last digit; x86-64: 16 lines, ≤6.2e+03 last digit |
| NW Model 12 h, bacterial regrowth (RK5) | B: Nb max 0.0086 (rel 0.002), p99 3.9e-06 | A: CL2 max 0.00048 (rel 0.0008), p99 4.9e-07 | A: Nb max 0.0018 (rel 0.0004), p99 4.4e-06 | FMA off: 18 lines, ≤9.5e+03 last digit; FMA across statements: 14 lines, ≤9.5e+03 last digit; x86-64: 16 lines, ≤6.2e+03 last digit |
| NW Model 12 h, chloramine decay (ROS2) | FAIL: NH4 max 2.1e-06 (rel 0.002), p99 7.8e-10, beyond B 11 | FAIL: NH4 max 8.9e-07 (rel 0.001), p99 8.7e-10, beyond B 12 | FAIL: NH4 max 6.5e-07 (rel 0.0008), p99 8.9e-10, beyond B 10 | FMA off: 18 lines, ≤9.5e+03 last digit; FMA across statements: 14 lines, ≤9.5e+03 last digit; x86-64: 16 lines, ≤6.2e+03 last digit |

### Distance from the converged reference

Every build against `bit@conv` (integrator tolerances 1000 times tighter, Newton to 8 significant digits, Euler replaced by RK5; segments merged as before). The same measures as above.

| Case | `base` | `base@nofma` | `base@fmafast` | `base@x86` | `only:NEAR-01` | `only:NEAR-02` | `only:NEAR-03` | `near` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | FAIL: CL2 max 0.028 (rel 1), p99 0.0099, beyond B 541 | FAIL: CL2 max 0.028 (rel 1), p99 0.0099, beyond B 541 | FAIL: CL2 max 0.028 (rel 1), p99 0.0099, beyond B 541 | FAIL: CL2 max 0.028 (rel 1), p99 0.0099, beyond B 541 | FAIL: CL2 max 0.028 (rel 1), p99 0.0099, beyond B 541 | FAIL: CL2 max 0.028 (rel 1), p99 0.0099, beyond B 541 | FAIL: CL2 max 0.028 (rel 1), p99 0.0099, beyond B 541 | FAIL: CL2 max 0.028 (rel 1), p99 0.0099, beyond B 541 |
| L-Town 24 h, bacterial regrowth (RK5) | A: Na max 4.4e-14 (rel 1e-14), p99 8e-15 | A: CL2 max 2.9e-05 (rel 6e-05), p99 5.2e-07 | A: Na max 4.4e-14 (rel 1e-14), p99 8e-15 | A: CL2 max 3.9e-05 (rel 8e-05), p99 5.2e-07 | A: Na max 4.4e-14 (rel 1e-14), p99 8e-15 | A: Na max 4.4e-14 (rel 1e-14), p99 8e-15 | A: Na max 4.4e-14 (rel 1e-14), p99 8e-15 | A: Na max 4.4e-14 (rel 1e-14), p99 8e-15 |
| L-Town 24 h, chloramine decay (ROS2) | FAIL: NH4 max 7.5e-08 (rel 0.0009), p99 6.2e-08, beyond B 1341 | FAIL: NH4 max 7.6e-08 (rel 0.0009), p99 6.2e-08, beyond B 1341 | FAIL: NH4 max 7.5e-08 (rel 0.0009), p99 6.2e-08, beyond B 1341 | FAIL: NH4 max 7.5e-08 (rel 0.0009), p99 6.2e-08, beyond B 1343 | FAIL: NH4 max 7.5e-08 (rel 0.0009), p99 6.2e-08, beyond B 1341 | FAIL: NH4 max 7.5e-08 (rel 0.0009), p99 6.2e-08, beyond B 1341 | FAIL: NH4 max 7.5e-08 (rel 0.0009), p99 6.2e-08, beyond B 1341 | FAIL: NH4 max 7.5e-08 (rel 0.0009), p99 6.2e-08, beyond B 1341 |
| NW Model 12 h, chlorine bulk + wall (Euler) | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0025, beyond B 1458 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0025, beyond B 1458 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0025, beyond B 1458 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0025, beyond B 1458 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0025, beyond B 1458 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0025, beyond B 1458 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0025, beyond B 1458 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0025, beyond B 1458 |
| NW Model 12 h, bacterial regrowth (RK5) | A: Na max 3e-12 (rel 1e-12), p99 1.9e-14 | B: Nb max 0.0086 (rel 0.002), p99 3.9e-06 | A: CL2 max 0.00048 (rel 0.0008), p99 4.9e-07 | A: Nb max 0.0018 (rel 0.0004), p99 4.4e-06 | A: Na max 3e-12 (rel 1e-12), p99 1.9e-14 | A: Na max 3e-12 (rel 1e-12), p99 1.9e-14 | A: Na max 3e-12 (rel 1e-12), p99 1.9e-14 | A: Na max 3e-12 (rel 1e-12), p99 1.9e-14 |
| NW Model 12 h, chloramine decay (ROS2) | FAIL: NH4 max 7.8e-08 (rel 0.0008), p99 6e-08, beyond B 18435 | FAIL: NH4 max 2.1e-06 (rel 0.002), p99 6e-08, beyond B 18435 | FAIL: NH4 max 9.3e-07 (rel 0.001), p99 6e-08, beyond B 18435 | FAIL: NH4 max 6.9e-07 (rel 0.0008), p99 6e-08, beyond B 18435 | FAIL: NH4 max 7.8e-08 (rel 0.0008), p99 6e-08, beyond B 18435 | FAIL: NH4 max 7.8e-08 (rel 0.0008), p99 6e-08, beyond B 18435 | FAIL: NH4 max 7.8e-08 (rel 0.0008), p99 6e-08, beyond B 18435 | FAIL: NH4 max 7.8e-08 (rel 0.0008), p99 6e-08, beyond B 18435 |

### `only:NEAR-01`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | A: CL2 max 1.8e-15 (rel 4e-15), p99 1.1e-16 | identical | PASS | within tolerance, as every platform is |
| L-Town 24 h, bacterial regrowth (RK5) | A: Nb max 4.9e-15 (rel 1e-15), p99 8.9e-16 | identical | PASS | within tolerance, as every platform is |
| L-Town 24 h, chloramine decay (ROS2) | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| NW Model 12 h, chlorine bulk + wall (Euler) | A: CL2 max 2.4e-15 (rel 6e-15), p99 1.7e-16 | identical | PASS | within tolerance where a platform is not |
| NW Model 12 h, bacterial regrowth (RK5) | A: Nb max 2e-14 (rel 6e-15), p99 8.9e-16 | identical | PASS | within tolerance, as every platform is |
| NW Model 12 h, chloramine decay (ROS2) | IDENTICAL | identical | PASS | within tolerance where a platform is not |

### `only:NEAR-02`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| L-Town 24 h, bacterial regrowth (RK5) | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| L-Town 24 h, chloramine decay (ROS2) | A: NH4 max 2.8e-12 (rel 8e-09), p99 2.3e-12 | identical | PASS | within tolerance where a platform is not |
| NW Model 12 h, chlorine bulk + wall (Euler) | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| NW Model 12 h, bacterial regrowth (RK5) | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| NW Model 12 h, chloramine decay (ROS2) | A: NH4 max 2.9e-12 (rel 8e-09), p99 2.2e-12 | identical | PASS | within tolerance where a platform is not |

### `only:NEAR-03`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| L-Town 24 h, bacterial regrowth (RK5) | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| L-Town 24 h, chloramine decay (ROS2) | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| NW Model 12 h, chlorine bulk + wall (Euler) | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| NW Model 12 h, bacterial regrowth (RK5) | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| NW Model 12 h, chloramine decay (ROS2) | IDENTICAL | identical | PASS | within tolerance where a platform is not |

### `near`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| L-Town 24 h, chlorine bulk + wall (Euler) | A: CL2 max 1.8e-15 (rel 4e-15), p99 1.1e-16 | identical | PASS | within tolerance, as every platform is |
| L-Town 24 h, bacterial regrowth (RK5) | A: Nb max 4.9e-15 (rel 1e-15), p99 8.9e-16 | identical | PASS | within tolerance, as every platform is |
| L-Town 24 h, chloramine decay (ROS2) | A: NH4 max 2.8e-12 (rel 8e-09), p99 2.3e-12 | identical | PASS | within tolerance where a platform is not |
| NW Model 12 h, chlorine bulk + wall (Euler) | A: CL2 max 2.4e-15 (rel 6e-15), p99 1.7e-16 | identical | PASS | within tolerance where a platform is not |
| NW Model 12 h, bacterial regrowth (RK5) | A: Nb max 2e-14 (rel 6e-15), p99 8.9e-16 | identical | PASS | within tolerance, as every platform is |
| NW Model 12 h, chloramine decay (ROS2) | A: NH4 max 2.9e-12 (rel 8e-09), p99 2.2e-12 | identical | PASS | within tolerance where a platform is not |

Totals: PASS 24
