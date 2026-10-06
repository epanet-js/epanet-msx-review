# Reproducing the results

[All changes](README.md)

Every number in this repository can be checked on your own machine. This page goes through the claims in the order a reviewer is likely to check them. [benchmarking.md](benchmarking.md) describes the tools in full.

## What you need

- **macOS**: the Xcode command line tools (`xcode-select --install`), Homebrew's OpenMP runtime (`brew install libomp`) and Python 3. On Apple silicon, the x86-64 platform sample of the near-identical checks needs Rosetta (`softwareupdate --install-rosetta`).
- **Linux**: GCC (or clang with libomp), git and Python 3; clang too for the Linux platform samples (`base@clang`).
- For the near-identical verdicts only: numpy (`pip install numpy`).
- About 1 GB of disk for builds, and more for the near-identical checks on the larger networks.

```sh
git clone --recurse-submodules https://github.com/epanet-js/epanet-msx-review.git
cd epanet-msx-review
```

The `msx` folder is a submodule: EPANET-MSX at [85a303d](https://github.com/USEPA/EPANETMSX/commit/85a303dca05859389eced63fabd5ea145c096333), the head of `main` when this work was done, with its own EPANET2.2 submodule at 1e2fc3d. If you cloned without `--recurse-submodules`, the scripts fetch it the first time. To use an MSX clone you already have, set `MSX_SRC` to its path; the scripts export from it with `git archive` and never change it.

## 1. The bit-identical changes leave every result unchanged

```sh
tools/try.py bit --quick
```

This builds 85a303d and the bit-identical series (FIX-01, FIX-02, BIT-01 to BIT-17) with the same compiler and flags, runs the 7 main cases in step mode at 1 and 8 threads and in solve mode, and compares a hash of every concentration of every species at every node and link after every step, and in solve mode the binary output file and the report. It takes about 3 minutes. In the table of speed-ups it prints, the Results column should say `identical`. Without `--quick` it keeps the best of a checked run and 3 timed runs, interleaved (about 10 minutes).

To check one group, or the series up to it:

```sh
tools/try.py BIT-06 --against BIT-05       # BIT-06 on its own: the table in its README
tools/try.py BIT-10                        # the series up to BIT-10
tools/try.py bit@noomp --quick             # the series built without OpenMP
tools/try.py bit --cases output --quick    # the output-heavy cases
```

## 2. The near-identical changes move results by less than the platforms already differ

```sh
tools/try.py only:NEAR-01 only:NEAR-02 only:NEAR-03 near --quick
```

Each `only:NEAR-NN` is the bit-identical series plus that one change. Where results differ, `tools/try.py` builds 85a303d three other ways (without fused multiply-add, with it across statements, and for x86-64 under Rosetta on macOS, and on Linux four ways, with clang and `-march=native` in place of x86-64) and a converged reference, and applies [the acceptance rule](2-near-identical/README.md#how-within-tolerance-was-decided) species by species. The platform samples take a few minutes the first time and are reused afterwards. The full acceptance table, and the check that results do not depend on the thread count, come from:

```sh
tools/yardstick.py run --builds base,base@nofma,base@fmafast,base@x86,bit@conv,only:NEAR-01,only:NEAR-02,only:NEAR-03,near --cases main,output
tools/yardstick.py threads --builds only:NEAR-01,only:NEAR-02,only:NEAR-03,near
```

On Linux, replace `base@x86` with `base@clang,base@native`.

## 3. The speed-ups

The headline and per-case tables come from `tools/run-all.sh` (see [results/](results/README.md)). To remake one table without touching the repository, run the step's `tools/bench.py` command (listed in `tools/run-all.sh`) yourself; its summary goes to `.build/results/`:

```sh
tools/bench.py --builds base,bit,near --threads 1,8,default --reps 5 --tag headline-step   # the headline
tools/bench.py --builds base,bit,near --cases real --threads 1,8 --reps 0 --tag real       # L-Town and the NW Model (about 20 minutes)
```

`tools/run-all.sh headline-step` does the same and then copies every result into `results/` and rewrites the READMEs' tables; `git diff` shows what moved.

Speed-ups depend on the machine. The ones here are from an Apple M1 Pro (8 performance and 2 efficiency cores) that was in use at the time; the load average is recorded with every measurement. On another machine, expect the same pattern rather than the same numbers.

## 4. The bug fixes

The three fixes leave results unchanged on every benchmark case; `tools/try.py FIX-01 FIX-02 FIX-03 --quick` shows it. Each fix's README describes how the bug shows and how it was reproduced. Test programs for them (`FIX-NN_test.c`, run against a sanitizer build, `NAME@asan`) are not in the repository yet.

## 5. With the project's own build

The tools compile MSX directly, with the flags of CMake's Release build. To check with the project's own CMake build, apply the patches to an MSX checkout ([benchmarking.md](benchmarking.md#applying-the-patches)) and build it as its README says:

```sh
cmake -B build . && cmake --build build --config Release
cd Examples && ../build/src/run/runepanetmsx example.inp example.msx out.rpt
```

With [BIT-01](1-bit-identical/BIT-01-build-defaults/), that command compiles with optimisation and, on macOS, finds Homebrew's libomp. MSX has no unit tests of its own, and `Examples/example.rpt` at 85a303d is not a report of the example (it ends with an EPANET error), so compare with an unpatched build instead: build a second checkout at 85a303d the same way (here `../msx-unpatched`), run the same command there, and compare the two reports apart from the date and time lines:

```sh
strip() { grep -v -E 'Page [0-9]|Analysis (begun|ended)' "$1"; }
diff <(strip ../../msx-unpatched/Examples/out.rpt) <(strip out.rpt) && echo identical
```

With the bit-identical patches the reports are the same.

## 6. Newer versions

```sh
tools/check.py              # upstream dev: do the patches apply, and do they still leave its results unchanged?
tools/check.py --prs        # also: how far the series applies to each open pull request
```

[status.md](status.md) holds the last check.

## 7. Your own models

```sh
cp ~/models/town.inp models/private/
tools/private-reactions.py models/private/town.inp       # chlorine, bacteria and chloramine reaction files
tools/try.py bit near --cases private --quick
```

[models/private/README.md](models/private/README.md) explains how to report back without sharing the model.

## 8. The published reaction models

```sh
tools/try.py bit near --cases literature --quick                         # the seven models on L-Town, dispersion on BWSN2
tools/run-all.sh literature yardstick-literature                         # the table, and the acceptance check of near (about an hour)
tools/private-reactions.py models/private/town.inp --kinds literature    # the seven models for a network of your own
```

[models/literature.md](models/literature.md) gives their sources, equations and assumptions. On L-Town the unpatched code takes up to about three minutes per model on one thread; on the larger networks (`--cases literature-large`) it takes many minutes even on eight, which is why `tools/run-all.sh` runs it on eight threads only there.
