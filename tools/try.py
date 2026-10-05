#!/usr/bin/env python3
"""Try EPANET-MSX builds against the unpatched code, built on this machine: how much faster they
are, and whether their results are identical (or, where they are not, within tolerance).

  tools/try.py                           bit, near and all against 85a303d, main cases
  tools/try.py BIT-07 only:NEAR-02       part of the series; one near-identical change alone
  tools/try.py FIX-02                    a fix on its own
  tools/try.py dev dev:bit dev:near      upstream dev as it is, and with the patches on top
  tools/try.py pull/29:bit --quick       a pull request with the patches
  tools/try.py ~/src/msx                 your own MSX source tree, as it is on disk
  tools/try.py ~/src/msx:bit             ... with the bit-identical patches applied to it
  tools/try.py near+my.patch             the series plus a patch of your own
  tools/try.py near --cases private      your own models (models/private/README.md)

TARGET is [SOURCE:]NAME[@FLAVOUR]. NAME is any build name tools/patch-order.sh knows (base,
FIX-02, BIT-07, bit, NEAR-02, near, only:NEAR-02, all, joined with "+", patch files);
omitted, it is "base". SOURCE is an MSX commit, tag, branch (dev, main), pull/<number>, or a
directory holding an MSX source tree; omitted, it is 85a303d, the commit the patches were
written against. FLAVOUR is a build flavour of tools/build-msx.sh (@noomp, @asan, ...).

The baseline is 85a303d unpatched (or --against), built here with the same compiler and
flags. A target on another source also gets that source's own base: speed is reported
against both, and its results are judged against its own base, so that upstream's own
changes stay apart from the patches'.

Each case runs in step mode at every --threads count and in solve mode at one thread. Each
build first runs once with a check (a hash of every concentration after every step; in
solve mode also the MD5 of the output file and of the report), then --reps times without,
builds interleaved, best kept. --quick: one checked run, which is also the timed run, and
the baseline's last results on this machine are reused if its build and the models have not
changed (marked with a dagger). For the larger cases (real, private) the baseline is always
reused when it can be, unless --retime.

Where results are not identical, tools/yardstick.py judges them species by species against
how much the reference already varies between platforms (built without fused multiply-add,
with it across statements, and for x86-64 on macOS; with clang and -march=native on Linux),
and against a converged run. Needs numpy for that step only.

Writes .build/results/try-<date>-<targets>.json and .md; the Markdown is safe to paste (no
file names or paths, private models labelled). Exit code 0 when every target's results are
what its patches' headers say (Results: identical or near).
"""
import argparse, glob, hashlib, json, os, re, statistics, subprocess, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import bench  # noqa: E402

MEASURED = "85a303dca05859389eced63fabd5ea145c096333"
REPO = "https://github.com/USEPA/EPANETMSX"
DAGGER = "†"


# ---------------------------------------------------------------- targets

class Target:
    """one build to try: display name, build spec, source, and how to build it"""

    def __init__(self, spec):
        self.display = spec
        self.flavour = ""
        if "@" in spec and not os.path.isdir(os.path.expanduser(spec)):
            spec, self.flavour = spec.rsplit("@", 1)
        self.tree = None
        self.source = None
        name = spec
        path = os.path.expanduser(spec)
        if os.path.isdir(path):                                 # a directory, as it is
            self.tree, name = path, "base"
        elif ":" in spec and not spec.startswith("only:"):
            src, rest = spec.split(":", 1)
            if os.path.isdir(os.path.expanduser(src)):
                self.tree, name = os.path.expanduser(src), rest
            else:
                self.source, name = src, rest
        elif re.fullmatch(r"(pull/\d+|[0-9a-f]{7,40}|v[\d.]+.*|dev|main|master)", spec):
            self.source, name = spec, "base"                    # an upstream version as it is
        self.name = name or "base"
        if self.source in (MEASURED[:7], MEASURED):
            self.source = None

    def build_spec(self):
        s = (f"{self.source}:" if self.source else "") + self.name
        return s + (f"@{self.flavour}" if self.flavour else "")

    def base(self):
        """the target's own base, for a target on another source with patches"""
        if (self.source or self.tree) and self.name != "base":
            t = Target.__new__(Target)
            t.__dict__.update(self.__dict__)
            t.name, t.flavour = "base", ""
            t.display = (self.source if self.source else os.path.basename(self.tree.rstrip("/"))) + ":base"
            return t
        return None

    def build(self):
        env = dict(os.environ)
        if self.tree:
            env["MSX_TREE"] = self.tree
        spec = (self.name + (f"@{self.flavour}" if self.flavour else "")) if self.tree else self.build_spec()
        p = subprocess.run([os.path.join(HERE, "tools", "build-msx.sh"), spec], capture_output=True, text=True, env=env)
        if p.returncode == 3 and os.environ.get("PARTIAL") != "1":
            sys.stderr.write(p.stderr)
            raise SystemExit(f"{self.display}: a patch does not apply (PARTIAL=1 builds the patches before it)")
        if p.returncode:
            sys.stderr.write(p.stderr)
            raise SystemExit(f"build of {self.display} failed")
        self.dir = p.stdout.strip().splitlines()[-1]
        return self.dir

    def describe(self):
        info = dict(l.split(" ", 1) for l in open(os.path.join(self.dir, "info.txt")).read().splitlines() if " " in l)
        msx = info.get("msx", "?")
        if msx.startswith("local"):
            src = f"local tree `{os.path.basename(self.tree.rstrip('/'))}` (checksum {msx.split()[-1]})"
        else:
            src = f"[{msx[:7]}]({REPO}/commit/{msx})" + (f" (`{self.source}`)" if self.source else "")
        states = [l.split(" ", 1) for l in open(os.path.join(self.dir, "patches.txt")).read().splitlines() if l]
        counts = {}
        for _, st in states:
            counts[st] = counts.get(st, 0) + 1
        pt = ", ".join(f"{v} {k}" for k, v in counts.items()) if states else "none"
        return src, pt, states


