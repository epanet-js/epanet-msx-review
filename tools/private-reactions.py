#!/usr/bin/env python3
"""Write three MSX reaction files for an EPANET network of your own, so that it can be timed
like the public larger networks.

  tools/private-reactions.py models/private/town.inp
      writes models/private/town-chlorine.msx, town-bacteria.msx and town-chloramine.msx
  tools/private-reactions.py models/private/town.inp --kinds chlorine,age
      only those: age is water age in hours (Euler, 300 s), which keeps water parcels from
      merging, so it shows what long runs with many segments cost

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

The published models of the literature cases can be written too:

  tools/private-reactions.py models/private/town.inp --kinds dbp,psm,podds
  tools/private-reactions.py models/inp/nwmodel-12h.inp --kinds literature --name nw --out models/msx

literature is all seven: dbp, regrowth-thm, psm, temperature, inactivation, podds and vcdm,
from models/msx/ltown-<kind>.msx. The L-Town file is the template: its first source water
(NODE R1) goes to the first reservoir and to the junctions with a negative demand, its
second (NODE R2), where it has one, to every second reservoir; LU is set to 0.3048 for a
network in US units; and the report keeps the species but not L-Town's nodes. Three kinds
need the network's hydraulics, which come from EPANET (the base build's library):

- podds and vcdm start each pipe's material conditioned at half of the peak wall shear
  stress the pipe sees in the run (rho*g*(D/4)*headloss/length), at least 0.02 Pa, as the
  L-Town files do;
- inactivation puts its intrusion at the junction with the largest flow through it among
  those at least three pipes from where water enters, from the middle of the intrusion,
  which starts at 06:00 (or a quarter of the way into a shorter run) and lasts 2 hours (or
  a sixth of the run), on the network's pattern time step.
"""
import argparse
import ctypes
import os
import re
import subprocess
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LITERATURE = ["dbp", "regrowth-thm", "psm", "temperature", "inactivation", "podds", "vcdm"]
TEMPLATES = {"chlorine": "nw-chlorine.msx", "bacteria": "nw-bacteria.msx", "chloramine": "nw-chloramine.msx"}
SOURCES = {   # concentrations entering the network, per kind of reaction
    "chlorine": [("CL2", "1.0")],
    "bacteria": [("CL2", "1.2"), ("S", "0.4"), ("Xb", "0.01")],
    "chloramine": [("NH2CL", "3.0E-5"), ("NH3", "5.0E-6"), ("ALK", "0.004"), ("H", "2.818E-8"), ("TOC", "2.0E-4")],
}
AGE = """[TITLE]
Water age

[OPTIONS]
  RATE_UNITS     HR
  SOLVER         EUL
  TIMESTEP       300

[SPECIES]
  BULK  AGE  HR  0.01  0.001     ;water age, hours

[PIPES]
  RATE  AGE  1

[TANKS]
  RATE  AGE  1

[REPORT]
  SPECIES AGE YES
"""
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


