# Status against the latest EPANET-MSX

[All changes](README.md)

Checked on 5 October 2026 against EPANET-MSX `dev` at [f11bf1d](https://github.com/USEPA/EPANETMSX/commit/f11bf1d0310c74f64ccbe2c4984edbf59459833c) (2026-03-30 Merge pull request #24 from LRossman/dev-Cmake+msxout_fixes), with `tools/check.py`. It pins EPANET 2.2 at 1e2fc3d, as 85a303d does. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1); one checked run per build on the 7 main cases; load average 57.02 at the start and 17.75 at the end. The machine was busy (a load average above its core count), so treat the speed-ups as rough; `tools/check.py --reps 3` measures them again more carefully.

## Upstream changes since 85a303d

- `f11bf1d` 2026-03-30: Merge pull request #24 from LRossman/dev-Cmake+msxout_fixes
- `10ac6e2` 2026-03-30: Merge pull request #21 from LRossman/dev-tempfile_fix
- `e013d84` 2026-03-28: Adds to CMakeLists and fixes msxout.c
- `ea76825` 2026-03-27: Replace contents of MSXutils_getTempName
- `2730907` 2026-03-27: Merge pull request #20 from USEPA/master

## Speed

Median speed-up over 85a303d, per case:

| How MSX is run | f11bf1d | 85a303d + bit-identical | f11bf1d + bit-identical | 85a303d + near-identical | f11bf1d + near-identical |
| --- | ---: | ---: | ---: | ---: | ---: |
| Step, 1 thread | 1.00x | 16.46x | 19.25x | 18.35x | 19.36x |
| Step, 8 threads | 0.99x | 10.60x | 9.52x | 9.98x | 9.08x |
| Solve, 1 thread | 1.04x | 18.15x | 18.22x | 18.33x | 18.97x |

## The patches on this version

- Applied: 21
- Applied (3-way merge): 1 (BIT-15)
- Does not apply (a fix; skipped): 1 (FIX-03)

Each fix on its own (a fix that no longer applies may be fixed upstream another way; its README says what is known, and its test, once added, will tell):

| Fix | On this version |
| --- | --- |
| [FIX-01](3-bug-fixes/FIX-01-reaction-loop-error-race/) | applied |
| [FIX-02](3-bug-fixes/FIX-02-zero-flow-segment-leak/) | applied |
| [FIX-03](3-bug-fixes/FIX-03-tempfile-descriptor-leak/) | does not apply |

## Results

- With the bit-identical patches, f11bf1d's results are unchanged in all 21 runs.
- f11bf1d's own results are the same as 85a303d's in all 21 runs.

## Each patch

| Patch | State |
| --- | --- |
| FIX-01 | applied |
| FIX-02 | applied |
| FIX-03 | does not apply (a fix; skipped) |
| BIT-01 | applied |
| BIT-02 | applied |
| BIT-03 | applied |
| BIT-04 | applied |
| BIT-05 | applied |
| BIT-06 | applied |
| BIT-07 | applied |
| BIT-08 | applied |
| BIT-09 | applied |
| BIT-10 | applied |
| BIT-11 | applied |
| BIT-12 | applied |
| BIT-13 | applied |
| BIT-14 | applied |
| BIT-15 | applied (3-way merge) |
| BIT-16 | applied |
| BIT-17 | applied |
| NEAR-01 | applied |
| NEAR-02 | applied |
| NEAR-03 | applied |

## Open pull requests

Whether the series applies on top of each open pull request (FIX-01 to NEAR-03 in order; no build).

| Pull request | Updated | Series |
| --- | --- | --- |
| [#29](https://github.com/USEPA/EPANETMSX/pull/29) Fix cross-compiler compatibility issues | 2026-09-30 | stops at BIT-02, which does not apply; FIX-03 skipped (does not apply) |
| [#28](https://github.com/USEPA/EPANETMSX/pull/28) Fix reactions with no rate species | 2026-09-30 | every patch applies |
