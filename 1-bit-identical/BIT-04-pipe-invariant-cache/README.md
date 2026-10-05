# BIT-04: Cache terms that depend only on hydraulics, parameters and constants

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Chemistry (expression interpreter) |
| **Results** | <!-- results:BIT-04 -->Identical to 85a303d in all 14 runs (9 cases; step and solve mode at 1 and 8 threads, read mode on the output-heavy cases, and built without OpenMP)<!-- /results --> |
| **Files** | `mathexpr.c`, `mathexpr.h`, `msxchem.c` (+420 / -36 lines) |
| **Patch** | [`BIT-04.patch`](BIT-04.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-03 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

After [BIT-02](../BIT-02-terms-evaluated-once/), each term is evaluated once per rate evaluation. Some terms, though, never depend on a concentration, only on a pipe's parameters, the constants and the pipe's hydraulic variables (diameter, flow, velocity, Reynolds number and so on):

- in the Net6 and KY8 chlorine model, all five terms, including three `pow` calls (`Re^0.88`, `Sc^0.3333`, `Interm^0.6667`);
- in the Net3 arsenic model, `Kf`, `Ks` and `LPERCF`.

Parts of other expressions are the same: `(4/D)*Kw*Kf/(Kw+Kf)` in the Net6 and KY8 rate, `k11*S1` and `k12*S2` in the chloramine terms. All of these were computed again for every segment, in every rate evaluation, at every step, though for a given pipe they change only when its hydraulics do. The hydraulic variables are copied for each pipe at every step ([msxchem.c:294](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L294-L295)), and nothing keeps what was computed from them.

## What the change does

- **Found when the file is opened.** The pipe terms and formula species whose every variable is a parameter, a constant, a hydraulic variable or another such term are marked invariant. In the other pipe expressions, `mathexpr_split` replaces each largest sub-expression of two or more tokens that depends only on those inputs by a new variable. Only whole sub-expressions are split off; nothing is regrouped.
- **Cached per pipe.** When work on a pipe starts, these values are taken from the pipe's cache entry if its parameters, the constants and its hydraulic variables are bit for bit the same (`memcmp`) as when the values were computed. Otherwise they are computed, and stored with a copy of those inputs.
- **No hooks.** The values are therefore computed again exactly when an input changes: new hydraulics, `MSXsetparameter`, `MSXsetconstant`. Nothing in the hydraulics or toolkit code has to tell the cache.
- **NaN kept inside.** A split-off part keeps a NaN result (`mathexpr_evalPart`), as it would have propagated inside the whole expression; the whole expression still turns a NaN result into 0 at the end.
- **Pipes only.** Tanks are few, and their expressions are evaluated as before. Each pipe's cache entry is written only by the thread working on that pipe. An entry holds one value for each cached term, formula and part, and for each parameter, constant and hydraulic variable.

## Why the results are unchanged

The same operations are done on the same numbers. A cached value is the value the expression would compute, because the cache is keyed on the exact bit patterns of every input it depends on; and a split-off part is a whole sub-expression, whose value the rest of the expression used as it is.

Beyond the benchmark cases, the change was checked with:

- a test program that changes constants and parameters, of pipes and of tanks, part way through a run, and then runs `MSXinit` a second time (on four benchmark models and two variants of the torture model described in [BIT-02](../BIT-02-terms-evaluated-once/#why-the-results-are-unchanged));
- the torture model's pipe formula that depends only on hydraulics;
- a NaN inside a cached part: `SGN(A + LOG(c2))` with a negative `c2`. If the part's NaN were turned into 0, this would give the sign of `A` instead of 0.

## Measured

<!-- measured:BIT-04 -->
Each table compares the series up to BIT-03 ("before") with BIT-04 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 8.90 | 8.99 | 0.99x | 2.42 | 2.36 | 1.03x | yes |
| Net6, chlorine bulk + wall | 3.64 | 1.07 | 3.39x | 1.70 | 0.937 | 1.82x | yes |
| KY8, chlorine + dispersion | 3.98 | 1.60 | 2.49x | 1.13 | 0.670 | 1.69x | yes |
| Richmond, bacterial regrowth | 5.92 | 5.93 | 1.00x | 1.39 | 1.36 | 1.03x | yes |
| Net3, chloramine decay | 4.12 | 4.08 | 1.01x | 1.11 | 1.11 | 1.00x | yes |
| Net3, arsenic adsorption | 1.30 | 0.951 | 1.37x | 0.403 | 0.324 | 1.25x | yes |
| MSX example (4 nodes) | 0.136 | 0.133 | 1.02x | 0.105 | 0.104 | 1.01x | yes |
| **Median** | | | **1.02x** | | | **1.03x** | |

To measure it yourself:

```sh
tools/try.py BIT-04 --against BIT-03
```
<!-- /measured -->

## Tried and not kept

- Multiplying by a cached reciprocal instead of dividing by an invariant divisor: it changes the last bits, and was slower or within noise on Richmond.