class Hydraulics:
    """EPANET's hydraulic solution of a network, through the base build's EPANET library"""

    def __init__(self, inp):
        p = subprocess.run([os.path.join(HERE, "tools", "build-msx.sh"), "base"], capture_output=True, text=True)
        if p.returncode:
            raise SystemExit(p.stderr)
        lib = [os.path.join(p.stdout.split()[-1], n) for n in ("libepanet2.dylib", "libepanet2.so")]
        en = ctypes.CDLL(next(f for f in lib if os.path.exists(f)))
        ph, i, t, d = ctypes.c_void_p(), ctypes.c_int(), ctypes.c_long(), ctypes.c_double()
        tmp = tempfile.mkdtemp()
        en.EN_createproject(ctypes.byref(ph))
        err = en.EN_open(ph, inp.encode(), os.path.join(tmp, "x.rpt").encode(), b"")
        if err > 100:
            raise SystemExit(f"EPANET error {err} reading the network")

        def get(fn, *args):
            fn(ph, *args)
        get(en.EN_getflowunits, ctypes.byref(i))
        self.si = i.value >= 5                                     # LPS and after: SI units
        times = []
        for code in (0, 3, 4):                                     # duration, pattern step and start
            get(en.EN_gettimeparam, code, ctypes.byref(t))
            times.append(t.value)
        self.duration, self.pattern_step, self.pattern_start = times
        get(en.EN_getcount, 0, ctypes.byref(i)); nn = i.value
        get(en.EN_getcount, 2, ctypes.byref(i)); nl = i.value
        buf = ctypes.create_string_buffer(64)
        self.nodes, self.node_type = [], []
        for k in range(1, nn + 1):
            get(en.EN_getnodeid, k, buf); self.nodes.append(buf.value.decode())
            get(en.EN_getnodetype, k, ctypes.byref(i)); self.node_type.append(i.value)
        self.links, self.pipe, self.ends, diam, length = [], [], [], [], []
        a, b = ctypes.c_int(), ctypes.c_int()
        for k in range(1, nl + 1):
            get(en.EN_getlinkid, k, buf); self.links.append(buf.value.decode())
            get(en.EN_getlinktype, k, ctypes.byref(i)); self.pipe.append(i.value <= 1)
            get(en.EN_getlinknodes, k, ctypes.byref(a), ctypes.byref(b)); self.ends.append((a.value - 1, b.value - 1))
            get(en.EN_getlinkvalue, k, 0, ctypes.byref(d)); diam.append(d.value / (1000.0 if self.si else 12.0))
            get(en.EN_getlinkvalue, k, 1, ctypes.byref(d)); length.append(d.value)
        # every hydraulic period: the peak wall shear stress of each pipe, and the flows at each time
        self.peak = [0.0] * nl
        self.flows = []
        lu = 1.0 if self.si else 0.3048
        get(en.EN_openH); get(en.EN_initH, 0)
        while True:
            get(en.EN_runH, ctypes.byref(t))
            now = t.value
            head = []
            for k in range(1, nn + 1):
                get(en.EN_getnodevalue, k, 10, ctypes.byref(d)); head.append(d.value)
            q = []
            for k in range(nl):
                get(en.EN_getlinkvalue, k + 1, 8, ctypes.byref(d)); q.append(d.value)
                if self.pipe[k] and length[k] > 0:
                    n1, n2 = self.ends[k]
                    tau = 9810.0 * diam[k] * lu / 4 * abs(head[n1] - head[n2]) / length[k]
                    self.peak[k] = max(self.peak[k], tau)
            self.flows.append((now, q))
            get(en.EN_nextH, ctypes.byref(t))
            if t.value <= 0:
                break
        get(en.EN_closeH); get(en.EN_close)
        en.EN_deleteproject(ph)

    def intrusion(self, entering):
        """the intrusion's start and length (s), and its junction"""
        start = min(6 * 3600, self.duration // 4)
        span = min(2 * 3600, self.duration // 6)
        mid = start + span // 2
        q = min(self.flows, key=lambda f: abs(f[0] - mid))[1]
        hops, todo = {}, [j for j, n in enumerate(self.nodes) if self.node_type[j] > 0 or n in entering]
        for j in todo:
            hops[j] = 0
        nbr = {}
        for k, (a, b) in enumerate(self.ends):
            nbr.setdefault(a, []).append(b); nbr.setdefault(b, []).append(a)
        while todo:
            nxt = []
            for j in todo:
                for m in nbr.get(j, []):
                    if m not in hops:
                        hops[m] = hops[j] + 1; nxt.append(m)
            todo = nxt
        through = [0.0] * len(self.nodes)
        for k, (a, b) in enumerate(self.ends):
            through[a if q[k] > 0 else b] += abs(q[k])            # flow leaving each node
        cand = [j for j in range(len(self.nodes)) if self.node_type[j] == 0 and hops.get(j, 0) >= 3]
        return start, span, self.nodes[max(cand, key=lambda j: through[j])]


def coefficients(text):
    return {t[1].upper(): float(t[2]) for t in (l.split() for l in text.split("\n"))
            if len(t) >= 3 and t[0].upper() in ("PARAMETER", "CONSTANT")}


def write_literature(kind, inp, out, reservoirs, junctions, hyd):
    text = open(os.path.join(HERE, "models", "msx", f"ltown-{kind}.msx")).read()
    lines, sect, waters, keep = text.split("\n"), None, {}, []
    for line in lines:
        s = line.strip()
        if s.startswith("["):
            sect = s.split(";")[0].strip().upper()
            keep.append(line)
            continue
        t = s.split(";")[0].split()
        if sect == "[TITLE]" and s.startswith(";"):
            continue                                               # the template's header, about L-Town
        elif sect == "[TITLE]" and s:
            line = re.sub(r"^L-Town:?\s*", "", line).strip()
            line = line[:1].upper() + line[1:] + \
                f"\n; Written by tools/private-reactions.py from models/msx/ltown-{kind}.msx for " \
                f"{os.path.basename(inp)}.\n; Sources, equations and assumptions: models/literature.md."
        elif sect in ("[QUALITY]", "[SOURCES]", "[PATTERNS]", "[REPORT]") and s.startswith(";"):
            continue                                               # comments about L-Town
        elif sect == "[QUALITY]" and t and t[0].upper() in ("NODE", "LINK"):
            if t[0].upper() == "NODE":
                waters.setdefault(t[1], []).append((t[2], t[3]))
            continue
        elif sect == "[QUALITY]" and kind in ("podds", "vcdm") and t and t[0].upper() == "GLOBAL" \
                and re.match(r"(CPOT|PHI\d+)$", t[1], re.I):
            continue
        elif sect == "[REPORT]" and t and t[0].upper() in ("NODES", "LINKS"):
            continue
        elif sect == "[SOURCES]" and t and t[0].upper() == "MASS":
            line = re.sub(r"^(\s*MASS\s+)\S+", r"\1@INTRUSION@", line)
        elif sect == "[PATTERNS]" and t:
            continue
        elif sect == "[COEFFICIENTS]" and len(t) >= 3 and t[1].upper() == "LU":
            line = line.replace(t[2], "1.0" if hyd.si else "0.3048", 1)
        keep.append(line)
    sections = []                                                  # [header, lines], in file order
    for line in keep:
        if line.strip().startswith("["):
            sections.append([line.split(";")[0].strip().upper(), [line]])
        else:
            sections[-1][1].append(line)

    def body(name, new=None, before="[QUALITY]"):
        for s in sections:
            if s[0] == name:
                return s[1]
        if new is None:
            return None
        at = next(i for i, s in enumerate(sections) if s[0] == before)
        sections.insert(at, [name, [name, ""]])
        return sections[at][1]

    def add(name, extra, front=False, before="[QUALITY]"):
        b = body(name, new=True, before=before)
        while len(b) > 1 and not b[-1].strip():
            b.pop()
        if front:
            b[1:1] = extra
        else:
            b += extra
        b.append("")

    first, second = waters.get("R1", []), waters.get("R2", waters.get("R1", []))
    q = []
    for n, r in enumerate(reservoirs):
        q += [f"  NODE  {r}  {sp}  {v}" for sp, v in (first if n % 2 == 0 else second)]
    if kind in ("podds", "vcdm"):
        c = coefficients("\n".join(keep))
        cond = {hyd.links[k]: max(0.02, 0.5 * hyd.peak[k]) for k in range(len(hyd.links)) if hyd.pipe[k]}
        if kind == "podds":
            q.append(f"  GLOBAL  CPOT  {max(0.0, c['CMAX'] + c['K'] * 0.02):.5f}")
            q += [f"  LINK  {l}  CPOT  {max(0.0, c['CMAX'] + c['K'] * tc):.5f}" for l, tc in cond.items() if tc > 0.02]
        else:
            bands = sorted((k, v) for k, v in c.items() if re.match(r"S\d+$", k))
            q += [f"  GLOBAL  PHI{k[1:]}  {0 if s < 0.02 else 1}" for k, s in bands]
            q += [f"  LINK  {l}  PHI{k[1:]}  0" for l, tc in cond.items() for k, s in bands if 0.02 <= s < tc]
    add("[QUALITY]", q)
    src = body("[SOURCES]")
    if src and any("@INTRUSION@" in l for l in src):
        start, span, node = hyd.intrusion(set(junctions))
        src[:] = [l.replace("@INTRUSION@", node) for l in src]
        step = hyd.pattern_step or 3600
        mult = ["1" if start <= t * step + hyd.pattern_start < start + span else "0"
                for t in range(hyd.duration // step + 1)]
        add("[PATTERNS]", [f"  PINT  {' '.join(mult[i:i + 24])}" for i in range(0, len(mult), 24)], before="[REPORT]")
    if junctions and first:
        add("[SOURCES]", [f"  CONCEN  {j}  {sp}  {v}" for j in junctions for sp, v in first], front=True)
    text = "\n".join(l for s in sections for l in s[1])
    open(out, "w").write(re.sub(r"\n\n\n+", "\n\n", text).rstrip("\n") + "\n")


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
    ap.add_argument("--kinds", default="chlorine,bacteria,chloramine",
                    help="any of chlorine, bacteria, chloramine, age, " + ", ".join(LITERATURE) + ", or literature for all seven")
    ap.add_argument("--name", default=None, help="file names start with this (default: the network's file name)")
    a = ap.parse_args()
    reservoirs, junctions = inflow_points(a.inp)
    if a.no_junction_sources:
        junctions = []
    if not reservoirs and not junctions:
        raise SystemExit("No reservoirs and no junctions with a negative demand: nowhere for water to enter")
    stem = a.name or os.path.splitext(os.path.basename(a.inp))[0]
    out = a.out or os.path.dirname(os.path.abspath(a.inp))
    kinds = a.kinds.replace("literature", ",".join(LITERATURE)).split(",")
    hyd = Hydraulics(os.path.abspath(a.inp)) if set(kinds) & set(LITERATURE) else None
    for kind in kinds:
        path = os.path.join(out, f"{stem}-{kind}.msx")
        if kind == "age":
            open(path, "w").write(AGE)
        elif kind in TEMPLATES:
            write(kind, a.inp, path, reservoirs, junctions)
        elif kind in LITERATURE:
            write_literature(kind, a.inp, path, reservoirs, junctions, hyd)
        else:
            raise SystemExit(f"Unknown kind {kind}")
        print(path)
    print(f"Sources: {len(reservoirs)} reservoirs, {len(junctions)} junctions with a negative demand")


if __name__ == "__main__":
    main()
