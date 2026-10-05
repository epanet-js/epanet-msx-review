# BIT-05: Fewer, cheaper interpreter dispatches

| | |
|---|---|
| **Category** | [Bit-identical](../README.md): every concentration, the binary output file and the report are unchanged |
| **Area** | Chemistry (expression interpreter) |
| **Results** | <!-- results:BIT-05 -->Identical to 85a303d in all 14 runs (9 cases; step and solve mode at 1 and 8 threads, read mode on the output-heavy cases, and built without OpenMP)<!-- /results --> |
| **Files** | `mathexpr.c`, `mathexpr.h`, `msxchem.c` (+909 / -79 lines) |
| **Patch** | [`BIT-05.patch`](BIT-05.patch), applied after FIX-01, FIX-02 and BIT-01 to BIT-04 ([the patches form one series](../../benchmarking.md#applying-the-patches)) |
| **Requires** | none |
| **Also fixes** | none |

## What was slow

After [BIT-02](../BIT-02-terms-evaluated-once/) and [BIT-04](../BIT-04-pipe-invariant-cache/), the expression interpreter is still 45-80 % of the run in profiles taken at that point, and most of its cost is the dispatch: one pass through a `switch` per token ([mathexpr.c:543](https://github.com/USEPA/EPANETMSX/blob/85a303dca05859389eced63fabd5ea145c096333/src/solver/mathexpr.c#L541-L543)).

- A typical expression such as `-Kb*CL2` is three or four dispatches, half of them just pushing a value.
- Each term and each expression is a separate call into the evaluator; BWSN2's rate expression `0` cost a whole call.
- A `switch` inside a loop compiles to one shared indirect branch, which the processor predicts poorly, plus a range check, for every operation.
- Expressions as written often take more operations than needed: `-Kb*CL2 - X` is a negation, a multiplication and a subtraction, and operands in the wrong order can keep an invariant part from being cached or a value from being fused.

## What the change does

Four steps, in this order:

1. **Operands fused into operators.** A number or variable that is the second operand of `+ - * / ^` is merged into the operator (new operator codes 41-45 for a variable, 51-55 for a number): one dispatch instead of two, with no push or pop. This applies to BIT-02's internal copies of the expressions only, after BIT-04's split.
2. **One program per set of expressions.** Each set (its terms and formulas, then its rate or equilibrium expressions) is joined into one program with store instructions: code 60 stores a value with the NaN-to-0 step, code 61 stores it as it is (for BIT-04's split-off parts). BIT-04's per-pipe computation of the invariants is one program too. If a program cannot be built (an expression that is malformed or needs a stack of 64 or more), the expressions are evaluated one at a time as before.
3. **Threaded dispatch.** With GNU C's labels-as-values (GCC and Clang), the code for each operation ends by jumping straight to the next operation's code through a table, so each operation has its own indirect branch, which the processor predicts far better. Programs end with a sentinel token (code 0). If the loop's exit test carries the result value instead, Clang merges all the jumps back into one (7 indirect branches instead of 43), and most of the gain is lost; the sentinel avoids that. Elsewhere (MSVC, or `-DMATHEXPR_NO_LABELS_AS_VALUES`) the same source compiles to the `switch` version.
4. **Exact rewrites.** Before BIT-04 splits off the invariant parts, each pipe term, formula, rate and equilibrium expression is turned into a tree and rewritten with identities that are exact in floating point: swapping the operands of `+` and `*`; `a + (-b)` = `a - b`; `(-a)*b` = `-(a*b)`; `(-a)/b` = `-(a/b)`; `-(-x)` = `x`. A cost model counts the dispatches each form would take after the split and step 1, and a dynamic program picks the cheapest form. It is used only if it is strictly cheaper and its stack depth stays within the evaluator's limit. `-(a+b)` and `-(a-b)` are not rewritten, because that can change the sign of a zero. Tank expressions and compiled chemistry (`COMPILER`) are untouched.

Steps 1 and 3 carry most of the gain. Step 2 mostly removes calls (4-21 % fewer instructions, measured on its own) and is what [BIT-08](../BIT-08-euler-lanes/) builds on. Step 4 saves one to three dispatches per evaluation in the expressions it can improve:

| Model | Expression | Dispatches before | After |
|---|---|---:|---:|
| Richmond | rate of `CL2` (`-Kb*CL2`) | 3 | 2 |
| Richmond | rate of `S`; terms `Ib`, `Ia` | 9 | 8 |
| Net3 arsenic | rate of `A5` | 8 | 7 |
| Net3 arsenic | rate of `A5w` | 15 | 12 |
| Net3 chloramine | rate of `HOCL` | 7 | 6 |
| Net3 chloramine | rate of `NH3` | 6 | 5 |
| Net6, KY8 | rate of `CL2` | 6 | 5 |
| BWSN2 | rate of `CL2` | 9 | 8 |

## Why the results are unchanged

- Step 1: each operation keeps its operand order (`top OP operand`).
- Step 2: each expression is evaluated by exactly the same operations, in the same order, as when it is evaluated on its own, and its value is stored with the NaN-to-0 step exactly where the separate evaluation applied it.
- Step 3: the same operations run on the same operands. The `switch` version was checked separately and gives identical results.
- Step 4: each identity gives the same IEEE result for every input, signed zeros included, and a NaN stays a NaN (this is why the two rules that could flip the sign of a zero are left out). A test program evaluated every expression of the benchmark models in its original and its rewritten form on 20,000 random inputs each: no bit differed.

Beyond the benchmark cases, the change was checked with the torture models of [BIT-02](../BIT-02-terms-evaluated-once/#why-the-results-are-unchanged) (every math function among them), with `MSXsetconstant` and `MSXsetparameter` called part way through a run, and with the `switch` dispatch, built with Clang and `-DMATHEXPR_NO_LABELS_AS_VALUES`. MSVC itself was not tested.

## Measured

<!-- measured:BIT-05 -->
Each table compares the series up to BIT-04 ("before") with BIT-05 added ("after"), so it shows this change alone. Apple M1 Pro (macOS, arm64, 10 cores), Apple clang version 15.0.0 (clang-1500.0.40.1), `-O3 -DNDEBUG`, OpenMP; step mode, best of two runs per build (a checked run and a timed run); load average 10.9 at the start and 9.1 at the end; measured 2026-10-05. Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.

| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BWSN2, two-source chlorine | 8.99 | 6.43 | 1.40x | 2.36 | 2.05 | 1.15x | yes |
| Net6, chlorine bulk + wall | 1.07 | 0.927 | 1.16x | 0.937 | 0.892 | 1.05x | yes |
| KY8, chlorine + dispersion | 1.60 | 1.40 | 1.14x | 0.670 | 0.568 | 1.18x | yes |
| Richmond, bacterial regrowth | 5.93 | 3.02 | 1.96x | 1.36 | 0.816 | 1.66x | yes |
| Net3, chloramine decay | 4.08 | 1.79 | 2.27x | 1.11 | 0.529 | 2.10x | yes |
| Net3, arsenic adsorption | 0.951 | 0.578 | 1.65x | 0.324 | 0.261 | 1.24x | yes |
| MSX example (4 nodes) | 0.133 | 91.8 ms | 1.45x | 0.104 | 85.7 ms | 1.21x | yes |
| **Median** | | | **1.45x** | | | **1.21x** | |

To measure it yourself:

```sh
tools/try.py BIT-05 --against BIT-04
```
<!-- /measured -->

## Tried and not kept

- A register-based interpreter, or instructions for "variable op variable": at most about 15 % fewer dispatches, for a rewrite of the interpreter. Sharing common sub-expressions such as `(CL2-CL2Tb)`, and further combined instructions, would save about two dispatches per rate evaluation on Richmond.
- Not computing rate expressions that are constant (BWSN2's `0`, the chloramine model's `H`, `ALK` and `TOC`): no gain.
- Regrouping sums and products around their invariant parts saves more dispatches, but changes the last bits: it is [NEAR-01](../../2-near-identical/NEAR-01-reassociate-expressions/).
- A faster `exp` of its own: at most about 3 % on Richmond even at twice the speed, and it would not give the C library's bits.
