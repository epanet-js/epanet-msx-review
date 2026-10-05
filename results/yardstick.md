Reference `base`; platform samples `base@nofma`, `base@fmafast`, `base@x86`; converged reference `bit@conv`. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), 2026-10-05.

### Platform variation

Each sample against the reference: the verdict, then the species furthest from it relative to its tier-B limit, with its largest absolute difference (and the largest relative difference), its 99th percentile, and the most nodes and links beyond tier B for any species. Concentrations in the species' own units. Report: lines that differ, and how far printed values and the mass balance move.

| Case | FMA off | FMA across statements | x86-64 | Reports |
| --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | A: CL2 max 2.1e-05 (rel 0.0001), p99 1.7e-10 | IDENTICAL | A: CL2 max 1.2e-05 (rel 5e-05), p99 2.3e-10 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| Net6, chlorine bulk + wall | A: CL2 max 0.00013 (rel 0.0005), p99 1.8e-08 | A: CL2 max 0.00015 (rel 0.0006), p99 1.6e-08 | A: CL2 max 5.6e-05 (rel 0.0002), p99 1.6e-08 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| KY8, chlorine + dispersion | A: CL2 max 0.0011 (rel 0.003), p99 3.2e-07 | A: CL2 max 0.0011 (rel 0.003), p99 3.1e-07 | A: CL2 max 0.0011 (rel 0.003), p99 2.9e-07 | FMA off: MSX tables identical (and 23 lines of EPANET's hydraulic log); FMA across statements: MSX tables identical (and 22 lines of EPANET's hydraulic log); x86-64: MSX tables identical (and 21 lines of EPANET's hydraulic log) |
| Richmond, bacterial regrowth | FAIL: Nb max 1 (rel 4), p99 0.0019, beyond B 110 | IDENTICAL | FAIL: Nb max 0.87 (rel 0.2), p99 0.00095, beyond B 25 | FMA off: 7 lines, ≤1 last digit; mass balance 8e-05; FMA across statements: identical; x86-64: 5 lines; mass balance 3e-05 |
| Net3, chloramine decay | A: NH4 max 2.6e-09 (rel 2e-06), p99 1e-10 | A: NH4 max 2e-08 (rel 2e-05), p99 1.5e-10 | A: NH4 max 2.7e-09 (rel 2e-06), p99 9.4e-11 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| Net3, arsenic adsorption | FAIL: A5s max 5.4 (rel 2e+02), p99 1.1, beyond B 114 | FAIL: A5s max 2.4 (rel 1e+01), p99 0.13, beyond B 29 | FAIL: A5s max 5.7 (rel 2e+02), p99 1.1, beyond B 118 | FMA off: 19 lines, ≤20 last digit; mass balance 2e-05; FMA across statements: 10 lines, ≤1 last digit; mass balance 3e-05; x86-64: 16 lines, ≤20 last digit; mass balance 2e-05 |
| MSX example (4 nodes) | A: AS5 max 1.6e-14 (rel 2e-15), p99 8.9e-15 | IDENTICAL | A: AS5 max 1.6e-14 (rel 2e-15), p99 8.9e-15 | FMA off: identical; FMA across statements: identical; x86-64: identical |
| BWSN2, 2 species, every node and link every 5 min | A: S2 max 9.3e-06 (rel 4e-05), p99 1.6e-08 | IDENTICAL | A: S2 max 2.1e-05 (rel 8e-05), p99 1.5e-08 | FMA off: 2 lines, ≤1 last digit; FMA across statements: identical; x86-64: 1 lines, ≤1 last digit |
| Net3 chloramine, 14 species, every node and link every 5 min | A: NH4 max 1.3e-09 (rel 2e-06), p99 2.7e-11 | A: NH4 max 2.7e-09 (rel 3e-06), p99 3.3e-11 | A: NH4 max 1.8e-09 (rel 3e-06), p99 3.8e-11 | FMA off: identical; FMA across statements: identical; x86-64: identical |

### Distance from the converged reference

Every build against `bit@conv` (integrator tolerances 1000 times tighter, Newton to 8 significant digits, Euler replaced by RK5; segments merged as before). The same measures as above.

| Case | `base` | `base@nofma` | `base@fmafast` | `base@x86` | `only:NEAR-01` | `only:NEAR-02` | `only:NEAR-03` | `near` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 2.1e-05 (rel 0.0001), p99 1.7e-10 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 1.2e-05 (rel 5e-05), p99 2.3e-10 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 | A: CL2 max 1.6e-12 (rel 6e-11), p99 2.2e-16 |
| Net6, chlorine bulk + wall | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 | FAIL: CL2 max 0.042 (rel 0.2), p99 0.0019, beyond B 1017 |
| KY8, chlorine + dispersion | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 | FAIL: CL2 max 0.059 (rel 0.2), p99 0.0015, beyond B 108 |
| Richmond, bacterial regrowth | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | FAIL: Nb max 1 (rel 4), p99 0.0019, beyond B 110 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | FAIL: Nb max 0.87 (rel 0.2), p99 0.00095, beyond B 25 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 | A: Na max 6e-14 (rel 2e-14), p99 9.3e-15 |
| Net3, chloramine decay | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 |
| Net3, arsenic adsorption | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 27 (rel 9e+02), p99 7.1, beyond B 199 | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 26 (rel 1e+03), p99 7, beyond B 198 | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 27 (rel 1e+03), p99 7.1, beyond B 199 | FAIL: A5s max 26 (rel 1e+03), p99 7, beyond B 198 |
| MSX example (4 nodes) | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 | FAIL: AS5 max 0.0076 (rel 0.006), p99 8e-05, beyond B 1 |
| BWSN2, 2 species, every node and link every 5 min | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 1.7e-05 (rel 5e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 2.4e-05 (rel 9e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 | A: S2 max 1.6e-05 (rel 2e-05), p99 1.1e-05 |
| Net3 chloramine, 14 species, every node and link every 5 min | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 | FAIL: NH4 max 8.2e-08 (rel 0.002), p99 7.6e-08, beyond B 209 |

### `only:NEAR-01`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | A: CL2 max 1e-15 (rel 1e-15), p99 2.5e-24 | identical | PASS | within tolerance, as every platform is |
| Net6, chlorine bulk + wall | A: CL2 max 1.8e-15 (rel 4e-15), p99 2.2e-16 | identical | PASS | within tolerance, as every platform is |
| KY8, chlorine + dispersion | A: CL2 max 1.4e-15 (rel 3e-15), p99 1.7e-16 | identical | PASS | within tolerance, as every platform is |
| Richmond, bacterial regrowth | A: Nb max 2e-14 (rel 5e-15), p99 8.9e-16 | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Net3, arsenic adsorption | FAIL: A5s max 4.9 (rel 4e+01), p99 0.81, beyond B 126 | 19 lines, ≤5 last digit; mass balance 6e-05 | PASS | as close as the platforms |
| MSX example (4 nodes) | A: AS5 max 8.5e-14 (rel 5e-14), p99 5.5e-14 | identical | PASS | within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Net3 chloramine, 14 species, every node and link every 5 min | IDENTICAL | identical | PASS | within tolerance, as every platform is |

### `only:NEAR-02`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Net6, chlorine bulk + wall | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| KY8, chlorine + dispersion | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Richmond, bacterial regrowth | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay | A: NH4 max 3e-12 (rel 1e-08), p99 2.8e-12 | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |
| Net3, arsenic adsorption | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| MSX example (4 nodes) | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Net3 chloramine, 14 species, every node and link every 5 min | A: NH4 max 3e-12 (rel 1e-08), p99 2.8e-12 | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |

### `only:NEAR-03`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Net6, chlorine bulk + wall | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| KY8, chlorine + dispersion | A: CL2 max 1.1e-10 (rel 3e-10), p99 1.1e-13 | identical | PASS | within tolerance, as every platform is |
| Richmond, bacterial regrowth | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Net3, arsenic adsorption | IDENTICAL | identical | PASS | within tolerance where a platform is not |
| MSX example (4 nodes) | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Net3 chloramine, 14 species, every node and link every 5 min | IDENTICAL | identical | PASS | within tolerance, as every platform is |

### `near`

| Case | Candidate | Report | Judgement | Why |
| --- | --- | --- | --- | --- |
| BWSN2, two-source chlorine | A: CL2 max 1e-15 (rel 1e-15), p99 2.5e-24 | identical | PASS | within tolerance, as every platform is |
| Net6, chlorine bulk + wall | A: CL2 max 1.8e-15 (rel 4e-15), p99 2.2e-16 | identical | PASS | within tolerance, as every platform is |
| KY8, chlorine + dispersion | A: CL2 max 1.1e-10 (rel 3e-10), p99 1.1e-13 | identical | PASS | within tolerance, as every platform is |
| Richmond, bacterial regrowth | A: Nb max 2e-14 (rel 5e-15), p99 8.9e-16 | identical | PASS | within tolerance where a platform is not |
| Net3, chloramine decay | A: NH4 max 3e-12 (rel 1e-08), p99 2.8e-12 | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |
| Net3, arsenic adsorption | FAIL: A5s max 4.9 (rel 4e+01), p99 0.81, beyond B 126 | 19 lines, ≤5 last digit; mass balance 6e-05 | PASS | as close as the platforms |
| MSX example (4 nodes) | A: AS5 max 8.5e-14 (rel 5e-14), p99 5.5e-14 | identical | PASS | within tolerance, as every platform is |
| BWSN2, 2 species, every node and link every 5 min | IDENTICAL | identical | PASS | within tolerance, as every platform is |
| Net3 chloramine, 14 species, every node and link every 5 min | A: NH4 max 3e-12 (rel 1e-08), p99 2.8e-12 | 3 lines; mass balance 2e-06 | PASS | within tolerance, as every platform is |

Totals: PASS 36

### Cases judged by clause 2 or 3

#### `only:NEAR-01` on Net3, arsenic adsorption

Clause 2 applied. Per species, the 99th percentile of the difference from the reference and the number of nodes and links beyond tier B, for the candidate and each platform sample:

| Species | Candidate p99 / beyond B | FMA off | FMA across statements | x86-64 | Limit (2x the largest) | Within |
| --- | --- | --- | --- | --- | --- | --- |
| A3 | 8.2e-11 / 0 | 2.1e-10 / 0 | 2.8e-11 / 0 | 4.9e-10 / 0 | 0.005 / 5 | yes |
| A5 | 0.022 / 122 | 0.015 / 113 | 0.0064 / 24 | 0.014 / 118 | 0.03 / 236 | yes |
| A5w | 0.022 / 126 | 0.016 / 114 | 0.0068 / 29 | 0.015 / 116 | 0.033 / 232 | yes |
| A5s | 0.81 / 101 | 1.1 / 101 | 0.13 / 25 | 1.1 / 102 | 2.3 / 204 | yes |
| NH2CL | 0.0049 / 24 | 0.0045 / 20 | 0.0026 / 8 | 0.0044 / 21 | 0.0089 / 42 | yes |

Distance from the converged reference `bit@conv` (p99 / beyond B), clause 3:

| Species | Candidate | `base` | `base@nofma` | `base@fmafast` | `base@x86` | Limit | Within |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 0.005 / 5 | yes |
| A5 | 0.33 / 198 | 0.34 / 198 | 0.34 / 199 | 0.34 / 198 | 0.34 / 198 | 0.68 / 398 | yes |
| A5w | 0.33 / 198 | 0.34 / 199 | 0.34 / 199 | 0.34 / 199 | 0.34 / 199 | 0.68 / 398 | yes |
| A5s | 7 / 114 | 7.1 / 114 | 7.1 / 114 | 7.1 / 114 | 7.1 / 114 | 14 / 228 | yes |
| NH2CL | 0.0063 / 28 | 0.0065 / 26 | 0.0066 / 26 | 0.0064 / 28 | 0.0065 / 27 | 0.013 / 56 | yes |

#### `near` on Net3, arsenic adsorption

Clause 2 applied. Per species, the 99th percentile of the difference from the reference and the number of nodes and links beyond tier B, for the candidate and each platform sample:

| Species | Candidate p99 / beyond B | FMA off | FMA across statements | x86-64 | Limit (2x the largest) | Within |
| --- | --- | --- | --- | --- | --- | --- |
| A3 | 8.2e-11 / 0 | 2.1e-10 / 0 | 2.8e-11 / 0 | 4.9e-10 / 0 | 0.005 / 5 | yes |
| A5 | 0.022 / 122 | 0.015 / 113 | 0.0064 / 24 | 0.014 / 118 | 0.03 / 236 | yes |
| A5w | 0.022 / 126 | 0.016 / 114 | 0.0068 / 29 | 0.015 / 116 | 0.033 / 232 | yes |
| A5s | 0.81 / 101 | 1.1 / 101 | 0.13 / 25 | 1.1 / 102 | 2.3 / 204 | yes |
| NH2CL | 0.0049 / 24 | 0.0045 / 20 | 0.0026 / 8 | 0.0044 / 21 | 0.0089 / 42 | yes |

Distance from the converged reference `bit@conv` (p99 / beyond B), clause 3:

| Species | Candidate | `base` | `base@nofma` | `base@fmafast` | `base@x86` | Limit | Within |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 2.9e-06 / 0 | 0.005 / 5 | yes |
| A5 | 0.33 / 198 | 0.34 / 198 | 0.34 / 199 | 0.34 / 198 | 0.34 / 198 | 0.68 / 398 | yes |
| A5w | 0.33 / 198 | 0.34 / 199 | 0.34 / 199 | 0.34 / 199 | 0.34 / 199 | 0.68 / 398 | yes |
| A5s | 7 / 114 | 7.1 / 114 | 7.1 / 114 | 7.1 / 114 | 7.1 / 114 | 14 / 228 | yes |
| NH2CL | 0.0063 / 28 | 0.0065 / 26 | 0.0066 / 26 | 0.0064 / 28 | 0.0065 / 27 | 0.013 / 56 | yes |
