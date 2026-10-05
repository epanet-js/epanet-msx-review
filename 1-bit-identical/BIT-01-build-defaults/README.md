# BIT-01: Build optimised, with OpenMP on macOS, when following the README

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Build |
| **Results** | <!-- results:BIT-01 -->Identical to 85a303d in all 14 runs (9 cases; step and solve mode at 1 and 8 threads, read mode on the output-heavy cases, and built without OpenMP)<!-- /results --> |
| **Files** | `CMakeLists.txt`, `src/solver/CMakeLists.txt` (+24 / -0 lines) |
| **Patch** | [`BIT-01.patch`](BIT-01.patch), applied after FIX-01 and FIX-02 ([the patches form one series](../../benchmarking.md#applying-the-patches)); it changes no C source, so it also applies to 85a303d on its own |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

The README's build instructions ([README.md, lines 19-20](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/README.md#L19-L20)) are:

```sh
cmake -B build .
cmake --build build --config Release --target package
```

Followed on Linux or macOS, they build a slow library, for two reasons.

**No optimisation.** `--config Release` selects a configuration only for multi-configuration generators such as Visual Studio and Xcode. The default generator on Linux and macOS is Unix Makefiles, which, like Ninja, has one configuration, fixed when the project is configured, and ignores `--config`. With no `CMAKE_BUILD_TYPE`, CMake adds no optimisation flags, so MSX and EPANET 2.2 are compiled without optimisation: the compile command for `msxchem.c` has no `-O` option at all. The one exception in the CMake files is `-O3` for Apple's compiler with the Ninja generator ([src/solver/CMakeLists.txt, lines 62-64](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/CMakeLists.txt#L62-L64)), which covers MSX but not EPANET. The CI workflow builds Windows and macOS with Visual Studio and Xcode, which honour `--config`; its Linux job uses Unix Makefiles with the same two commands ([build-and-test.yml, lines 26 and 61-62](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/.github/workflows/build-and-test.yml#L61-L62)), so that build is unoptimised too.

**No OpenMP on macOS.** Apple's compiler ships without OpenMP. Homebrew's `libomp` is "keg-only": Homebrew does not link it into its default include and library paths, so `find_package(OpenMP)` ([src/solver/CMakeLists.txt, line 10](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/CMakeLists.txt#L10)) reports `Could NOT find OpenMP`, `USE_OPENMP` is not defined ([lines 47-52](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/CMakeLists.txt#L47-L52)), and the library runs on one thread whatever thread count is asked for. The CI workflow avoids this with `brew link --force --overwrite libomp` ([build-and-test.yml, lines 53-54](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/.github/workflows/build-and-test.yml#L53-L54)); a user following the README does not.

## What the change does

Two independent parts, each a few lines of CMake:

1. **Release by default** (root `CMakeLists.txt`). If the generator has a single configuration and no build type was given, `CMAKE_BUILD_TYPE` is set to `Release` (`-O3 -DNDEBUG` with GCC and Clang). An explicit `-DCMAKE_BUILD_TYPE=...` is respected, and multi-configuration generators are left alone. It is set in the root file, so EPANET 2.2 and `runepanetmsx` are optimised too.

2. **Homebrew's libomp** (`src/solver/CMakeLists.txt`). On macOS, if OpenMP was not found, CMake runs `brew --prefix libomp`. If `omp.h` is there, it sets `OpenMP_C_FLAGS` (`-Xpreprocessor -fopenmp -I<prefix>/include`), `OpenMP_C_LIB_NAMES` and `OpenMP_omp_LIBRARY`, and calls `find_package(OpenMP COMPONENTS C)` again. Without Homebrew, or without libomp, nothing changes. With them, configuring prints `Found OpenMP_C: -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include (found version "5.0")`, the compile commands carry `-DUSE_OPENMP -Xpreprocessor -fopenmp`, and the library links `libomp.dylib`.

The two parts can be split. The second runs `brew` when the project is configured; a maintainer who would rather not do that can take the first part alone and add the libomp step to the README's instructions instead.

Left as it is: `src/solver/CMakeLists.txt` also links `omp` when `OpenMP_AVAILABLE` is set ([line 92](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/CMakeLists.txt#L92)), a variable that nothing sets.

## Why the results are unchanged

No C source changes. A Release build compiles with `-O3 -DNDEBUG`, the flags every measurement in this repository uses; neither MSX nor EPANET 2.2 contains an `assert`, so `NDEBUG` removes no code. On the benchmark cases, built with Apple clang for arm64, the unoptimised build gives the same concentrations as the `-O3` one. With other compilers, optimisation can change how floating-point operations are contracted, as it can for any Release build.

MSX gives the same concentrations with and without OpenMP and at any thread count: every patch of the series is checked at 1 and 8 threads and built without OpenMP.

## Measured

`tools/build-msx.sh` compiles the sources directly, with Release flags and OpenMP, so applying BIT-01 changes nothing it builds. The table shows instead what the two defaults cost the unpatched code: built without optimisation, against `-O3`; and built without OpenMP at one thread, as macOS users got it, against the OpenMP build at 8 threads. At one thread the unpatched code is a little faster without OpenMP, because of how it reads per-thread state; [BIT-03](../BIT-03-thread-state-without-tls/) removes that cost.

<!-- measured:BIT-01 -->
To measure it yourself:

```sh
tools/bench.py --builds base,base@O0,base@noomp --threads 1
```
<!-- /measured -->

## Tried and not kept

None. Link-time optimisation and `-ffast-math` were not tried; the second changes results.
