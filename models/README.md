# Benchmark cases

[All changes](../README.md)

Each case pairs an EPANET network (`inp/`) with an MSX reaction file (`msx/`). `cases.json` lists them with the options `tools/bench.py` passes. `private/` is for your own models: it is empty in the repository, and git ignores anything you put there ([see below](#your-own-models)).

## The cases

The seven main cases pair public networks with the reaction systems of the EPANET-MSX 2.0 user's manual. Between them they cover the three integrators (Euler, RK5, ROS2), bulk and wall species, `EQUIL` and `FORMULA` expressions, `[TERMS]`, dispersion, and networks with and without tanks. The run times are of 85a303d, unpatched, on one thread of an Apple M1 Pro.

| Case | ID | Network | Pipes | Tanks | Reactions (manual listing) | Solver, step | Species | Duration | Unpatched, 1 thread |
|---|---|---|---:|---:|---|---|---|---|---:|
| BWSN2, two-source chlorine | `bwsn2-2src` | BWSN network 2 | 14,822 | 2 | Two-source chlorine decay (5.1) | RK5, 300 s | 2 bulk | 6 h | ~13 s |
| Net6, chlorine bulk + wall | `net6-cl2` | Net6 | 3,829 | 32 | Chlorine bulk and wall decay with Sherwood-number terms (5.2, no dispersion) | Euler, 60 s | 1 bulk | 12 h | ~11 s |
| KY8, chlorine + dispersion | `ky8-disp` | KY8 | 1,614 | 5 | The same, with dispersion (5.2) | Euler, 60 s | 1 bulk | 4 h | ~10 s |
| Richmond, bacterial regrowth | `rich-bact` | Richmond | 949 | 6 | Bacterial regrowth with chlorine inhibition (5.4) | RK5, 300 s | 4 bulk, 2 wall; 2 formulas; 4 terms | 12 h | ~15 s |
| Net3, chloramine decay | `net3-chlm` | Net3 | 117 | 3 | Monochloramine decomposition (5.5) | ROS2, 300 s | 14 bulk; 6 equilibria; 13 terms | 24 h | ~11 s |
| Net3, arsenic adsorption | `net3-as` | Net3 | 117 | 3 | Mass-transfer limited arsenic oxidation and adsorption (5.3) | RK5, 180 s | 4 bulk, 1 wall; 1 equilibrium; 3 terms | 24 h | ~2.5 s |
| MSX example (4 nodes) | `example` | The manual's example network | 5 | 0 | Arsenic oxidation and adsorption (section 3) | RK5, 360 s | 4 bulk, 1 wall | 48 h | ~0.2 s |

The pipe counts include only pipes; MSX also routes water through pumps and valves.

**Output-heavy cases** (`--cases output`) report every node, link and species every 5 minutes, to measure the code that saves and reports results:

| Case | ID | Network | Reactions | Duration |
|---|---|---|---|---|
| BWSN2, 2 species, every node and link every 5 min | `bwsn2-out` | BWSN2, `Report Timestep 0:05` | Two first-order decaying species (Euler) | 6 h |
| Net3 chloramine, 14 species, every node and link every 5 min | `net3-chlm-out` | Net3, `Report Timestep 0:05` | Listing 5.5 with every species reported | 24 h |

**Stress cases** (`--cases stress`) exercise paths the main cases do not:

| Case | ID | Network | Reactions | Duration |
|---|---|---|---|---|
| BWSN2 48 h, water age and two source tracers (Euler) | `bwsn2-age` | BWSN2 | Water age, and the share of water from each reservoir (written for this case) | 48 h |
| Net3, chloramine decay with full coupling (ROS2) | `net3-chlm-full` | Net3 | Listing 5.5 with `COUPLING FULL` | 24 h |

**Larger real-world networks** (`--cases real`), each with three kinds of reactions: chlorine bulk and wall decay (Euler), bacterial regrowth (RK5) and chloramine decomposition (ROS2), with the sources at the networks' reservoirs:

| Case | Network | Pipes | Duration | Unpatched, 1 thread |
|---|---|---:|---|---:|
| L-Town 24 h, chlorine, bacteria, chloramine | L-Town, the BattLeDIM 2020 network (5-minute demand patterns) | 905 | 24 h | about 3-50 s |
| NW Model 12 h, chlorine, bacteria, chloramine | The Northwest System (pumps and rules) | 9,979 | 12 h | about 65-690 s |

## Where the files come from

The networks were downloaded in September 2026 and are byte-identical to their sources apart from the lines listed below (checked in October 2026). The edited copies of BWSN2, KY8 and Richmond were first made for [epanet-performance](https://github.com/epanet-js/epanet-performance), whose [models/README.md](https://github.com/epanet-js/epanet-performance/blob/main/models/README.md) lists those edits; the only further change here is a shorter `Duration`, so that each shortened case takes 10-16 seconds unpatched on one thread.

| File | Network | Origin | Changed here | Licence or terms |
|---|---|---|---|---|
| `Net3.inp` | EPANET example network 3 | [OWA EPANET](https://github.com/OpenWaterAnalytics/EPANET), `example-networks/Net3.inp` | unchanged | MIT, as EPANET |
| `Net3-r5.inp` | As above | As above | `Report Timestep 1:00` → `0:05` | MIT, as EPANET |
| `example.inp` | The EPANET-MSX example | [USEPA/EPANETMSX](https://github.com/USEPA/EPANETMSX), `Examples/example.inp` | unchanged | MIT, as EPANET-MSX |
| `net6-12h.inp` | Net6 | [USEPA/WNTR](https://github.com/USEPA/WNTR), `examples/networks/Net6.inp` | `Duration 96:00` → `12:00` | Revised BSD, as WNTR |
| `ltown-24h.inp` | L-Town, the BattLeDIM 2020 network | Vrachimis et al., [Zenodo 4017659](https://doi.org/10.5281/zenodo.4017659) | `Duration 168:00` → `24:00` | CC BY 4.0: credit the authors and say that the duration was changed |
| `nwmodel-12h.inp` | Northwest System | [OWA epanet-example-networks](https://github.com/OpenWaterAnalytics/epanet-example-networks), `epanet-tests/large/NW_Model.inp` | `Duration 0:00` → `12:00` | Distributed publicly for research; no licence stated |
| `ky8-4h.inp` | KY8, University of Kentucky water distribution research database | [KIOS-Research/EPANET-Benchmarks](https://github.com/KIOS-Research/EPANET-Benchmarks), `collect-epanet-inp/ky8.inp`, as edited for epanet-performance (`ky8-age-24h.inp`) | `Duration 24:00` → `4:00` | As above |
| `richmond-12h.inp` | Richmond, University of Exeter Centre for Water Systems | EPANET-Benchmarks, `Richmond_standard.inp`, as edited for epanet-performance (`richmond-chlorine-72h.inp`) | `Duration 72:00` → `12:00` | As above |
| `bwsn2-6h.inp` | Battle of the Water Sensor Networks, network 2 (Ostfeld et al., 2008) | EPANET-Benchmarks, `BWSN_Network_2.inp`, as edited for epanet-performance (`bwsn2-chemical-48h.inp`) | `Duration 48` → `6:00` | As above |
| `bwsn2-6h-r5.inp` | As above | As above | Also `Report Timestep 0:05` | As above |
| `bwsn2-48h.inp` | As above | As above | unchanged from the epanet-performance copy (48 h) | As above |

`ltown-24h.inp` and `net6-12h.inp` keep their original Windows line endings; `.gitattributes` stops git from changing them.

These files are not covered by this repository's MIT licence; each remains under its publisher's terms. If you publish results for them, cite the original source.

## The reaction files

Each is a system from the EPANET-MSX 2.0 user's manual, with its sources moved to the network's reservoirs and a `[REPORT]` section added. They are derived from the manual's listings and are released with the rest of this repository.

| File | From | Changed |
|---|---|---|
| `example.msx` | `Examples/example.msx` of EPANET-MSX | unchanged |
| `net3-arsenic.msx` | Listing 5.3 | Arsenite and monochloramine at both reservoirs (River, Lake) |
| `net3-chloramine.msx` | Listing 5.5 | The manual gives no sources or initial values apart from pH and alkalinity, so these are added: monochloramine 3e-5 M and ammonia 5e-6 M at both reservoirs, 1e-5 M monochloramine and 2e-4 M TOC everywhere at the start |
| `net3-chloramine-all.msx` | As above | Every node, link and species reported |
| `richmond-bacteria.msx` | Listing 5.4 | The listing's `[SOURCES]` entries are written as initial qualities at reservoir O (MSX applies `CONCEN` sources only at junctions with water entering), and small initial bacterial concentrations are set everywhere so that the logarithmic cell counts are finite |
| `ky8-dispersion.msx` | Listing 5.2 | The source at both reservoirs |
| `net6-chlorine.msx` | Listing 5.2 without the `[DIFFUSIVITY]` section | No dispersion |
| `bwsn2-twosource.msx` | Listing 5.1 | The tracer at RESERVOIR-12523 |
| `bwsn2-output.msx` | Written for the output-heavy case | Two first-order decaying species, every node and link reported |
| `bwsn2-age-tracers.msx` | Written for the water-age stress case | Water age in hours (rate 1) and one tracer per reservoir (rate 0, 1.0 at its reservoir) |
| `net3-chloramine-full.msx` | `net3-chloramine.msx` | `COUPLING FULL` |
| `ltown-*.msx`, `nw-*.msx` | `net6-chlorine.msx`, `richmond-bacteria.msx` and `net3-chloramine.msx` | Sources at each network's reservoirs (L-Town R1, R2; NW Model 7384, 311, RES9000); no nodes or links reported |

## Why the runs are short

The unpatched code is slow on these networks: the full-length runs take 106 s (Richmond, 72 h) and 140 s (KY8 with dispersion, 24 h) with one thread. The shorter runs do the same kinds of work, though not in exactly the same proportions: per step, KY8's full 24-hour run costs about twice as much on average as its first 4 hours. For a full-length run, restore the original `Duration`.

## Your own models

Put EPANET input files and MSX reaction files in [`private/`](private/README.md). `tools/bench.py --cases private` and `tools/try.py --cases private` include every model there, and git ignores them, so they are never committed. `tools/private-reactions.py` writes the three reaction files above for a network of your own. See [private/README.md](private/README.md) for how to run them and report results without sharing the model.
