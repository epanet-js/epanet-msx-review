# Your own models

Put EPANET input files (`.inp`) and MSX reaction files (`.msx`) in this folder to time them with the patches. The folder is empty in the repository, and its `.gitignore` keeps anything you put here out of git, so your models are never committed.

```sh
cp ~/models/town.inp ~/models/town-chlorine.msx models/private/
tools/try.py bit near --cases private          # 85a303d against the patches, 1 and 8 threads
tools/try.py bit near --cases private --quick  # one run each, for a first look
```

A network `X.inp` is run with every reaction file whose name starts with `X` (`X-chlorine.msx`, `X-chloramine.msx`, ...), or, if there is none, with those whose name starts with the first word of `X` followed by `-` or `_`. To run other pairs, or to set options, add a `cases.json` here (see below).

**No reaction file of your own?** `tools/private-reactions.py models/private/X.inp` writes three, with the reactions of the larger public cases: chlorine bulk and wall decay (Euler), bacterial regrowth (RK5) and monochloramine decomposition (ROS2). The water entering the network gets the same concentrations as in those cases: at its reservoirs, and at junctions with a negative demand, where water enters. The chloramine file also sets pH and alkalinity at those junctions; without them the equilibria have no solution there, which [FIX-01](../../3-bug-fixes/FIX-01-reaction-loop-error-race/) reports as error 514.

`tools/try.py` runs each case in step mode at 1 and 8 threads and in solve mode, checks whether the results are identical to the unpatched build's, and judges them against the tolerance rule where they are not. It prints a summary and writes it to `.build/results/try-<date>-<targets>.md`. Large models take a while unpatched: the two utility models in the [README](../../README.md#larger-networks) took up to about 15 minutes per run on one thread. The unpatched results are kept, and later runs reuse them unless you pass `--retime`.

## Reporting back

The summary is safe to share as it stands. It labels your models `Private model 1`, `Private model 2` and so on, in alphabetical order of file name, with the kind of reactions and the solver ("Private model 1, chloramine (ROS2)"), and contains no IDs, file names, paths or concentrations: only times, whether the results matched, and for near-identical builds how far each species moved. `tools/bench.py --cases private` also describes each model by its size and settings, rounded to one significant figure (for example: about 20,000 pipes; 72 h; hydraulic step 15 min). Pass `--names` if you would rather see your file names, and do not share that output.

Please open an issue with the summary, especially when:

- a bit-identical build (`bit`, or any `BIT-NN`) gives results that differ from 85a303d on your model;
- a model runs slower with the patches;
- a model fails with the patches but not without them. Error 513 or 514 after [FIX-01](../../3-bug-fixes/FIX-01-reaction-loop-error-race/) is not a failure of the patch: the unpatched code was losing that error.

For a result difference, `tools/try.py BIT-05 BIT-10 bit --cases private --quick` narrows it down to a range of patches, and then any single group can be tested the same way.

## Options per model

By default each case runs once per measurement with the files' own settings. To pair files yourself, repeat a short model inside one run (more reliable timings) or limit the thread counts of a long one, add a `cases.json` here:

```json
{
 "cases": [
  {"inp": "town.inp", "msx": "town-chloramine.msx", "reps": 1},
  {"inp": "small-zone.inp", "msx": "zone-chlorine.msx", "reps": 10},
  {"inp": "whole-city.inp", "msx": "city-bacteria.msx", "threads": [8], "timeout": 3600}
 ]
}
```

Paths are relative to this folder. `reps` repeats the whole run inside one process and keeps the fastest; `threads` limits the thread counts; `timeout` stops a run after that many seconds. For models outside the repository, `tools/bench.py --cases private --cases-file PATH` reads the list from elsewhere.

Before you commit anything to a fork of this repository, `tools/privacy-check.sh` checks that no tracked file or commit message contains the name of a file in this folder.