def expected(target):
    """what the patches' headers say about results: identical, near or changes"""
    if target.name == "base" and not target.tree:
        return None
    files = subprocess.run([os.path.join(HERE, "tools", "patch-order.sh"), target.name],
                           capture_output=True, text=True).stdout.split("\n")
    exp = "identical"
    for f in filter(None, files):
        head = open(f).read().split("diff --git ", 1)[0]
        m = re.search(r"^Results:\s*(\w+)", head, re.M)
        r = m.group(1) if m else "changes"
        if r == "changes":
            return "changes"
        if r == "near":
            exp = "near"
    return exp


# ---------------------------------------------------------------- baseline cache

def md5file(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def cache_path(bdir, case, mode, th):
    d = os.path.join(os.path.dirname(bdir), "_cache", os.path.basename(bdir))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{case['id']}-{mode}-{th}.json")


def cache_key(bdir, case):
    return "|".join([open(os.path.join(bdir, "stamp")).read().strip(), md5file(case["inp"]), md5file(case["msx"]),
                     bench.machine()])


def cache_get(bdir, case, mode, th):
    p = cache_path(bdir, case, mode, th)
    if os.path.exists(p):
        c = json.load(open(p))
        if c.get("key") == cache_key(bdir, case):
            return c
    return None


def cache_put(bdir, case, mode, th, rec):
    json.dump({"key": cache_key(bdir, case), "date": time.strftime("%Y-%m-%d"), **rec},
              open(cache_path(bdir, case, mode, th), "w"))


# ---------------------------------------------------------------- measuring

def measure_case(case, mode, th, targets, baseline, reps, use_cache, progress):
    """one case, mode and thread count; every build interleaved, the baseline from the cache if allowed"""
    names = [t.display for t in targets]
    dirs = {t.display: t.dir for t in targets}
    cached = cache_get(baseline.dir, case, mode, th) if use_cache else None
    run_names = [n for n in names if not (cached and n == baseline.display)]
    recs = bench.measure(run_names, dirs, [case], [mode], [th], reps, progress=lambda s: None)
    rec = recs[0] if recs else {"case": case["id"], "name": case["name"], "mode": mode, "threads": th, "builds": {}}
    if cached:
        rec["builds"][baseline.display] = {"check": cached["check"], "best": cached["best"], "cached": cached["date"],
                                           "rc": cached["check"].get("rc")}
    else:
        b = rec["builds"][baseline.display]
        if b.get("best") is not None:
            cache_put(baseline.dir, case, mode, th, {"check": b["check"], "best": b["best"]})
    line = [f"{case['id']} {mode} {th}t"]
    bt = rec["builds"][baseline.display].get("best")
    for n in names:
        d = rec["builds"][n]
        sp = f" x{bt / d['best']:.2f}" if bt and d.get("best") else ""
        line.append(f"{n}={bench.fmt(d.get('best'))}{DAGGER if d.get('cached') else ''}{sp}")
    progress("  ".join(line))
    return rec


def same(a, b):
    keys = ("hash", "out_md5", "rpt_md5")
    return a.get("rc") == 0 and b.get("rc") == 0 and all(a.get(k) == b.get(k) for k in keys)


def stats(xs):
    xs = [x for x in xs if x]
    if not xs:
        return "-"
    if len(xs) == 1:
        return f"{xs[0]:.2f}x"
    return f"{statistics.median(xs):.2f}x ({min(xs):.2f}-{max(xs):.2f}x)"


# ---------------------------------------------------------------- tolerance

def tolerance(target, ref, cases, private_label, progress):
    """tools/yardstick.py on the cases whose results differ; returns {case id: (judgement, why, species rows)}"""
    if sys.platform == "darwin":
        flav = ["nofma", "fmafast"] + (["x86"] if subprocess.run(["arch", "-x86_64", "/usr/bin/true"],
                                                              capture_output=True).returncode == 0 else [])
    else:
        flav = ["nofma", "fmafast", "clang", "native"]
    refspec = ref.build_spec()
    builds = [refspec] + [f"{refspec}@{f}" for f in flav]
    conv = (f"{ref.source}:" if ref.source else "") + "bit@conv"
    if not ref.tree and subprocess.run([os.path.join(HERE, "tools", "build-msx.sh"), conv],
                                       capture_output=True, text=True).returncode == 0:
        builds.append(conv)
    env = dict(os.environ)
    if target.tree:
        progress("  (tolerance check of a local tree: not supported; compare dumps with tools/compare.py)")
        return {}
    builds.append(target.build_spec())
    tag = "try-ys-" + re.sub(r"[^A-Za-z0-9]+", "-", target.display)[:40]
    ids = ",".join(c["id"] for c in cases)
    progress(f"  judging {target.display} on {ids} against {', '.join(builds[1:-1])} ...")
    p = subprocess.run([os.path.join(HERE, "tools", "yardstick.py"), "run", "--builds", ",".join(builds),
                        "--cases", ids, "--tag", tag, "--private-label", private_label],
                       capture_output=True, text=True, env=env)
    path = os.path.join(HERE, ".build", "results", tag + ".json")
    if not os.path.exists(path):
        progress("  tolerance check failed: " + (p.stderr.strip().splitlines() or ["?"])[-1])
        return {}
    res = json.load(open(path))
    out = {}
    cand = builds[-1]
    for cid, rec in res["results"].items():
        r = rec.get(cand, {})
        j = r.get("judgement", ["ERROR", "run failed", None])
        rows = []
        for s in r.get("vs_ref", {}).get("species", []):
            if s["verdict"] == "IDENTICAL":
                continue
            rows.append((s["id"], s["verdict"], s["maxabs"], s["p99"], s["overB"]))
        out[cid] = (j[0], j[1], rows, r.get("vs_ref", {}).get("verdict", "?"))
    return out


# ---------------------------------------------------------------- report

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*", default=["bit", "near", "all"])
    ap.add_argument("--against", default="base", help="the baseline (default: 85a303d unpatched)")
    ap.add_argument("--cases", default="main")
    ap.add_argument("--threads", default="1,8")
    ap.add_argument("--modes", default="step,solve", help="step runs at every thread count, solve at one thread")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="one checked run each; reuse the baseline's last results")
    ap.add_argument("--retime", action="store_true", help="time the baseline again on real and private cases too")
    ap.add_argument("--no-fetch", action="store_true", help="do not fetch upstream refs from GitHub")
    ap.add_argument("--no-tolerance", action="store_true", help="skip the tolerance verdicts")
    ap.add_argument("--names", action="store_true", help="show private models' file names")
    ap.add_argument("--private-label", default="Private model")
    ap.add_argument("--out", default=None, help="also write the Markdown summary to this file")
    a = ap.parse_args()

    say = lambda s: print(s, flush=True)
    baseline = Target(a.against)
    key = lambda x: (x.tree or "", x.build_spec())
    targets, seen = [], {key(baseline): baseline}
    alias = {}                      # a target's own base that is the same build as another target
    for spec in a.targets:
        t = Target(spec)
        for x in (t.base(), t):
            if not x:
                continue
            if key(x) in seen:
                alias[x.display] = seen[key(x)].display
                continue
            seen[key(x)] = x
            targets.append(x)
    if not targets:
        raise SystemExit("Nothing to try")

    # fetch upstream refs once, and build everything before timing anything
    fetched = set()
    for t in [baseline] + targets:
        if t.source and t.source not in fetched and not a.no_fetch:
            fetched.add(t.source)
            if re.fullmatch(r"pull/\d+|dev|main|master", t.source) or subprocess.run(
                    [os.path.join(HERE, "tools", "get-msx.sh"), "--commit"], capture_output=True,
                    env=dict(os.environ, MSX_COMMIT=t.source)).returncode:
                say(f"Fetching {t.source} from GitHub ...")
                subprocess.run([os.path.join(HERE, "tools", "get-msx.sh"), "--fetch"],
                               env=dict(os.environ, MSX_COMMIT=t.source), capture_output=True)
    say(f"Building {', '.join([baseline.display] + [t.display for t in targets])} ...")
    for t in [baseline] + targets:
        t.build()

    cases = bench.load_cases(a.cases, a.private_label, None, a.names)
    threads = [x if x == "default" else int(x) for x in a.threads.split(",")]
    modes = a.modes.split(",")
    reps = 0 if a.quick else a.reps
    allt = [baseline] + targets
    start = {"time": time.strftime("%Y-%m-%d %H:%M"), "load": bench.loadavg()}
    say(f"Measuring on {len(cases)} cases ({'one checked run each' if a.quick else f'best of {reps}'}); "
        f"load average {start['load'][0] if start['load'] else '?'}")
    records = []
    for case in cases:
        big = case.get("group") in ("real", "private")
        use_cache = (a.quick or big) and not a.retime
        for mode in modes:
            for th in (threads if mode != "solve" else [1]):
                if case.get("threads") and str(th) not in [str(x) for x in case["threads"]]:
                    continue
                records.append(measure_case(case, mode, th, allt, baseline, reps, use_cache, say))
    end = {"time": time.strftime("%Y-%m-%d %H:%M"), "load": bench.loadavg()}

    # identity: each target against its own base (another source's base for a target on that source)
    own = {}
    for t in targets:
        b = t.base()
        own[t.display] = alias.get(b.display, b.display) if b else baseline.display
    verdict = {}
    for t in targets:
        exp = expected(t)
        diff = [r for r in records if not same(r["builds"][own[t.display]]["check"], r["builds"][t.display]["check"])]
        failed = [r for r in records if r["builds"][t.display]["check"].get("rc") not in (0, None)]
        verdict[t.display] = {"expected": exp, "identical": not diff, "differing": diff, "failed": failed, "tol": {}}
    # tolerance, on solve-mode results of the cases that differ
    for t in targets:
        v = verdict[t.display]
        if v["identical"] or a.no_tolerance or v["expected"] == "changes":
            continue
        dcases = []
        for r in v["differing"]:
            c = next(c for c in cases if c["id"] == r["case"])
            if c not in dcases:
                dcases.append(c)
        ref = next(x for x in allt if x.display == own[t.display])
        v["tol"] = tolerance(t, ref, dcases, a.private_label, say)

    # summary
    md = []
    md.append(f"## tools/try.py: {' '.join(a.targets)}\n")
    md.append(f"{bench.machine()}; `-O3 -DNDEBUG`, OpenMP; {start['time']} to {end['time']}; load average "
              f"{start['load'][0] if start['load'] else '?'} at the start, {end['load'][0] if end['load'] else '?'} at the end. "
              f"{'One checked run per build' if a.quick else f'Best of {reps} interleaved runs'}; "
              f"{len(cases)} cases ({a.cases}); step mode at {', '.join(map(str, threads))} thread(s), solve mode at 1."
              + (f" {DAGGER} the baseline's earlier result on this machine." if any(
                  r["builds"][baseline.display].get("cached") for r in records) else ""))
    md.append("")
    md.append("| Build | Source | Patches |")
    md.append("| --- | --- | --- |")
    for t in allt:
        src, pt, _ = t.describe()
        md.append(f"| `{t.display}` | {src} | {pt} |")
    md.append("")
    cols = [f"step, {th} thread{'s' if th != 1 else ''}" for th in threads] + (["solve, 1 thread"] if "solve" in modes else [])
    md.append(f"Speed-up over `{baseline.display}`, median over the cases (range):\n")
    md.append("| Target | Results | " + " | ".join(cols) + " |")
    md.append("| --- | --- |" + " ---: |" * len(cols))
    ok_all = True
    for t in targets:
        v = verdict[t.display]
        if v["failed"]:
            res = f"**failed** on {len(v['failed'])} runs"
            ok = False
        elif v["identical"]:
            res = "identical" + (f" to `{own[t.display]}`" if own[t.display] != baseline.display else "")
            ok = v["expected"] in (None, "identical", "near")
        else:
            n = len({r['case'] for r in v["differing"]})
            ncases = f"{n} case{'s' if n != 1 else ''}"
            if v["tol"]:
                js = [x[0] for x in v["tol"].values()]
                res = f"differ on {ncases}: " + ("**within tolerance** (PASS)" if all(j == "PASS" for j in js)
                                                   else "**beyond tolerance** on " + ", ".join(
                                                       k for k, x in v["tol"].items() if x[0] != "PASS"))
                ok = v["expected"] == "near" and all(j == "PASS" for j in js)
            else:
                res = f"differ on {ncases}" + (" (expected)" if v["expected"] in ("near", "changes") else "")
                ok = v["expected"] in ("near", "changes", None)
            if v["expected"] is None:
                res += f" (`{t.display}` is an upstream version: its own changes)"
        if v["expected"] is not None:
            ok_all &= ok
        cells = []
        for th in threads:
            cells.append(stats([r["builds"][baseline.display]["best"] / r["builds"][t.display]["best"]
                                for r in records if r["mode"] == "step" and r["threads"] == th
                                and r["builds"][t.display].get("best") and r["builds"][baseline.display].get("best")]))
        if "solve" in modes:
            cells.append(stats([r["builds"][baseline.display]["best"] / r["builds"][t.display]["best"]
                                for r in records if r["mode"] == "solve"
                                and r["builds"][t.display].get("best") and r["builds"][baseline.display].get("best")]))
        md.append(f"| `{t.display}` | {res} | " + " | ".join(cells) + " |")
    # per case
    for mode in modes:
        for th in (threads if mode != "solve" else [1]):
            rows = [r for r in records if r["mode"] == mode and r["threads"] == th]
            if not rows:
                continue
            md.append(f"\n### {mode} mode, {th} thread{'s' if th != 1 else ''}: seconds (speed-up)\n")
            md.append("| Case | " + " | ".join(f"`{t.display}`" for t in allt) + " |")
            md.append("| --- |" + " ---: |" * len(allt))
            for r in rows:
                bt = r["builds"][baseline.display].get("best")
                cells = []
                for t in allt:
                    d = r["builds"][t.display]
                    s = bench.fmt(d.get("best")) + (DAGGER if d.get("cached") else "")
                    if t is not baseline and bt and d.get("best"):
                        s += f" ({bt / d['best']:.2f}x)"
                    if t is not baseline and not same(r["builds"][own[t.display]]["check"], d["check"]):
                        s += " *differs*"
                    if d["check"].get("rc"):
                        s += f" rc {d['check']['rc']}"
                    cells.append(s)
                md.append(f"| {r['name']} | " + " | ".join(cells) + " |")
    # tolerance details
    for t in targets:
        tol = verdict[t.display]["tol"]
        if not tol:
            continue
        md.append(f"\n### `{t.display}`: how far results move, against `{own[t.display]}`\n")
        md.append("Per case: the judgement of the acceptance rule (2-near-identical/README.md), then per species "
                  "that differs: tier (A below report precision, B within the species' tolerance, FAIL beyond), "
                  "largest difference, 99th percentile, nodes and links beyond tier B.\n")
        names = {c["id"]: c["name"] for c in cases}
        for cid, (j, why, rows, vv) in tol.items():
            md.append(f"- **{names.get(cid, cid)}**: {j}, {why}. " +
                      "; ".join(f"{s} {tier} max {mx:.2g}, p99 {p:.2g}" + (f", {ob} beyond B" if ob else "")
                                for s, tier, mx, p, ob in rows[:6]) + ("; ..." if len(rows) > 6 else ""))
    text = "\n".join(md) + "\n"
    resdir = os.path.join(HERE, ".build", "results")
    os.makedirs(resdir, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", "-".join(a.targets))[:60].strip("-")
    base = os.path.join(resdir, f"try-{time.strftime('%Y%m%d-%H%M')}-{slug}")
    for r in records:
        if r.get("private"):
            for b in r["builds"].values():
                b["check"].pop("err", None)
    json.dump({"targets": [t.display for t in targets], "baseline": baseline.display, "own_base": own,
               "machine": bench.machine(), "start": start, "end": end, "cases": a.cases, "quick": a.quick,
               "verdict": {k: {"expected": v["expected"], "identical": v["identical"],
                               "tolerance": {c: list(x[:2]) for c, x in v["tol"].items()}} for k, v in verdict.items()},
               "results": records}, open(base + ".json", "w"), indent=1)
    open(base + ".md", "w").write(text)
    if a.out:
        open(a.out, "w").write(text)
    print()
    print(text)
    print(f"Written: {base}.md (and .json)")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
