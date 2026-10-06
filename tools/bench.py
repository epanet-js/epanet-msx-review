#!/usr/bin/env python3
"""Time EPANET-MSX builds on the benchmark cases and check that their results agree.

  tools/bench.py                                  base against bit, 1 and 8 threads
  tools/bench.py --builds base,BIT-06,bit,near    several builds; the first is the reference
  tools/bench.py --builds BIT-05,BIT-06           one change: before and after
  tools/bench.py --builds base,dev:base,dev:bit   another MSX version (see tools/build-msx.sh)
  tools/bench.py --cases rich-bact,ky8-disp --threads 1 --reps 5
  tools/bench.py --modes step,solve,read          solve mode also compares the binary output
                                                  file and the report (MD5); read mode also
                                                  times reading every value
  tools/bench.py --cases output --modes solve     the output-heavy cases
  tools/bench.py --cases real --reps 0            the larger networks, one checked run each
  tools/bench.py --cases private                  your own models in models/private/

--cases takes groups (main, output, real, stress, public = all four, private, private:N for
your Nth model only) and case IDs, joined with commas. For each case, mode and thread count, every build is first run once
with -check (a hash of every node and link concentration of every species after every
step), then --reps times without it, builds interleaved; the fastest of all these runs is
kept (reading the values for the hash is not timed). With --reps 0 the checked run is the
only run. Results go to .build/results/<tag>.json and a summary to .build/results/<tag>.md.

Private models are labelled "Private model 1, 2, ..." in file-name order (--private-label
to change it) and described only by their size and settings, rounded; their file names,
IDs and messages are never printed unless --names is given.
"""
import argparse, glob, hashlib, json, math, os, re, statistics, subprocess, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(HERE, "models")
PRIVATE = os.path.join(MODELS, "private")
KINDS = {"chlorine": "chlorine", "bacteria": "bacterial regrowth", "chloramine": "chloramine",
         "arsenic": "arsenic", "dispersion": "dispersion", "age": "water age"}
SOLVERS = {"EUL": "Euler", "RK5": "RK5", "ROS2": "ROS2"}


def build(name):
    out = subprocess.run([os.path.join(HERE, "tools", "build-msx.sh"), name], capture_output=True, text=True)
    if out.returncode:
        sys.stderr.write(out.stderr)
        raise SystemExit(f"build {name} failed")
    return out.stdout.strip().splitlines()[-1]


# ---------------------------------------------------------------- cases

def msx_solver(path):
    sect = None
    for raw in open(path, errors="replace"):
        line = raw.split(";")[0].strip()
        if line.startswith("["):
            sect = line.upper()
        elif sect == "[OPTIONS]" and line.upper().startswith("SOLVER"):
            tok = line.split()
            return SOLVERS.get(tok[1].upper(), tok[1]) if len(tok) > 1 else "?"
    return "Euler"


def private_cases(label="Private model", cases_file=None, names=False):
    """The models in models/private/ (or a cases file), labelled anonymously."""
    out = []
    if cases_file or os.path.exists(os.path.join(PRIVATE, "cases.json")):
        path = cases_file or os.path.join(PRIVATE, "cases.json")
        base = os.path.dirname(os.path.abspath(path))
        listed = json.load(open(path))["cases"]
        pairs = [(os.path.join(base, c["inp"]), os.path.join(base, c["msx"]), dict(c, listed=True)) for c in listed]
    else:
        pairs = []
        for inp in sorted(glob.glob(os.path.join(PRIVATE, "*.inp"))):
            stem = os.path.splitext(os.path.basename(inp))[0]
            msx = sorted(glob.glob(os.path.join(PRIVATE, glob.escape(stem) + "*.msx")))
            if not msx:
                first = re.split(r"[-_. ]", stem)[0]
                msx = sorted(glob.glob(os.path.join(PRIVATE, glob.escape(first) + "[-_]*.msx")))
            for m in msx:
                pairs.append((inp, m, {}))
    # models are numbered in the order of cases.json, or in file-name order without one
    inps = list(dict.fromkeys(p[0] for p in pairs)) if any(p[2] for p in pairs) else sorted({p[0] for p in pairs})
    count = {}
    for inp, msx, opts in pairs:
        i = inps.index(inp) + 1
        count[i] = count.get(i, 0) + 1
        mstem = os.path.splitext(os.path.basename(msx))[0].lower()
        kind = next((v for k, v in KINDS.items() if mstem.endswith(k)), f"reactions {count[i]}")
        solver = msx_solver(msx)
        name = f"{label} {i}, {kind} ({solver})"
        if names:
            name += f" [{os.path.basename(inp)}, {os.path.basename(msx)}]"
        c = {"id": f"private-{i}-{count[i]}", "name": name, "inp": inp, "msx": msx, "reps": 1,
             "group": "private", "private": True, "model": i}
        c.update({k: v for k, v in opts.items() if k in ("reps", "maxreps", "threads", "timeout")})
        out.append(c)
    return out


