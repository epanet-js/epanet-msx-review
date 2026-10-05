# Measuring EPANET-MSX

[All changes](README.md)

Everything here runs on macOS (Apple clang and Homebrew's `libomp`) or Linux (GCC, or clang with OpenMP), with git and Python 3. The tolerance verdicts for near-identical changes also need numpy. Windows is not supported; WSL works. `tools/try.py`, `tools/bench.py`, `tools/build-msx.sh` and `tools/yardstick.py` write only into `.build/`, which git ignores, and no source checkout is ever changed. The scripts that remake this repository's pages (`tools/run-all.sh`, `tools/update-docs.py`, `tools/check.py`) write to `results/`, `status.md` and the READMEs.

```sh
git clone --recurse-submodules https://github.com/epanet-js/epanet-msx-review.git
cd epanet-msx-review
brew install libomp                  # macOS only
tools/try.py bit --quick             # the bit-identical series against 85a303d: about 3 minutes
```

## tools/try.py

`tools/try.py` is the way in. It builds the unpatched code (EPANET-MSX at [85a303d](https://github.com/USEPA/EPANETMSX/commit/85a303dca05859389eced63fabd5ea145c096333), EPANET 2.2 at 1e2fc3d) on your machine as the baseline, builds each target the same way, times them, and says whether their results are identical to the baseline's:

```sh
tools/try.py                         # bit, near and all, against 85a303d, on the 7 main cases
tools/try.py BIT-07                  # the series up to BIT-07
tools/try.py only:NEAR-02 FIX-02     # one near-identical change alone; one fix alone
tools/try.py dev dev:bit dev:near    # upstream dev as it is, and with the patches on top
tools/try.py pull/28:bit --quick     # a pull request, with the patches
tools/try.py ~/src/my-msx            # your own MSX source tree, as it is on disk
tools/try.py ~/src/my-msx:bit        # ... with the bit-identical patches applied to it
tools/try.py near+my.patch           # the series and a patch of your own
tools/try.py near --cases private    # your own models (models/private/README.md)
tools/try.py BIT-06 --against BIT-05 # one group on its own: before and after
```

A target is `[SOURCE:]NAME[@FLAVOUR]`: a build name from [the table below](#the-builds), on 85a303d unless a source is given. The source can be an MSX commit, tag, branch (`dev`, `main`), `pull/<number>`, or a directory holding an MSX source tree. A target on another source also gets that source's own unpatched build, so that upstream's own changes stay apart from the patches': its speed is shown against 85a303d, and its results are judged against its own base.

For each case it runs step mode at 1 and 8 threads (`--threads`) and solve mode at one thread. Each build is first run once with a check (a hash of every concentration of every species at every node and link after every step; in solve mode also the MD5 of the binary output file and of the report), then `--reps` times (default 3), builds interleaved, and the best of all these runs is kept (reading the values for the hash is not timed). `--quick` makes one checked run per build, which is also the timed run, and reuses the baseline's last results on this machine if neither its build nor the models have changed (marked †). On the larger cases (`--cases real`, `--cases private`) the baseline's results are always reused when they can be, because the unpatched code takes minutes there; `--retime` measures it again.

It prints the speed-up per target (median over the cases, and the range) and per case, and whether results are identical. Where they are not, it judges them with [the near-identical rule](2-near-identical/README.md#how-within-tolerance-was-decided), species by species: it builds the baseline three other ways (four on Linux) to see how much its results already vary between platforms, and a converged reference, and runs only the cases that differ. The summary goes to `.build/results/try-<date>-<targets>.md` (and `.json`). It names private models only as `Private model 1, 2, ...`, so it is safe to paste into an issue. The exit code is 0 when every target's results are what its patches' headers say (`Results: identical` or `near`).

## The builds

`tools/build-msx.sh NAME` builds into `.build/<msx commit>/<NAME>/`, which git ignores; every other script calls it.

| Name | What is built |
|---|---|
| `base` | MSX as it is, with no patches |
| `FIX-02` | FIX-02 on its own (fixes apply alone; any patch named in a `Requires:` line comes too) |
| `fixes` | FIX-01, FIX-02 and FIX-03 |
| `BIT-07` | FIX-01 and FIX-02, which the bit-identical series builds on, then BIT-01 to BIT-07 |
| `bit` | FIX-01, FIX-02, BIT-01 to BIT-17 (the same as `BIT-17`) |
| `NEAR-02` | `bit`, then NEAR-01 and NEAR-02 |
| `only:NEAR-02` | `bit`, then NEAR-02 alone (each near-identical change applies on its own) |
| `near` | `bit`, then NEAR-01 to NEAR-03 |
| `all` | Every patch: FIX-01 to FIX-03, BIT-01 to BIT-17, NEAR-01 to NEAR-03 |
| `bit+FIX-03`, `near+my.patch` | Several names or patch files joined with `+`, applied in series order, files last |
| `dev:bit`, `pull/28:near` | Any of the above on another MSX version |
| `NAME@noomp` | Without OpenMP, as when CMake finds none |
| `NAME@O0` | No optimisation, as a plain `cmake -B build .` builds it with the Makefile or Ninja generator ([BIT-01](1-bit-identical/BIT-01-build-defaults/)) |
| `NAME@nofma` | `-ffp-contract=off`: no fused multiply-add, as x86-64 builds and MSVC `/fp:precise` |
| `NAME@fmafast` | `-ffp-contract=fast`: fused multiply-add across statements, GCC's default on 64-bit ARM Linux |
| `NAME@x86` | macOS only: built for x86-64 and run under Rosetta, without OpenMP (Homebrew's libomp is arm64 only; results do not depend on the thread count) |
| `NAME@clang`, `NAME@native` | Linux: built with clang; built for this processor (`-march=native`). The Linux platform samples |
| `bit@conv` | The converged reference: `bit` (whose results are 85a303d's) with [`tools/converged.patch`](tools/converged.patch) |
| `NAME@asan` | AddressSanitizer and UndefinedBehaviorSanitizer, `-O1 -g`, OpenMP kept |

MSX and EPANET 2.2 are built as shared libraries, as the project's CMake build does by default, with `$CC` (default `cc`) and `$CFLAGS` (default `-O3 -DNDEBUG`, CMake's Release flags) and OpenMP (`-fopenmp`; on macOS `-Xpreprocessor -fopenmp` with Homebrew's libomp, or `$LIBOMP`). The build folder holds `libepanet2`, `libepanetmsx`, the benchmark driver `bench`, `runepanetmsx`, and `patches.txt`, which records what happened to each patch. A build is reused while its source, compiler, flags and patches are unchanged; editing a patch's description does not rebuild it.

The source is exported from the `msx` submodule with `git archive`, and EPANET 2.2 at the commit that MSX commit pins. To build from an MSX clone of your own, set `MSX_SRC`; to build a working tree as it is on disk, give its directory as the source (`tools/try.py ~/src/my-msx`) or set `MSX_TREE`.

## Applying the patches

Each change's folder has its patch, `<ID>.patch`. The text above the first `diff --git` line says what the patch changes and why, its `Requires:` and its `Results:`; `git apply` ignores that text. The patches form one series, applied in this order: FIX-01 to FIX-03, BIT-01 to BIT-17, NEAR-01 to NEAR-03. Each bit-identical patch is made against the tree that FIX-01, FIX-02 and the bit-identical patches before it produce. Each near-identical patch applies on its own after BIT-17. Each fix applies on its own to 85a303d.

From the root of an EPANET-MSX checkout at 85a303d (some patched lines keep the original code's trailing spaces):

```sh
R=../epanet-msx-review
for p in $($R/tools/patch-order.sh bit); do
    case "$p" in
        *BIT-16*) git -C EPANET2.2 apply --whitespace=nowarn "$p" ;;   # a patch to EPANET 2.2
        *)        git apply --whitespace=nowarn "$p" ;;
    esac
done
```

`tools/patch-order.sh NAME` lists a build's patches in order. [BIT-16](1-bit-identical/BIT-16-epanet-savehydfile-block-copy/) is a patch to the EPANET2.2 submodule (its paths start with `SRC_engines/`); all the others are patches to MSX. [BIT-17](1-bit-identical/BIT-17-compact-segments/) trades memory for speed and can be left out.

On a newer MSX, where a patch no longer applies as it stands, git can often merge it three ways. `tools/build-msx.sh` does that automatically: it replays the series on 85a303d once, in `.build/objects/`, so that every patch's original blobs exist, and borrows those objects when it applies the series elsewhere. By hand, the same works with `git apply --3way` in an MSX clone that has those objects.

## The driver

`bench FILE.inp FILE.msx [-mode step|solve|read|info] [-reps N] [-check] [-dump FILE] [-dumpevery N]` opens EPANET and MSX, solves the hydraulics with `MSXsolveH`, and runs the water quality:

| Mode | What it runs | Results compared |
|---|---|---|
| `step` | `MSXinit(0)` and an `MSXstep` loop, as a toolkit program does | With `-check`: a hash of every node's and link's concentration of every species after every step (read with `MSXgetqual`, untimed) |
| `solve` | What `runepanetmsx` does: `MSXinit(1)`, the `MSXstep` loop, `MSXreport`, `MSXsaveoutfile` | The same hash, plus the MD5 of the binary output file and of the report (EPANET's date and time stamps removed) |
| `read` | Step mode, also reading every node and link concentration of every species with `MSXgetqual` after every step, timed | The same hash |
| `info` | Nothing is run: the model's size and settings (counts and times only, no IDs) | - |

It prints the time spent opening (`ENopen`, `MSXopen`), in `MSXsolveH`, in quality (`MSXinit` and every `MSXstep`), reporting and closing (the minimum over `-reps` repetitions in one process), and the peak resident memory. `-dump` writes every concentration after every step as float64 for [`tools/compare.py`](tools/compare.py); `-dumpevery N` keeps every Nth step, for large networks.

## Timing

`tools/bench.py` is the lower-level timer that `tools/try.py` and `tools/run-all.sh` use:

```sh
tools/bench.py --builds base,BIT-05,BIT-06 --cases rich-bact,ky8-disp --threads 1,8 --reps 5
tools/bench.py --builds BIT-13,BIT-14 --cases output --modes solve,read
tools/bench.py --builds base,bit,near --cases real --reps 0      # one checked run each
```

`--cases` takes groups (`main`, `output`, `real`, `public` for all three, `private`) and case IDs from [models/cases.json](models/cases.json). For each case, mode and thread count it runs each build once with `-check`, then `--reps` times without it (`--reps 0`: the checked run alone), builds interleaved so that background load affects them alike, and keeps the fastest of all these runs. The first build is the reference for speed-ups and for the "Identical" column. Thread counts are set with `OMP_NUM_THREADS`; `default` leaves it unset, so OpenMP uses every core (10 on an M1 Pro). Every result records the load average at its start and end. Results go to `.build/results/<tag>.json` and `.md`.

**Timing advice.** On Apple silicon, run-to-run noise is about 1-2 % at one thread on a quiet machine and much more with something else running; at eight threads timings vary more, partly because the system may place threads on the slower efficiency cores. Do not run two benchmarks at once. The tables in this repository were made on a machine in use, as one quick pass (see below); treat differences under about 5 % at one thread and 20 % at eight threads as noise there.

## Checking results

A change is **bit-identical** when, on every case, the hash of every concentration after every step is the same in step mode at 1 and 8 threads, in read mode, and in solve mode, where the binary output file and the report are also byte-for-byte the same, as for the unpatched build; and the same holds built without OpenMP. The unpatched code itself gives the same concentrations at any thread count; before [BIT-11](1-bit-identical/BIT-11-dispersion-mass-without-locks/), the dispersion term of its mass balance could change in its last digits between runs. [verification.md](verification.md) has the table.

## Near-identical changes

Changes in [2-near-identical/](2-near-identical/README.md) alter results, so they are compared value by value, against how much the unpatched code already varies between platforms. [The category page](2-near-identical/README.md#how-within-tolerance-was-decided) explains the rule; these are the tools:

```sh
tools/yardstick.py run --builds base,base@nofma,base@fmafast,base@x86,bit@conv,only:NEAR-01,only:NEAR-02,only:NEAR-03,near \
                       --cases main,output
tools/yardstick.py run --builds ... --cases real --dumpevery 6    # the larger networks
tools/yardstick.py threads --builds only:NEAR-01,near              # same bits at 1, 8, 10 threads and without OpenMP
tools/compare.py A.dump B.dump --msx models/msx/F.msx              # two dumps, species by species
tools/compare.py A.rpt B.rpt                                       # two reports, and their mass balance
```

- **`tools/yardstick.py run`** runs every build on every case once, in solve mode on one thread, with `bench -dump`, the report and the binary output file. The first build is the reference; builds with `@nofma`, `@fmafast`, `@x86` (or `@clang`, `@native`) are platform samples; the build with `@conv` is the converged reference; the others are candidates, each judged on its own against the reference. Dumps of the reference, samples and converged reference are kept in `.build/yardstick/dumps/` and reused while their build is unchanged. Leave out `@x86` except on macOS with Rosetta.
- **`tools/yardstick.py threads`** runs each build at 1, 8 and 10 threads and its `@noomp` twin, in step mode with `-check`, and fails unless all give the same hash.
- **`tools/compare.py`** reads the `.msx` file for each species' tolerances and report precision, and reports per species the tier (A, B or beyond), the largest absolute and relative difference, the 99th percentile, and how many nodes and links are beyond each tier. For reports it compares MSX's own tables and the mass balance. `--no-where` leaves out where the largest difference is, for private models.
- **`tools/converged.patch`** is used only by `@conv`: integrator tolerances times 10⁻³ (`MSX_CONV_SCALE`), Newton to 8 significant digits (`MSX_CONV_NUMSIG`), Euler replaced by RK5. Segment merging still uses each species' own tolerance.

## Newer versions of EPANET-MSX

`tools/check.py` compares the latest `dev` (or any other version) with 85a303d and the patches, and records the outcome in [status.md](status.md):

```sh
tools/check.py              # the dev branch as it is on GitHub now
tools/check.py pull/28      # a pull request
tools/check.py --prs        # also: how far the series applies to each open pull request
```

It fetches the version into the `msx` submodule, applies the series (each patch applies, applies after a three-way merge, is already there, or does not apply, which stops the series; a fix that does not apply and that no later patch requires is skipped instead, as FIX-03 is on `dev`), applies each fix on its own, times 85a303d, the newer version, and both with the bit-identical and near-identical patches, and writes `status.md`. Commit it to keep the check, or discard it with `git checkout status.md`.

## Your own models

Put input and reaction files in `models/private/`, which git ignores, and run `tools/try.py bit near --cases private`. [models/private/README.md](models/private/README.md) explains how to pair the files, how to make reaction files for a network with `tools/private-reactions.py`, and how to report back without sharing the model.

## Everything the README reports

`tools/run-all.sh` builds everything, makes every measurement in [results/](results/README.md) again, and writes the tables into the READMEs with `tools/update-docs.py`. With a checked run and 5 timed runs per build, interleaved, it takes about 6 hours on an Apple M1 Pro; it waits for a quiet moment before each step (up to 30 minutes) and never closes anything. `QUICK=1 tools/run-all.sh` makes a checked run and one timed run per build instead, in about 2.5 hours; that is how the tables in this repository were made. Either way it copies everything it measured into `results/` and rewrites the tables in the READMEs; `git diff` shows what changed, and `git checkout .` undoes it. `tools/run-all.sh --list` lists the steps, and `tools/run-all.sh series near` runs only those.

## Scripts

| Script | What it does |
|---|---|
| [`tools/try.py`](tools/try.py) | Tries any target against 85a303d: speed, identical results or a tolerance verdict, a summary to paste |
| [`tools/build-msx.sh`](tools/build-msx.sh) | Builds MSX and EPANET 2.2 with part or all of the series, on any version, or another way (flavours) |
| [`tools/patch-order.sh`](tools/patch-order.sh) | Lists the patches of a build, in order |
| [`tools/get-msx.sh`](tools/get-msx.sh) | Finds the MSX source and commit (`MSX_SRC`, `MSX_COMMIT`) and the EPANET 2.2 commit it pins |
| [`tools/bench.c`](tools/bench.c) | The driver: one network and reaction file, one mode; timings and result hashes |
| [`tools/bench.py`](tools/bench.py) | Times builds on the cases, interleaved, and compares their results |
| [`tools/compare.py`](tools/compare.py) | Compares two builds' results value by value, species by species |
| [`tools/yardstick.py`](tools/yardstick.py) | Judges near-identical changes against the platform samples and the converged reference; checks thread counts |
| [`tools/converged.patch`](tools/converged.patch) | The converged reference (`@conv`) |
| [`tools/check.py`](tools/check.py) | Compares a newer MSX with 85a303d and the patches; writes `status.md` |
| [`tools/patch-workspace.sh`](tools/patch-workspace.sh) | An editable copy of the source with a patch applied; writes your changes back to the patch |
| [`tools/run-all.sh`](tools/run-all.sh) | Remakes everything in `results/` and updates the READMEs |
| [`tools/update-docs.py`](tools/update-docs.py) | Writes the measured tables into the READMEs from `results/` |
| [`tools/private-reactions.py`](tools/private-reactions.py) | Writes chlorine, bacteria and chloramine reaction files for a network of your own |
| [`tools/private-summary.py`](tools/private-summary.py) | Reduces a run on private models to what can be shared |
| [`tools/privacy-check.sh`](tools/privacy-check.sh) | Fails if a tracked file or commit message names a private model |
