Reference `base`; platform samples `base@nofma`, `base@fmafast`, `base@x86`; converged reference `bit@conv`. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), 2026-10-05.

### Platform variation

Each sample against the reference: the verdict, then the species furthest from it relative to its tier-B limit, with its largest absolute difference (and the largest relative difference), its 99th percentile, and the most nodes and links beyond tier B for any species. Concentrations in the species' own units. Report: lines that differ, and how far printed values and the mass balance move.

| Case | FMA off | FMA across statements | x86-64 | Reports |
| --- | --- | --- | --- | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | B: AGE max 0.02 (rel 0.002), p99 2.7e-05 | IDENTICAL | FAIL: TR1 max 0.013 (rel 0.09), p99 2e-06, beyond B 1 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| Net3, chloramine decay with full coupling (ROS2) | A: NH4 max 2.6e-09 (rel 2e-06), p99 1e-10 | A: NH4 max 2e-08 (rel 2e-05), p99 1.5e-10 | A: NH4 max 2.7e-09 (rel 2e-06), p99 9.4e-11 | FMA off: identical; FMA across statements: identical; x86-64: identical |

### Distance from the converged reference

Every build against `bit@conv` (integrator tolerances 1000 times tighter, Newton to 8 significant digits, Euler replaced by RK5; segments merged as before). The same measures as above.

| Case | `base` | `base@nofma` | `base@fmafast` | `base@x86` | `only:NEAR-01` | `only:NEAR-02` | `only:NEAR-03` | `near` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | A: AGE max 2.8e-13 (rel 7e-15), p99 5e-14 | B: AGE max 0.02 (rel 0.002), p99 2.7e-05 | A: AGE max 2.8e-13 (rel 7e-15), p99 5e-14 | FAIL: TR1 max 0.013 (rel 0.09), p99 2e-06, beyond B 1 | A: AGE max 2.8e-13 (rel 7e-15), p99 5e-14 | A: AGE max 2.8e-13 (rel 7e-15), p99 5e-14 | A: AGE max 2.8e-13 (rel 7e-15), p99 5e-14 | A: AGE max 2.8e-13 (rel 7e-15), p99 5e-14 |
| Net3, chloramine decay with full coupling (ROS2) | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 |

### `only:NEAR-01`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay with full coupling (ROS2) | IDENTICAL | identical | PASS | within tolerance, as every platform is |

### `only:NEAR-02`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay with full coupling (ROS2) | A: NH4 max 3e-12 (rel 1e-08), p99 2.8e-12 | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |

### `only:NEAR-03`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay with full coupling (ROS2) | IDENTICAL | identical | PASS | within tolerance, as every platform is |

### `near`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| BWSN2 48 h, water age and two source tracers (Euler) | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay with full coupling (ROS2) | A: NH4 max 3e-12 (rel 1e-08), p99 2.8e-12 | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |

Totals: PASS 8
