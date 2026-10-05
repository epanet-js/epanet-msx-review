# BIT-02: Evaluate each term and formula once per rate evaluation, from flat expressions

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Chemistry (expression interpreter) |
| **Results** | <!-- results:BIT-02 -->Identical to 85a303d in all 49 runs (the 7 main cases in step mode at 1 and 8 threads; 9 cases in solve mode at 1 and 8 threads; the 2 output-heavy cases in step and read mode at 1 and 8 threads; 9 cases built without OpenMP)<!-- /results --> |
| **Files** | `mathexpr.c`, `mathexpr.h`, `msxchem.c` (+752 / -210 lines) |
| **Patch** | [`BIT-02.patch`](BIT-02.patch), applied after FIX-01, FIX-02 and BIT-01 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | With interpreted chemistry, a cycle of formula species (or of terms that the input check misses) recursed until the stack overflowed; `MSXopen` now returns error 506. Not covered: the same term cycles with the `COMPILER` option ([details](#why-the-results-are-unchanged)) |

## What was slow

In the profiles of the unpatched code, the expression interpreter is two-thirds to three-quarters of the run: `mathexpr_eval` and the variable callback `getPipeVariableValue` together take 64-73 % of all samples on Net3 chloramine and Richmond (one thread). Most of that is the same work done again:

- **Every reference to a term or formula species evaluates it again, recursively.** [`getPipeVariableValue`](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L923) evaluates a `[TERMS]` entry ([line 961](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L961)) or a formula species ([line 947](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L947)) each time an expression mentions it. In the Net6 and KY8 chlorine model, `Kf` appears twice in the rate; each `Kf` evaluates `SH`, which evaluates `SHt` and `SHl`, which evaluates `Interm` twice: six `pow` calls per rate evaluation. In the chloramine model one rate evaluation evaluates about 30 terms where there are 13 (`k5` three times, through `a5`), and ROS2's Jacobian evaluates the rates 16 times per step. In the Richmond model `MUa` and `MUb` appear twice each, and each recomputes `Ia` or `Ib` with `exp`.
- **Every variable goes through a callback** that works out its kind (species, term, parameter, constant or hydraulic variable) by a chain of comparisons, and reads thread-local variables to do so.
- **Each expression is a linked list** of separately allocated tokens, and `mathexpr_eval` declares an 8 KB stack array on every call ([mathexpr.c:535](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/mathexpr.c#L535)). On arm64 macOS a stack frame over 4 KB makes the compiler probe each page with `___chkstk_darwin`: 5-8 % of samples.
- **Every result is checked for NaN by a call** to [`MSXerr_validate`](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxerr.c#L76), in another file: 2-3.5 % of samples.
- **Copies nobody reads.** For every segment of every pipe at every step, `MSXchem_equil` copies the link's nine hydraulic variables again ([msxchem.c:352](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L352)), though they are already in place, and `evalPipeFormulas` copies the whole concentration vector ([line 852](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L852)) even when the model has no formula species. With full coupling the same happens in every derivative evaluation ([line 1092](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxchem.c#L1092)).

## What the change does

Four steps, in this order:

1. **Flat expressions and a small stack.** An expression becomes one block of memory: a header (number of tokens, deepest stack reached) followed by the tokens in postfix order. `mathexpr_create` computes the stack depth and checks that the expression is well formed. Well-formed expressions that need fewer than 64 stack entries are evaluated with a 64-entry local stack, the top kept in a register; anything else goes through the original algorithm, kept as `evalGeneric` and marked `noinline` so that its 8 KB array stays out of the fast path. The functions in `mathexpr.h` keep their signatures.
2. **Inline NaN check.** A static `validate()` in `msxchem.c` returns the value when `x == x`, and calls `MSXerr_validate` only otherwise.
3. **No unused copies.** New internal `pipeEquil()` and `tankEquil()` assume that the pipe or tank is already set up. The formula pass is skipped when the model has no formula species, and the per-segment equilibrium call when it has neither equilibrium nor formula species.
4. **Each term and formula once per rate evaluation.** When the file is opened, the pipe and tank expressions are copied, and each variable in a copy refers to a position in a per-thread array of values: species, terms, parameters, constants and hydraulic variables keep their variable index, and formula species get positions of their own. In tanks, hydraulic variables point at a position that always holds 0, which is what `getTankVariableValue` returned for them. For each set of expressions (pipe rates, pipe equilibria, pipe formulas, and the same for tanks) the terms and formula species it needs are listed in dependency order. Evaluating a set first computes each of them once into its position, then evaluates the expressions, which read positions directly (`mathexpr_evalVector`). Parameters, constants and hydraulic variables are put in place when work on a pipe or tank starts.

Step 4 carries almost all of the gain; each of steps 1 to 3 was worth 10 % or less when it was measured on its own. Step 1 is mostly groundwork: step 4 and the later chemistry groups copy, split, fuse and join expressions, which needs the flat layout. With the `COMPILER` option the expressions are not copied, so that path gets steps 2 and 3 only.

## Why the results are unchanged

Steps 1 and 2 do the same IEEE operations on the same operands in the same order. The final NaN-to-0 step of `mathexpr_eval` is kept ([mathexpr.c:725](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/mathexpr.c#L725)), and `MSXerr_validate` returns its argument whenever it is not NaN. Step 3 skips copies whose values were never read: the work vector is loaded again from the segment before any further use. Step 4 relies on evaluation being deterministic: within one rate evaluation the concentrations do not change, so a term evaluated once has exactly the value that each repeated evaluation had. Each term and formula value still goes through the NaN-to-0 step that its own evaluation went through.

Beyond the benchmark cases, the change was checked with a "torture" model on Net3 in six variants (Euler, RK5 and ROS2, each with full and with no coupling), covering terms that use formula species, formulas that use formulas, tank expressions that use hydraulic variables (0 in tanks), equilibrium species with full coupling, and every math function; and with the compiled-chemistry option (`COMPILER`) on four of the benchmark models.

**One behaviour change, in an error case.** MSX checks `[TERMS]` for cycles when it reads the file (error 410, [msxinp.c:351](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxinp.c#L351)), but not formula species ([line 933](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxinp.c#L933)). Two formulas that refer to each other (`FORMULA B A + C` and `FORMULA C B - A`) made the unpatched code recurse until the stack overflowed, as soon as they were first evaluated. Step 4 lists what each set of expressions needs when the file is opened, and a cycle found there now makes `MSXopen` return error 506 ("could not read MSX input file"; no line names the species). The same walk also stops the term cycles that the input check misses. That check records a reference to another term only when the name is a separate word ([lines 873-877](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxinp.c#L873-L877)), so `T1 T2*2` with `T2 T1*2` gets through where `T1 T2 * 2` does not, and its loop never starts from the last term ([line 1463](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxinp.c#L1463)), so a last term that refers to itself gets through too.

**What this does not cover.** With the `COMPILER` option the expressions are not copied and the walk is not made. Formula species do not recurse there (the generated code computes them in turn), but terms do: a term cycle that the input check misses still recurses in the generated `term()` function ([msxcompiler.c:283](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/msxcompiler.c#L283)) until the stack overflows. That case, and the two gaps in the input check, are listed for a later bug write-up.

## Measured

<!-- measured:BIT-02 -->
Each table compares the series up to BIT-01 ("before") with BIT-02 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 12.6 | 9.09 | 1.38x | 3.27 | 2.54 | 1.29x | yes |
| Net6, chlorine bulk + wall | 11.0 | 3.68 | 3.00x | 3.02 | 1.55 | 1.95x | yes |
| KY8, chlorine + dispersion | 10.6 | 3.88 | 2.73x | 2.18 | 1.09 | 1.99x | yes |
| Richmond, bacterial regrowth | 15.0 | 6.00 | 2.50x | 3.24 | 1.46 | 2.22x | yes |
| Net3, chloramine decay | 11.6 | 4.18 | 2.78x | 3.10 | 1.10 | 2.81x | yes |
| Net3, arsenic adsorption | 2.58 | 1.33 | 1.94x | 0.699 | 0.414 | 1.69x | yes |
| MSX example (4 nodes) | 0.212 | 0.138 | 1.54x | 0.144 | 0.106 | 1.35x | yes |
| **Median** | | | **2.50x** | | | **1.95x** | |

To measure it yourself:

```sh
tools/try.py BIT-02 --against BIT-01
```
<!-- /measured -->

## Tried and not kept

- Letting rate expressions read species straight from the integrator's vector, instead of from the copy in the array of values: no measurable gain.