def load_cases(spec, label="Private model", cases_file=None, names=False):
    allc = json.load(open(os.environ.get("BENCH_CASES", os.path.join(MODELS, "cases.json"))))["cases"]
    for c in allc:
        c["inp"] = os.path.join(MODELS, c["inp"])
        c["msx"] = os.path.join(MODELS, c["msx"])
    out = []
    for s in spec.split(","):
        if s in ("main", "all"):
            out += [c for c in allc if c.get("group", "main") == "main"]
        elif s == "public":
            out += allc
        elif s in ("output", "real", "stress"):
            out += [c for c in allc if c.get("group") == s]
        elif s == "private" or s.startswith("private:"):
            pc = private_cases(label, cases_file, names)
            if not pc:
                raise SystemExit("No models in models/private/ (see models/private/README.md)")
            if ":" in s:
                want = {int(x) for x in s.split(":", 1)[1].split("+")}
                pc = [c for c in pc if c["model"] in want]
            out += pc
        else:
            hit = [c for c in allc if c["id"] == s]
            if not hit:
                raise SystemExit(f"No case {s}")
            out += hit
    seen, uniq = set(), []
    for c in out:
        if c["id"] not in seen:
            seen.add(c["id"]); uniq.append(c)
    return uniq


def sig1(x):
    """round to one significant figure, for describing private models"""
    if x <= 0:
        return 0
    e = 10 ** int(math.floor(math.log10(x)))
    return int(round(x / e) * e)


def describe(bdir, case, exact=False):
    """size and settings of a model from bench -mode info; rounded for private models"""
    p = subprocess.run([os.path.join(bdir, "bench"), case["inp"], case["msx"], "-mode", "info"],
                       capture_output=True, text=True, cwd=os.path.join(HERE, ".build"))
    line = [l for l in p.stdout.splitlines() if l.startswith("INFO")]
    if not line:
        return None
    d = dict(kv.split("=") for kv in line[0].split()[1:])
    d = {k: int(v) for k, v in d.items()}
    if case.get("private") and not exact:
        for k in ("junctions", "pipes", "pumps", "valves", "tanks", "reservoirs", "controls", "rules"):
            d[k] = sig1(d[k])
    d["solver"] = msx_solver(case["msx"])
    return d


def describe_text(d):
    if not d:
        return "-"
    hrs = d["duration_s"] / 3600
    approx = "about " if d.get("approx") else ""
    return (f"{approx}{d['pipes']:,} pipes, {d['junctions']:,} junctions, {d['tanks']} tanks, "
            f"{d['pumps']} pumps; {hrs:g} h, hydraulic step {d['hydstep_s'] // 60} min; "
            f"{d['species_bulk']} bulk and {d['species_wall']} wall species, {d['solver']}")


# ---------------------------------------------------------------- running

def md5(path, report=False):
    if not os.path.exists(path):
        return "-"
    data = open(path, "rb").read()
    if report:
        # EPANET stamps the report header with the date and time of the run
        data = b"\n".join(l for l in data.split(b"\n")
                          if not re.search(rb"(Page \d+ .*\d\d:\d\d:\d\d \d{4})|Analysis (begun|ended)", l))
    return hashlib.md5(data).hexdigest()[:12]


def run(bdir, case, mode, threads, check, workdir, reps=None, timeout=None, extra=()):
    env = dict(os.environ)
    if threads == "default":
        env.pop("OMP_NUM_THREADS", None)
    else:
        env["OMP_NUM_THREADS"] = str(threads)
    rpt = os.path.join(workdir, "rpt.txt")
    out = os.path.join(workdir, "out.bin")
    for f in (rpt, out):
        if os.path.exists(f):
            os.remove(f)
    n = 1 if check else (reps or case.get("reps", 1))
    args = [os.path.join(bdir, "bench"), case["inp"], case["msx"], "-mode", mode, "-reps", str(n)]
    if check:
        args.append("-check")
    if mode == "solve":
        args += ["-rpt", rpt, "-out", out]
    args += list(extra)
    try:
        p = subprocess.run(args, capture_output=True, text=True, env=env, cwd=workdir,
                           timeout=timeout or case.get("timeout"))
    except subprocess.TimeoutExpired:
        return {"rc": -2, "err": "timeout"}
    line = [l for l in p.stdout.splitlines() if l.startswith("RESULT")]
    if not line:
        return {"rc": -1, "err": "" if case.get("private") else p.stderr[-500:]}
    f = line[0].split()
    r = {"rc": int(f[3]), "total": float(f[4]), "open": float(f[5]), "H": float(f[6]), "Q": float(f[7]),
         "report": float(f[8]), "close": float(f[9]), "steps": int(f[10]), "hash": f[11], "rss_kb": int(f[12])}
    if r["rc"] and not case.get("private"):
        r["err"] = p.stderr[-500:]
    if mode == "solve" and check:
        r["out_md5"] = md5(out)
        r["rpt_md5"] = md5(rpt, report=True)
    return r


