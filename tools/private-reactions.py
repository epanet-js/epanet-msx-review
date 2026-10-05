#!/usr/bin/env python3
"""Write three MSX reaction files for an EPANET network of your own, so that it can be timed
like the public larger networks.

  tools/private-reactions.py models/private/town.inp
      writes models/private/town-chlorine.msx, town-bacteria.msx and town-chloramine.msx

The reactions are those of the larger public cases (models/msx/nw-*.msx), from the EPANET-MSX
manual: chlorine bulk and wall decay (Euler), bacterial regrowth with chlorine inhibition
(RK5) and monochloramine decomposition (ROS2). The water entering the network gets the same
concentrations as in those cases:

- at every reservoir, as an initial quality ([QUALITY] NODE), which a reservoir keeps;
- at every junction with a negative base demand (water entering there), as a CONCEN source
  ([SOURCES]). For chloramine the source also sets alkalinity, pH (H) and organic carbon, so
  that the equilibria have a solution in the water it brings: a source without pH leaves
  the equilibrium equations with no solution, which MSX reports as error 514 once FIX-01 is
  applied (and which the unpatched code ignores).

--no-junction-sources leaves the junctions out. The files go next to the network unless
--out is given; models/private/ keeps them out of git. They name only the network's own
reservoir and junction IDs, so they stay as private as the network.
"""
import argparse
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = {"chlorine": "nw-chlorine.msx", "bacteria": "nw-bacteria.msx", "chloramine": "nw-chloramine.msx"}
SOURCES = {   # concentrations entering the network, per kind of reaction
    "chlorine": [("CL2", "1.0")],
    "bacteria": [("CL2", "1.2"), ("S", "0.4"), ("Xb", "0.01")],
    "chloramine": [("NH2CL", "3.0E-5"), ("NH3", "5.0E-6"), ("ALK", "0.004"), ("H", "2.818E-8"), ("TOC", "2.0E-4")],
}
RESERVOIR_ONLY = {"chloramine": {"NH2CL", "NH3"}}   # reservoirs keep the global ALK, H and TOC already


def sections(path):
    sect, out = None, {}
    for raw in open(path, errors="replace"):
        line = raw.split(";")[0].strip()
        if not line:
            continue
        if line.startswith("["):
            sect = line.upper()
            continue
        out.setdefault(sect, []).append(line.split())
    return out


def inflow_points(inp):
    s = sections(inp)
    reservoirs = [t[0] for t in s.get("[RESERVOIRS]", []) if t]
    demand = {}
    for t in s.get("[JUNCTIONS]", []):
        if len(t) >= 3:
            try:
                demand[t[0]] = demand.get(t[0], 0.0) + float(t[2])
            except ValueError:
                pass
    if s.get("[DEMANDS]"):
        demand = {}
        for t in s["[DEMANDS]"]:
            if len(t) >= 2:
                try:
                    demand[t[0]] = demand.get(t[0], 0.0) + float(t[1])
                except ValueError:
                    pass
    junctions = [j for j, d in demand.items() if d < 0]
    return reservoirs, junctions


def write(kind, inp, out, reservoirs, junctions):
    text = open(os.path.join(HERE, "models", "msx", TEMPLATES[kind])).read()
    text = re.sub(r"(\[TITLE\]\n)[^\n]*", r"\1" + {"chlorine": "Chlorine bulk and wall decay (MSX manual, Listing 5.2, without dispersion)",
                                                    "bacteria": "Bacterial regrowth with chlorine inhibition (MSX manual, Listing 5.4)",
                                                    "chloramine": "Monochloramine decomposition (MSX manual, Listing 5.5)"}[kind], text)
    text = re.sub(r"\n  NODE [^\n]*", "", text)                     # the template's own sources
    nodes = []
    for sp, v in SOURCES[kind]:
        if kind in RESERVOIR_ONLY and sp not in RESERVOIR_ONLY[kind]:
            continue
        nodes += [f"  NODE  {r}  {sp}  {v}" for r in reservoirs]
    text = text.replace("\n\n[REPORT]", "\n".join([""] + nodes) + "\n\n[REPORT]", 1) if nodes else text
    text = re.sub(r"\n\n\n+", "\n\n", text)
    if junctions:
        src = ["[SOURCES]"] + [f"  CONCEN  {j}  {sp}  {v}" for j in junctions for sp, v in SOURCES[kind]]
        text = text.replace("[QUALITY]", "\n".join(src) + "\n\n[QUALITY]", 1)
    open(out, "w").write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("--out", default=None, help="folder for the .msx files (default: next to the network)")
    ap.add_argument("--no-junction-sources", action="store_true")
    a = ap.parse_args()
    reservoirs, junctions = inflow_points(a.inp)
    if a.no_junction_sources:
        junctions = []
    if not reservoirs and not junctions:
        raise SystemExit("No reservoirs and no junctions with a negative demand: nowhere for water to enter")
    stem = os.path.splitext(os.path.basename(a.inp))[0]
    out = a.out or os.path.dirname(os.path.abspath(a.inp))
    for kind in TEMPLATES:
        path = os.path.join(out, f"{stem}-{kind}.msx")
        write(kind, a.inp, path, reservoirs, junctions)
        print(path)
    print(f"Sources: {len(reservoirs)} reservoirs, {len(junctions)} junctions with a negative demand")


if __name__ == "__main__":
    main()