def loadavg():
    try:
        return [round(x, 2) for x in os.getloadavg()]
    except OSError:
        return None


def machine():
    cpu = "?"
    try:
        if sys.platform == "darwin":
            cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        else:
            for l in open("/proc/cpuinfo"):
                if l.lower().startswith(("model name", "hardware", "cpu model")):
                    cpu = l.split(":", 1)[1].strip()
                    break
    except Exception:
        pass
    ncpu = os.cpu_count()
    osname = {"darwin": "macOS"}.get(sys.platform, sys.platform.capitalize())
    try:
        arch = os.uname().machine
    except Exception:
        arch = "?"
    cc = os.environ.get("CC", "cc")
    try:
        ccv = subprocess.run([cc, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    except Exception:
        ccv = cc
    return f"{cpu} ({osname}, {arch}, {ncpu} cores), {ccv}"


def fmt(t):
    if t is None:
        return "-"
    if t >= 100: return f"{t:,.0f}"
    if t >= 10: return f"{t:.1f}"
    if t >= 1: return f"{t:.2f}"
    if t >= 0.1: return f"{t:.3f}"
    return f"{t * 1000:.1f} ms"


def measure(builds, dirs, cases, modes, threads, reps, metric="total", timeout=None, work=None, progress=print,
            on_record=None):
    """Run every case x mode x thread count; returns the list of records. on_record(results)
    is called after each record, so that a long run can save what it has."""
    work = work or os.path.join(HERE, ".build", "work", os.environ.get("BENCH_WORK", "bench"))
    results = []
    for case in cases:
        for mode in modes:
            for th in threads:
                if case.get("threads") and str(th) not in [str(x) for x in case["threads"]]:
                    continue
                rec = {"case": case["id"], "name": case["name"], "mode": mode, "threads": th, "builds": {},
                       "load_start": loadavg()}
                if case.get("private"):
                    rec["private"] = True
                for b in builds:
                    wd = os.path.join(work, b.replace(":", "-").replace("/", "-"))
                    os.makedirs(wd, exist_ok=True)
                    rec["builds"][b] = {"check": run(dirs[b], case, mode, th, True, wd, timeout=timeout), "times": []}
                for _ in range(reps):
                    for b in builds:
                        wd = os.path.join(work, b.replace(":", "-").replace("/", "-"))
                        rec["builds"][b]["times"].append(run(dirs[b], case, mode, th, False, wd, timeout=timeout))
                rec["load_end"] = loadavg()
                ref = rec["builds"][builds[0]]
                line = [case["id"], mode, f"{th}t"]
                for b in builds:
                    d = rec["builds"][b]
                    # the checked run is timed like the others (reading values for the hash is not timed)
                    pool = d["times"] + [d["check"]]
                    ok = [t for t in pool if t.get("rc") == 0]
                    d["best"] = min(t[metric] for t in ok) if ok else None
                    d["best_Q"] = min(t["Q"] for t in ok) if ok else None
                    d["rss_kb"] = max(t["rss_kb"] for t in ok) if ok else None
                    d["rc"] = d["check"].get("rc")
                    keys = ["hash", "out_md5", "rpt_md5"]
                    d["identical"] = d["check"].get("rc") == 0 and all(
                        d["check"].get(k) == ref["check"].get(k) for k in keys)
                    d["speedup"] = (ref["best"] / d["best"]) if d["best"] and ref["best"] else None
                    sp = f" x{d['speedup']:.2f}" if d["speedup"] else ""
                    line.append(f"{b}={fmt(d['best'])}{sp}{'' if d['identical'] else ' DIFF'}"
                                + (f" rc={d['rc']}" if d["rc"] else ""))
                progress("  ".join(line) + f"  (load {rec['load_start'][0] if rec['load_start'] else '?'})")
                results.append(rec)
                if on_record:
                    on_record(results)
    return results


def summary(results, builds, threads, modes, header=""):
    out = [header] if header else []
    for mode in modes:
        for th in threads:
            rows = [r for r in results if r["mode"] == mode and r["threads"] == th]
            if not rows:
                continue
            out.append(f"### {mode} mode, {th} thread{'s' if th != 1 else ''}\n")
            hdr = "| Case | " + " | ".join(f"{b} (s)" for b in builds) + " | " + \
                  " | ".join(f"{b} speed-up" for b in builds[1:]) + " | Identical |"
            out.append(hdr)
            out.append("| --- |" + " ---: |" * (2 * len(builds) - 1) + " --- |")
            sps = {b: [] for b in builds[1:]}
            for r in rows:
                cells = [fmt(r["builds"][b]["best"]) for b in builds]
                spc = []
                for b in builds[1:]:
                    s = r["builds"][b]["speedup"]
                    if s:
                        sps[b].append(s)
                    spc.append(f"{s:.2f}x" if s else "-")
                bad = [b for b in builds if not r["builds"][b]["identical"]]
                ident = "yes" if not bad else "**no**: " + ", ".join(bad)
                out.append(f"| {r['name']} | " + " | ".join(cells) + " | " + " | ".join(spc) + f" | {ident} |")
            if builds[1:]:
                out.append("| **Median** | " + " | ".join("" for _ in builds) + " | " +
                           " | ".join(f"**{statistics.median(sps[b]):.2f}x**" if sps[b] else "-" for b in builds[1:]) + " | |")
            out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--builds", default="base,bit")
    ap.add_argument("--cases", default="main")
    ap.add_argument("--modes", default="step")
    ap.add_argument("--threads", default="1,8")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--metric", default="total", help="total or Q")
    ap.add_argument("--timeout", type=float, default=None, help="seconds per run")
    ap.add_argument("--names", action="store_true", help="show private models' file names")
    ap.add_argument("--exact", action="store_true", help="describe private models without rounding")
    ap.add_argument("--private-label", default="Private model")
    ap.add_argument("--cases-file", default=None, help="a cases.json for models outside this repository")
    a = ap.parse_args()

    cases = load_cases(a.cases, a.private_label, a.cases_file, a.names)
    builds = a.builds.split(",")
    threads = [t if t == "default" else int(t) for t in a.threads.split(",")]
    modes = a.modes.split(",")
    dirs = {b: build(b) for b in builds}
    tag = a.tag or "_".join(builds).replace(":", "-").replace("@", "-").replace("/", "-")[:80] + time.strftime("-%Y%m%d-%H%M%S")
    resdir = os.path.join(HERE, ".build", "results")
    os.makedirs(resdir, exist_ok=True)
    start = {"load": loadavg(), "time": time.strftime("%Y-%m-%d %H:%M")}
    models = {}
    for c in cases:
        if c.get("private"):
            d = describe(dirs[builds[0]], c, a.exact)
            if d and not a.exact:
                d["approx"] = True
            models[c.get("model")] = d
    partial = os.path.join(resdir, tag + ".partial.json")
    def save_partial(res):
        json.dump({"builds": builds, "threads": threads, "modes": modes, "reps": a.reps, "start": start,
                   "results": res}, open(partial, "w"), indent=1)
    results = measure(builds, dirs, cases, modes, threads, a.reps, a.metric, a.timeout, on_record=save_partial)
    if os.path.exists(partial):
        os.remove(partial)
    end = {"load": loadavg(), "time": time.strftime("%Y-%m-%d %H:%M")}
    data = {"builds": builds, "threads": threads, "modes": modes, "reps": a.reps, "metric": a.metric,
            "machine": machine(), "date": time.strftime("%Y-%m-%d"), "start": start, "end": end,
            "build_info": {b: open(os.path.join(dirs[b], "info.txt")).read() for b in builds},
            "results": results}
    if models:
        data["private_models"] = {str(k): v for k, v in models.items()}
    if any(c.get("private") for c in cases) and not a.names:
        for r in results:
            for b in r["builds"].values():
                b["check"].pop("err", None)
    json.dump(data, open(os.path.join(resdir, tag + ".json"), "w"), indent=1)
    head = (f"{data['machine']}; `-O3 -DNDEBUG`, OpenMP; best of {a.reps} interleaved runs"
            f"{' (one checked run)' if a.reps == 0 else ''}; {start['time']} to {end['time']}, "
            f"load average {start['load'][0] if start['load'] else '?'} at the start and "
            f"{end['load'][0] if end['load'] else '?'} at the end.\n")
    if models:
        head += "\n" + "\n".join(f"- {a.private_label} {k}: {describe_text(v)}" for k, v in sorted(models.items())) + "\n"
    md = summary(results, builds, threads, modes, head)
    open(os.path.join(resdir, tag + ".md"), "w").write(md)
    print()
    print(md)
    print(f"Results: {os.path.join(resdir, tag)}.json/.md")


if __name__ == "__main__":
    main()
