#!/usr/bin/env python3
"""Write the measured tables into the READMEs from the files in results/.

  tools/update-docs.py              from results/ (what tools/run-all.sh copies there)
  tools/update-docs.py --build      from .build/results/ instead, before copying
  tools/update-docs.py --only 1-bit-identical    only the change pages under that folder

Text between <!-- NAME --> and <!-- /NAME --> is replaced, where NAME is one of:

  in each change's README.md     results:ID (inline), measured:ID, moves:ID (near-identical)
  in README.md and the category pages
                                 summary:ID (inline), machine (inline), headline, permodel,
                                 real, private, scaling, flavours, output
  in 2-near-identical/README.md  near-verdicts, near-platforms, near-converged,
                                 near-acceptance, near-arsenic, near-real, near-threads
  in verification.md             verification
  in results/README.md           machine (inline)

The closing tag has no ID (<!-- /summary -->, <!-- /results -->, <!-- /measured -->,
<!-- /moves -->). A block whose results file is missing is left as it is.
"""
import glob, json, os, re, statistics, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
os.environ["YARDSTICK_FORMAT_ONLY"] = "1"       # the tables need no numpy
RES = os.path.join(HERE, ".build", "results") if "--build" in sys.argv else os.path.join(HERE, "results")

MAIN = ["bwsn2-2src", "net6-cl2", "ky8-disp", "rich-bact", "net3-chlm", "net3-as", "example"]
THREADED = {"BIT-03", "BIT-10", "BIT-11", "BIT-12", "BIT-13", "BIT-15", "BIT-17"}
OUTPUT_GROUPS = {"BIT-14": "BIT-13", "BIT-15": "BIT-14", "BIT-16": "BIT-15"}
NEARS = ["NEAR-01", "NEAR-02", "NEAR-03"]
SAMPLE_TITLES = {"@nofma": "FMA off", "@fmafast": "FMA across statements", "@x86": "x86-64",
                 "@clang": "clang", "@native": "native"}


def load(tag):
    p = os.path.join(RES, tag + ".json")
    return json.load(open(p)) if os.path.exists(p) else None


def fmt(t):
    if t is None: return "-"
    if t >= 100: return f"{t:,.0f}"
    if t >= 10: return f"{t:.1f}"
    if t >= 1: return f"{t:.2f}"
    if t >= 0.1: return f"{t:.3f}"
    return f"{t * 1000:.1f} ms"


def fsp(x):
    return "-" if not x else f"{x:.2f}x"


def sp(a, b):
    return a / b if a and b else None


def best(rec, build, key="total"):
    """the best time of a build in a record; reps 0 means the checked run was the timed run"""
    if not rec: return None
    d = rec["builds"].get(build)
    if not d: return None
    if d.get("check") is None:                      # an anonymous summary (private models)
        return d.get("best") if key == "total" else d.get("best_Q") if key == "Q" else None
    # every run counts, the checked one too: reading values for the hash is not timed
    pool = [t for t in d.get("times", []) + [d["check"]] if t.get("rc") == 0 and key in t]
    return min(t[key] for t in pool) if pool else None


def rows(data, mode=None, threads=None, cases=None):
    if not data: return []
    return [r for r in data["results"] if (mode is None or r["mode"] == mode)
            and (threads is None or r["threads"] == threads) and (cases is None or r["case"] in cases)]


def rec(data, case, mode, threads):
    r = rows(data, mode, threads, [case])
    return r[0] if r else None


def sig(r, b):
    c = r["builds"][b]["check"] if r and b in r["builds"] else {}
    return (c.get("rc"), c.get("hash"), c.get("out_md5"), c.get("rpt_md5"))


def median(xs):
    xs = [x for x in xs if x]
    return statistics.median(xs) if xs else None


def conditions(data, what="step mode"):
    """one sentence: machine, runs, load"""
    if not data: return ""
    reps = data.get("reps", 0)
    runs = "one checked and timed run per build" if reps == 0 else \
        "best of two runs per build (a checked run and a timed run)" if reps == 1 else \
        f"best of {reps + 1} interleaved runs"
    ls, le = (data.get("start") or {}).get("load"), (data.get("end") or {}).get("load")
    load = f"; load average {ls[0]:.1f} at the start and {le[0]:.1f} at the end" if ls and le else ""
    return f"{data.get('machine', '?')}, `-O3 -DNDEBUG`, OpenMP; {what}, {runs}{load}; measured {data.get('date', '?')}."


def noise(data):
    reps = (data or {}).get("reps", 0)
    if reps >= 3:
        return f"Each time is the best of {reps + 1} runs. Differences under about 3 % at one thread and 10 % at eight threads are within run-to-run noise."
    return ("Each time is the faster of two runs on a machine in use, so differences under about 5 % at one thread "
            "and 20 % at eight threads are within run-to-run noise; `tools/run-all.sh` remakes them as the best of 6.")


def replace(text, name, body, closing=None):
    closing = closing or name
    pat = re.compile(r"(<!-- %s -->)(.*?)(<!-- /%s -->)" % (re.escape(name), re.escape(closing)), re.S)
    if not pat.search(text):
        return text
    inline = name.split(":")[0] in ("summary", "results", "machine", "hl")
    if inline:
        return pat.sub(lambda m: m.group(1) + body.strip() + m.group(3), text)
    return pat.sub(lambda m: m.group(1) + "\n" + body.strip("\n") + "\n" + m.group(3), text)


# ---------------------------------------------------------------- per change

def prev_of(pid):
    if pid.startswith("FIX-") or pid == "BIT-01":
        return "base"
    n = int(pid[4:])
    return f"BIT-{n - 1:02d}"


def change_table(data, before, after, cases=None):
    """1 and 8 threads, step mode: before -> after"""
    L = ["| Case | Before, 1 thread (s) | After (s) | Speed-up | Before, 8 threads (s) | After (s) | Speed-up | Identical |",
         "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    s1, s8 = [], []
    for r1 in rows(data, "step", 1, cases):
        r8 = rec(data, r1["case"], "step", 8)
        a1, b1, a8, b8 = best(r1, before), best(r1, after), best(r8, before), best(r8, after)
        x1, x8 = sp(a1, b1), sp(a8, b8)
        if x1: s1.append((x1, r1["name"]))
        if x8: s8.append((x8, r1["name"]))
        ident = sig(r1, before) == sig(r1, after) and (not r8 or sig(r8, before) == sig(r8, after))
        L.append(f"| {r1['name']} | {fmt(a1)} | {fmt(b1)} | {fsp(x1)} | {fmt(a8)} | {fmt(b8)} | {fsp(x8)} | "
                 f"{'yes' if ident else '**no**'} |")
    m1, m8 = median([x for x, _ in s1]), median([x for x, _ in s8])
    L.append(f"| **Median** | | | **{fsp(m1)}** | | | **{fsp(m8)}** | |")
    return "\n".join(L), (m1, max(s1) if s1 else (None, None), m8, max(s8) if s8 else (None, None))


def output_table(data, before, after):
    L = ["| Case | Mode | Threads | Before (s) | After (s) | Speed-up | Report and save, before | After | Identical |",
         "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    out = []
    for r in rows(data):
        a, b = best(r, before), best(r, after)
        ra, rb = best(r, before, "report"), best(r, after, "report")
        x = sp(a, b)
        out.append((x, r))
        rep = (fmt(ra), fmt(rb)) if r["mode"] == "solve" else ("", "")
        L.append(f"| {r['name']} | {r['mode']} | {r['threads']} | {fmt(a)} | {fmt(b)} | {fsp(x)} | {rep[0]} | {rep[1]} | "
                 f"{'yes' if sig(r, before) == sig(r, after) else '**no**'} |")
    return "\n".join(L), out


def phase_table(data, before, after, key, label):
    L = [f"| Case | {label} before (s) | After (s) | Speed-up |", "| --- | ---: | ---: | ---: |"]
    xs = []
    for r in rows(data, "step", 1):
        a, b = best(r, before, key), best(r, after, key)
        x = sp(a, b)
        if x: xs.append((x, r["name"]))
        L.append(f"| {r['name']} | {fmt(a)} | {fmt(b)} | {fsp(x)} |")
    m = median([x for x, _ in xs])
    L.append(f"| **Median** | | | **{fsp(m)}** |")
    return "\n".join(L), m, (max(xs) if xs else (None, None))


def summary_text(pid, stats):
    m1, t1, m8, t8 = stats
    parts = []
    if t1[0] and t1[0] >= 1.05:
        parts.append(f"{fsp(m1)} median, up to {fsp(t1[0])} ({t1[1]})" if m1 and m1 >= 1.03 else f"up to {fsp(t1[0])} ({t1[1]})")
    if pid in THREADED and t8[0] and t8[0] >= 1.10:
        parts.append(f"at 8 threads {fsp(m8)} median, up to {fsp(t8[0])} ({t8[1]})" if m8 and m8 >= 1.05
                     else f"at 8 threads up to {fsp(t8[0])} ({t8[1]})")
    return "; ".join(parts) if parts else "within noise on these cases"


def counted(parts):
    """what a count of runs covers, from the result files it came from"""
    what = []
    if "series" in parts: what.append("the 7 main cases in step mode at 1 and 8 threads")
    if "solve" in parts: what.append("9 cases in solve mode at 1 and 8 threads")
    if "output" in parts: what.append("the 2 output-heavy cases in step and read mode at 1 and 8 threads")
    if "noomp" in parts: what.append("9 cases built without OpenMP")
    return "; ".join(what)


def results_text(pid, build, series, vsolve, vout, vnoomp, near=None):
    """how many runs are identical to 85a303d's"""
    n = same = 0
    parts = set()
    for key, data, b in (("series", series, build), ("series", near, build), ("solve", vsolve, build),
                         ("output", vout, build), ("noomp", vnoomp, build + "@noomp")):
        if not data or b not in data["builds"]:
            continue
        parts.add(key)
        ref = data["builds"][0]
        for r in data["results"]:
            if b not in r["builds"]:
                continue
            n += 1
            # near-series uses bit as its reference; bit's results are 85a303d's (verified in series)
            same += sig(r, b) == sig(r, ref)
    if not n:
        return None
    what = counted(parts)
    if same == n:
        return f"Identical to 85a303d in all {n} runs ({what})"
    return f"Differs from 85a303d in {n - same} of {n} runs ({what})"


def measured_block(pid, body, data, cmd):
    return (body + f"\n\nTo measure it yourself:\n\n```sh\n{cmd}\n```")


def per_change(docs):
    series, near = load("series"), load("near-series")
    og, flav, head = load("output-groups"), load("flavours"), load("headline-step")
    vsolve, vout, vnoomp = load("verify-solve"), load("verify-output"), load("verify-noomp")
    ys, ysr = load("yardstick"), load("yardstick-real")
    summaries, results = {}, {}
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for path in sorted(glob.glob(os.path.join(HERE, "[123]-*", "*-*", "README.md"))):
        if only and only not in path:
            continue
        pid = re.match(r"((?:BIT|NEAR|FIX)-\d+)", os.path.basename(os.path.dirname(path))).group(1)
        text = open(path).read()
        new = text
        if pid.startswith("NEAR-"):
            build = "only:" + pid
            if near and build in near["builds"]:
                tab, stats = change_table(near, "bit", build)
                intro = (f"The bit-identical series (FIX-01, FIX-02, BIT-01 to BIT-17) against the same with {pid} "
                         f"added, so it shows this change alone. {conditions(near)} {noise(near)}")
                new = replace(new, f"measured:{pid}", measured_block(pid, intro + "\n\n" + tab, near,
                                                                     f"tools/try.py only:{pid} --against bit"), "measured")
                summaries[pid] = summary_text("BIT-13", stats)   # threading counts too
            moves = moves_table(build, ys, ysr)
            if moves:
                new = replace(new, f"moves:{pid}", moves, "moves")
            rt = near_results_text(build, near, vsolve, vout, vnoomp, ys)
            if rt:
                results[pid] = rt
                new = replace(new, f"results:{pid}", rt, "results")
        else:
            if series and pid in series["builds"]:
                before = prev_of(pid)
                tab, stats = change_table(series, before, pid)
                bname = "85a303d unpatched" if before == "base" else f"the series up to {before}"
                intro = (f"Each table compares {bname} (\"before\") with {pid} " +
                         ("on its own" if pid.startswith("FIX-") else "added") +
                         f" (\"after\"), so it shows this change alone. {conditions(series)} {noise(series)}")
                body = intro + "\n\n" + tab
                summaries[pid] = summary_text(pid, stats)
                if pid.startswith("FIX-"):
                    summaries[pid] = (f"no change beyond noise ({fsp(stats[0])} median at one thread)"
                                      if stats[0] and stats[0] < 1.03 else summary_text(pid, stats))
                if pid in OUTPUT_GROUPS and og:
                    otab, out = output_table(og, OUTPUT_GROUPS[pid], pid)
                    body += ("\n\n**Output-heavy cases**: every node, link and species reported every 5 minutes. "
                             f"Solve mode runs as `runepanetmsx` does; read mode reads every value with `MSXgetqual` "
                             f"after every step. {conditions(og, 'solve and read mode')}\n\n" + otab)
                    good = sorted([o for o in out if o[0] and o[1]["threads"] == 1], key=lambda o: -o[0])
                    if pid in ("BIT-14", "BIT-15") and good:
                        summaries[pid] = "output-heavy cases, one thread: " + ", ".join(
                            f"{o[1]['name'].split(',')[0]} {o[1]['mode']} mode {fsp(o[0])}" for o in good[:2])
                if pid == "BIT-16":
                    ptab, m, t = phase_table(series, before, pid, "H", "MSXsolveH")
                    body += "\n\n**`MSXsolveH`** (EPANET's hydraulics and the copy of its file), one thread:\n\n" + ptab
                    summaries[pid] = f"MSXsolveH {fsp(m)} median, up to {fsp(t[0])} ({t[1]}); whole run " + \
                                     summary_text(pid, stats).replace("within noise on these cases", "within noise")
                if pid == "BIT-01":
                    body, summaries[pid] = flavours_block(flav, head)
                    cmd = ("tools/bench.py --builds base,base@O0,base@noomp --threads 1    # the first three columns\n"
                           "tools/bench.py --builds base --threads 8                       # OpenMP at 8 threads")
                elif pid in OUTPUT_GROUPS:
                    cmd = f"tools/try.py {pid} --against {before} --cases main,output --modes step,solve,read"
                    if pid == "BIT-16":
                        cmd += "\n# MSXsolveH is the H field of each run in the .json file it writes"
                else:
                    cmd = (f"tools/try.py {pid}" if pid.startswith("FIX-") else f"tools/try.py {pid} --against {before}")
                new = replace(new, f"measured:{pid}", measured_block(pid, body, series, cmd), "measured")
            rt = results_text(pid, pid if pid != "BIT-01" else "BIT-01", series, vsolve, vout, vnoomp)
            if rt:
                results[pid] = rt
                new = replace(new, f"results:{pid}", rt, "results")
        if new != text:
            open(path, "w").write(new)
            docs.append(os.path.relpath(path, HERE))
    return summaries, results


def flavours_block(flav, head):
    """BIT-01: what the build defaults cost"""
    if not flav:
        return "", "build options; see build flavours"
    L = ["| Case | `-O0` (plain `cmake`) (s) | `-O3` (s) | Speed-up | No OpenMP, 1 thread (s) | OpenMP, 8 threads (s) | Speed-up |",
         "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    o, t = [], []
    for r in rows(flav, "step", 1):
        a, b, c = best(r, "base@O0"), best(r, "base"), best(r, "base@noomp")
        h8 = best(rec(head, r["case"], "step", 8), "base") if head else None
        x, y = sp(a, b), sp(c, h8)
        o.append(x); t.append(y)
        L.append(f"| {r['name']} | {fmt(a)} | {fmt(b)} | {fsp(x)} | {fmt(c)} | {fmt(h8)} | {fsp(y)} |")
    L.append(f"| **Median** | | | **{fsp(median(o))}** | | | **{fsp(median(t))}** |")
    body = ("85a303d unpatched, built three ways: with no optimisation, as the README's `cmake -B build .` builds "
            "it with the Makefile or Ninja generator; with `-O3`, as a Release build; and without OpenMP, as on macOS "
            f"when CMake does not find Homebrew's libomp, against the OpenMP build at 8 threads. {conditions(flav)}\n\n"
            + "\n".join(L))
    return body, f"no optimisation to `-O3`: {fsp(median(o))} median; no OpenMP to 8 threads: {fsp(median(t))} median"


# ---------------------------------------------------------------- near-identical

def judged(ys, build):
    """per case: (judgement, why, clause, vs_ref) for a candidate"""
    out = {}
    if not ys: return out
    for cid, rr in ys["results"].items():
        c = rr.get(build)
        if c and "judgement" in c:
            out[cid] = (c["judgement"][0], c["judgement"][1], c["judgement"][2] if len(c["judgement"]) > 2 else None,
                        c.get("vs_ref", {}), c.get("report", {}))
    return out


def worst(cmp):
    sps = [s for s in cmp.get("species", []) if s["verdict"] != "IDENTICAL"]
    return max(sps, key=lambda s: s["ratioB"]) if sps else None


def moves_table(build, ys, ysr):
    L = ["| Case | Verdict | Species that moved most | Largest difference | 99th percentile | Nodes and links beyond tier B | Judgement |",
         "| --- | --- | --- | ---: | ---: | ---: | --- |"]
    any_ = False
    for data in (ys, ysr):
        if not data: continue
        names = {c["id"]: c["name"] for c in data["meta"]["cases"]}
        for cid, (j, why, cl, v, rp) in judged(data, build).items():
            any_ = True
            w = worst(v)
            if not w:
                L.append(f"| {names[cid]} | {v.get('verdict', '?')} | - | - | - | - | {j} |")
                continue
            L.append(f"| {names[cid]} | {v['verdict']} | {w['id']} ({w['units']}) | {w['maxabs']:.2g} | {w['p99']:.2g} | "
                     f"{w['overB']} | {j}: {why} |")
    if not any_:
        return None
    return ("Against 85a303d unpatched, solve mode, one thread, every concentration after every step (every sixth "
            "step on the larger networks). Tier A is below the species' report precision, tier B within its own "
            "tolerance; [the near-identical page](../README.md#how-within-tolerance-was-decided) has the rule.\n\n"
            + "\n".join(L))


def near_results_text(build, near, vsolve, vout, vnoomp, ys):
    n = d = 0
    parts = set()
    for key, data, b in (("series", near, build), ("solve", vsolve, build), ("output", vout, build),
                         ("noomp", vnoomp, build + "@noomp")):
        if not data or b not in data["builds"]:
            continue
        parts.add(key)
        ref = data["builds"][0]
        for r in data["results"]:
            if b in r["builds"]:
                n += 1
                d += sig(r, b) != sig(r, ref)
    if not n:
        return None
    j = judged(ys, build)
    passes = sum(1 for x in j.values() if x[0] == "PASS")
    tail = f"; every case passes the acceptance rule" if j and passes == len(j) else \
        (f"; {passes} of {len(j)} cases pass the acceptance rule" if j else "")
    return (f"Differs from 85a303d in {d} of {n} runs ({counted(parts)}), by rounding{tail} "
            f"(see [the acceptance check](../README.md#the-acceptance-table))")


def sample_title(b):
    return SAMPLE_TITLES.get(b[b.index("@"):], b) if "@" in b else b


def near_page(text, near):
    ys, ysr, th = load("yardstick"), load("yardstick-real"), load("threads")
    if ys:
        import yardstick as Y
        m = ys["meta"]
        names = {c["id"]: c["name"] for c in m["cases"]}
        samples, conv, ref = m["samples"], m["conv"], m["ref"]
        L = ["| Case | " + " | ".join(sample_title(s) for s in samples) + " | Report and mass balance |",
             "|" + " --- |" * (len(samples) + 2)]
        for cid, rr in ys["results"].items():
            L.append(f"| {names[cid]} | " + " | ".join(Y.cell(rr.get(s, {}).get("vs_ref")) for s in samples) + " | " +
                     "; ".join(f"{sample_title(s)}: {Y.rcell(rr.get(s, {}).get('report'))}" for s in samples) + " |")
        text = replace(text, "near-platforms", "\n".join(L))
        cols = [ref] + samples + m["candidates"]
        L = ["| Case | " + " | ".join(f"`{b}`" for b in cols) + " |", "|" + " --- |" * (len(cols) + 1)]
        for cid, rr in ys["results"].items():
            L.append(f"| {names[cid]} | " + " | ".join(Y.cell(rr.get(b, {}).get("vs_conv")) for b in cols) + " |")
        text = replace(text, "near-converged", f"Every build against `{conv}`.\n\n" + "\n".join(L))
        A = [f"Reference `{ref}` (85a303d unpatched); platform samples " + ", ".join(f"`{s}`" for s in samples) +
             f"; converged reference `{conv}`. Each `only:NEAR-NN` is the bit-identical series plus that change alone; "
             f"`near` is all three. {m['machine']}, {m['date']}.", ""]
        counts = {}
        for c in m["candidates"]:
            A += [f"#### `{c}`", "", "| Case | Verdict | Largest differences | Report | Judgement | Why |",
                  "| --- | --- | --- | --- | --- | --- |"]
            for cid, rr in ys["results"].items():
                x = rr.get(c, {})
                if "judgement" not in x: continue
                j = x["judgement"]
                counts[j[0]] = counts.get(j[0], 0) + 1
                v = x.get("vs_ref", {})
                sps = sorted([s for s in v.get("species", []) if s["verdict"] != "IDENTICAL"], key=lambda s: -s["ratioB"])
                ld = ", ".join(f"{s['id']} {s['maxabs']:.2g} (p99 {s['p99']:.2g}" + (f", {s['overB']} beyond B)" if s['overB'] else ")")
                               for s in sps[:3]) + (f", {len(sps) - 3} more species" if len(sps) > 3 else "") or "identical"
                A.append(f"| {names[cid]} | {v.get('verdict', '?')} | {ld} | {Y.rcell(x.get('report'))} | {j[0]} | {j[1]} |")
            A.append("")
        A.append("Totals: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        text = replace(text, "near-acceptance", "\n".join(A))
        rr = ys["results"].get("net3-as", {})
        if "only:NEAR-01" in rr and "judgement" in rr["only:NEAR-01"]:
            cl = rr["only:NEAR-01"]["judgement"][2] if len(rr["only:NEAR-01"]["judgement"]) > 2 else 2
            D = Y.detail(rr, ref, samples, conv, "only:NEAR-01", cl)
            text = replace(text, "near-arsenic", "\n".join(D))
        # per change
        V = ["| Change | Cases whose results move | Species that moved most (case) | Acceptance rule | Larger networks | Same bits at 1, 8, 10 threads and without OpenMP | Speed-up, 1 thread | 8 threads |",
             "| --- | ---: | --- | --- | --- | --- | ---: | ---: |"]
        for c in m["candidates"]:
            jj = judged(ys, c)
            moved = [cid for cid, x in jj.items() if x[3].get("verdict") != "IDENTICAL"]
            ws = [(worst(x[3]), cid) for cid, x in jj.items() if worst(x[3])]
            top = max(ws, key=lambda w: w[0]["ratioB"]) if ws else None
            tops = (f"{top[0]['id']} ({names[top[1]]}): {top[0]['verdict']}, max {top[0]['maxabs']:.2g}, "
                    f"p99 {top[0]['p99']:.2g}") if top else "-"
            passes = sum(1 for x in jj.values() if x[0] == "PASS")
            jr = judged(ysr, c) if ysr else {}
            real = (f"{sum(1 for x in jr.values() if x[0] == 'PASS')} of {len(jr)} pass") if jr else "not run"
            thr = "-"
            if th:
                rs = [r for r in th["rows"] if r["build"] == c]
                thr = (f"yes, {len(rs)} cases" if all(r["same"] for r in rs) else
                       f"**no** on {sum(1 for r in rs if not r['same'])} cases") if rs else "-"
            m1 = m8 = None
            if near and c in near["builds"]:
                m1 = median([sp(best(r, "bit"), best(r, c)) for r in rows(near, "step", 1)])
                m8 = median([sp(best(r, "bit"), best(r, c)) for r in rows(near, "step", 8)])
            V.append(f"| `{c}` | {len(moved)} of {len(jj)} | {tops} | {passes} of {len(jj)} pass | {real} | {thr} | "
                     f"{fsp(m1)} | {fsp(m8)} |")
        text = replace(text, "near-verdicts", "\n".join(V) + "\n\nSpeed-ups are median over the 7 main cases, "
                       "against the bit-identical series.")
    if ysr:
        import yardstick as Y
        m = ysr["meta"]
        names = {c["id"]: c["name"] for c in m["cases"]}
        L = [f"Reference `{m['ref']}`; platform samples " + ", ".join(f"`{s}`" for s in m["samples"]) +
             f"; converged reference `{m['conv']}`; every {m.get('dumpevery', 1)}th step compared. {m['date']}.", "",
             "| Case | " + " | ".join(sample_title(s) for s in m["samples"]) + " | " +
             " | ".join(f"`{c}`" for c in m["candidates"]) + " |",
             "|" + " --- |" * (len(m["samples"]) + len(m["candidates"]) + 1)]
        for cid, rr in ysr["results"].items():
            cells = [Y.cell(rr.get(s, {}).get("vs_ref")) for s in m["samples"]]
            for c in m["candidates"]:
                x = rr.get(c, {})
                cells.append((x.get("judgement") or ["-"])[0] + ": " + Y.cell(x.get("vs_ref")))
            L.append(f"| {names[cid]} | " + " | ".join(cells) + " |")
        text = replace(text, "near-real", "\n".join(L))
    if th:
        rs = th["rows"]
        builds = th["builds"]
        L = ["| Build | Cases | Same bits at " + ", ".join(th["threads"]) + " threads and without OpenMP |",
             "| --- | ---: | --- |"]
        for b in builds:
            r = [x for x in rs if x["build"] == b]
            L.append(f"| `{b}` | {len(r)} | " + ("yes, every case" if all(x["same"] for x in r) else
                                                  "**no**: " + ", ".join(x["name"] for x in r if not x["same"])) + " |")
        text = replace(text, "near-threads", "\n".join(L))
    return text


# ---------------------------------------------------------------- README index

def headline(text):
    hs, hv = load("headline-step"), load("headline-solve")
    if not hs:
        return text
    L = ["| How MSX is run | Median, bit-identical | Median, plus near-identical | Range, bit-identical | Range, plus near-identical |",
         "| --- | ---: | ---: | ---: | ---: |"]
    for data, mode in ((hs, "step"), (hv, "solve")):
        if not data: continue
        for th in data["threads"]:
            rr = rows(data, mode, th)
            xb = [sp(best(r, "base"), best(r, "bit")) for r in rr]
            xn = [sp(best(r, "base"), best(r, "near")) for r in rr]
            lab = {1: "1 thread", "default": "all cores (default)"}.get(th, f"{th} threads")
            mlab = "Step (`MSXstep` loop)" if mode == "step" else "Solve (as `runepanetmsx`)"
            L.append(f"| {mlab}, {lab} | {fsp(median(xb))} | {fsp(median(xn))} | "
                     f"{fsp(min(x for x in xb if x))}-{fsp(max(x for x in xb if x))} | "
                     f"{fsp(min(x for x in xn if x))}-{fsp(max(x for x in xn if x))} |")
    text = replace(text, "headline", "\n".join(L))
    P = ["| Case | Unpatched, 1 thread (s) | Bit-identical | Speed-up | Plus near-identical | Speed-up | "
         "Unpatched, 8 threads | Plus near-identical | Speed-up | Plus near-identical, 8 threads, against unpatched, 1 thread |",
         "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    c1, c2, c3, c4 = [], [], [], []
    for r in rows(hs, "step", 1):
        r8 = rec(hs, r["case"], "step", 8)
        b1, i1, n1 = best(r, "base"), best(r, "bit"), best(r, "near")
        b8, n8 = best(r8, "base"), best(r8, "near")
        x = (sp(b1, i1), sp(b1, n1), sp(b8, n8), sp(b1, n8))
        c1.append(x[0]); c2.append(x[1]); c3.append(x[2]); c4.append(x[3])
        P.append(f"| {r['name']} | {fmt(b1)} | {fmt(i1)} | {fsp(x[0])} | {fmt(n1)} | {fsp(x[1])} | {fmt(b8)} | "
                 f"{fmt(n8)} | {fsp(x[2])} | {fsp(x[3])} |")
    P.append(f"| **Median** | | | **{fsp(median(c1))}** | | **{fsp(median(c2))}** | | | **{fsp(median(c3))}** | **{fsp(median(c4))}** |")
    text = replace(text, "permodel", "\n".join(P))
    # numbers quoted in the README's prose
    r1 = {r["case"]: r for r in rows(hs, "step", 1)}
    r8 = {r["case"]: r for r in rows(hs, "step", 8)}
    def ratio(a, ab, b, bb):
        return [sp(best(r1[c] if a == 1 else r8[c], ab), best(r1[c] if b == 1 else r8[c], bb)) for c in r1 if c in r8]
    def rng(xs):
        xs = [x for x in xs if x]
        return f"{min(xs):.1f}-{max(xs):.0f}x" if xs else "-"
    def x1(v):
        return f"{v:.1f}x" if v else "-"
    vals = {"hl:bit1": x1(median(ratio(1, "base", 1, "bit"))), "hl:bit8": x1(median(ratio(8, "base", 8, "bit"))),
            "hl:near1": x1(median(ratio(1, "base", 1, "near"))), "hl:near8": x1(median(ratio(8, "base", 8, "near"))),
            "hl:cross": x1(median(ratio(1, "base", 8, "near"))), "hl:crossrange": rng(ratio(1, "base", 8, "near")),
            "hl:crossbit": x1(median(ratio(1, "base", 8, "bit")))}
    one = sorted([(sp(best(r, "base"), best(r, "bit")), r["name"]) for r in r1.values()], key=lambda x: x[0] or 0)
    if len(one) >= 4:
        vals["hl:extremes"] = (f"At one thread the bit-identical gain is smallest on {one[0][1]} ({fsp(one[0][0])}) and "
                               f"{one[1][1]} ({fsp(one[1][0])}), and largest on {one[-1][1]} ({fsp(one[-1][0])}) and "
                               f"{one[-2][1]} ({fsp(one[-2][0])}).")
    shares = []
    for r in r1.values():
        d = r["builds"]["bit"]
        t = min([x for x in d["times"] + [d["check"]] if x.get("rc") == 0], key=lambda x: x["total"])
        shares.append((t["H"] / t["total"], r["name"]))
    if shares:
        lo, hi = min(shares), max(shares)
        vals["hl:solveh"] = f"{100 * lo[0]:.1f}-{100 * hi[0]:.0f} % of a run with the bit-identical changes, one thread ({hi[1]}: {100 * hi[0]:.0f} %)"
    for k, v in vals.items():
        text = replace(text, k, v)
    return text


def simple_three(data, cases_label="Case", private=False):
    """base, bit, near at 1 and 8 threads, one row per case"""
    L = [f"| {cases_label} | Unpatched, 1 thread (s) | Bit-identical | Plus near-identical | Speed-up | "
         "Unpatched, 8 threads | Plus near-identical | Speed-up | Bit-identical results |",
         "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for r in rows(data, "step", 1):
        r8 = rec(data, r["case"], "step", 8)
        b1, i1, n1 = best(r, "base"), best(r, "bit"), best(r, "near")
        b8, n8 = best(r8, "base"), best(r8, "near")
        if private:
            ident = r["builds"]["bit"].get("identical") and (not r8 or r8["builds"]["bit"].get("identical"))
            rc = [r["builds"][b].get("rc") for b in ("base", "bit", "near")]
        else:
            ident = sig(r, "bit") == sig(r, "base") and (not r8 or sig(r8, "bit") == sig(r8, "base"))
            rc = [r["builds"][b]["check"].get("rc") for b in ("base", "bit", "near")]
        f = (lambda t: fmt(round(t, 1) if t and t >= 1 else t))
        note = "" if not any(rc) else f" (return codes {'/'.join(str(x) for x in rc)})"
        L.append(f"| {r['name']} | {f(b1)} | {f(i1)} | {f(n1)} | {fsp(sp(b1, n1))} | {f(b8)} | {f(n8)} | {fsp(sp(b8, n8))} | "
                 f"{'identical' if ident else '**differ**'}{note} |")
    return "\n".join(L)


def index(text):
    real, priv = load("real"), load("private")
    if real:
        text = replace(text, "real", simple_three(real) + f"\n\n{conditions(real)}")
    if priv:
        text = replace(text, "private", simple_three(priv, private=True) + f"\n\n{conditions(priv)}")
    sc = load("scaling")
    if sc:
        ths = sc["threads"]
        L = ["| Case | Build | " + " | ".join(f"{t} thr" for t in ths) + " |", "| --- | --- |" + " ---: |" * len(ths)]
        names = {"base": "unpatched", "bit": "bit-identical", "near": "plus near-identical"}
        for r1 in rows(sc, "step", 1):
            for b in sc["builds"]:
                L.append(f"| {r1['name']} | {names.get(b, b)} | " +
                         " | ".join(fmt(best(rec(sc, r1['case'], 'step', t), b)) for t in ths) + " |")
        text = replace(text, "scaling", "\n".join(L) + f"\n\n{conditions(sc)}")
        if 1 in ths and 8 in ths:
            sx = []
            for r1 in rows(sc, "step", 1):
                r8 = rec(sc, r1["case"], "step", 8)
                sx.append((sp(best(r1, "bit"), best(r8, "bit")), sp(best(r1, "base"), best(r8, "base")), r1["name"]))
            sx = sorted([x for x in sx if x[0]], key=lambda x: -x[0])
            if len(sx) >= 4:
                t1, t2, b1, b2 = sx[0], sx[1], sx[-2], sx[-1]
                text = replace(text, "hl:scaling",
                               f"From one to eight threads the bit-identical build speeds up {t1[0]:.1f}x on {t1[2]} and "
                               f"{t2[0]:.1f}x on {t2[2]}, against {t1[1]:.1f}x and {t2[1]:.1f}x for the unpatched code. "
                               f"Where the chemistry is now cheap it scales less, because the serial parts (moving water "
                               f"through the nodes, tanks, hydraulics) are a larger share: {b1[0]:.1f}x on {b1[2]} and "
                               f"{b2[0]:.1f}x on {b2[2]}.")
    fl = load("flavours")
    if fl:
        cols = [("base@O0", "`-O0` (plain `cmake`)"), ("base", "`-O3`, OpenMP (unpatched)"), ("base@noomp", "`-O3`, no OpenMP"),
                ("bit@noomp", "Bit-identical, no OpenMP"), ("bit", "Bit-identical, OpenMP"),
                ("near@noomp", "Plus near-identical, no OpenMP"), ("near", "Plus near-identical, OpenMP")]
        cols = [c for c in cols if c[0] in fl["builds"]]
        L = ["| Case | " + " | ".join(c[1] for c in cols) + " |", "| --- |" + " ---: |" * len(cols)]
        for r in rows(fl, "step", 1):
            L.append(f"| {r['name']} | " + " | ".join(fmt(best(r, c[0])) for c in cols) + " |")
        text = replace(text, "flavours", "\n".join(L) + f"\n\nOne thread. {conditions(fl)}")
    oh = load("output-headline")
    if oh:
        L = ["| Case | Mode | Threads | Unpatched (s) | Bit-identical | Plus near-identical | Speed-up | Report and save, unpatched | Bit-identical | Identical |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
        for r in rows(oh):
            b, i, n = best(r, "base"), best(r, "bit"), best(r, "near")
            rb, ri = (best(r, "base", "report"), best(r, "bit", "report")) if r["mode"] == "solve" else (None, None)
            L.append(f"| {r['name']} | {r['mode']} | {r['threads']} | {fmt(b)} | {fmt(i)} | {fmt(n)} | {fsp(sp(b, n))} | "
                     f"{fmt(rb) if rb else ''} | {fmt(ri) if ri else ''} | {'yes' if sig(r, 'bit') == sig(r, 'base') else '**no**'} |")
        text = replace(text, "output", "\n".join(L) + f"\n\n{conditions(oh, 'solve and read mode')}")
    return text


def describe(d):
    if not d: return "-"
    return (f"about {d['pipes']:,} pipes and {d['junctions']:,} junctions, {d['tanks']} tanks, {d['pumps']} pumps; "
            f"{d['duration_s'] / 3600:g} h with a hydraulic step of {d['hydstep_s'] // 60} min")


def verification():
    series, near = load("series"), load("near-series")
    vsolve, vout, vnoomp = load("verify-solve"), load("verify-output"), load("verify-noomp")
    if not series:
        return None
    base_sig = {}
    for data in (series, vsolve, vout):
        if data:
            for r in data["results"]:
                base_sig[(r["case"], r["mode"], r["threads"])] = sig(r, "base")
    cols = [("step", 1), ("step", 8), ("solve", 1), ("solve", 8), ("read", 1), ("read", 8)]
    L = ["| Patch | " + " | ".join(f"{m.capitalize()}, {t} thread{'s' if t > 1 else ''}" for m, t in cols) +
         " | No OpenMP, 1 thread |", "| --- |" + " ---: |" * (len(cols) + 1)]
    ids = [b for b in series["builds"] if b != "base"] + ([b for b in near["builds"] if b != "bit"] if near else [])
    for b in ids:
        cells = []
        for m, t in cols:
            n = s = 0
            for data in (series, near, vsolve, vout):
                if not data or b not in data["builds"]: continue
                for r in rows(data, m, t):
                    if b in r["builds"] and (r["case"], m, t) in base_sig:
                        n += 1
                        s += sig(r, b) == base_sig[(r["case"], m, t)]
            cells.append(f"{s}/{n}" if n else "-")
        n = s = 0
        if vnoomp and b + "@noomp" in vnoomp["builds"]:
            for r in vnoomp["results"]:
                n += 1
                s += sig(r, b + "@noomp") == sig(r, "base")
        cells.append(f"{s}/{n}" if n else "-")
        link = link_of(b.replace("only:", ""))
        label = f"[{b}]({link})" if link else f"`{b}`"
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(L)


def link_of(pid):
    d = glob.glob(os.path.join(HERE, "[123]-*", pid + "-*"))
    return os.path.relpath(d[0], HERE) + "/" if d else None


def main():
    docs = []
    summaries, results = per_change(docs)
    near = load("near-series")
    hs = load("headline-step")
    for path in [os.path.join(HERE, "README.md")] + sorted(glob.glob(os.path.join(HERE, "[123]-*", "README.md"))) + \
            [os.path.join(HERE, "verification.md"), os.path.join(HERE, "results", "README.md")]:
        if "--only" in sys.argv and "3-bug-fixes" in path or "--only" in sys.argv and "2-near" in path:
            continue
        if not os.path.exists(path):
            continue
        text = open(path).read()
        new = text
        for pid, s in summaries.items():
            new = replace(new, f"summary:{pid}", s, "summary")
        if hs:
            new = replace(new, "machine", f"{hs['machine']}, `-O3 -DNDEBUG` with OpenMP, measured {hs['date']}")
        if path.endswith("/README.md") and os.path.dirname(path) == HERE:
            new = headline(new)
            new = index(new)
            ids = [k for k in results if k.startswith(("FIX-", "BIT-"))]
            if ids:
                same = [k for k in ids if results[k].startswith("Identical")]
                m = re.search(r"in all (\d+) runs \((.*)\)", results[ids[0]])
                if len(same) == len(ids) and m:
                    v = (f"Every one of the {len(ids)} fixes and bit-identical groups gave results identical to "
                         f"85a303d's in all of its {m.group(1)} runs: {m.group(2)}.")
                else:
                    v = (f"{len(same)} of the {len(ids)} fixes and bit-identical groups gave results identical to "
                         f"85a303d's in every run; see verification.md.")
                new = replace(new, "hl:verify", v)
        if "2-near-identical" in path:
            new = near_page(new, near)
        if path.endswith("verification.md"):
            v = verification()
            if v:
                new = replace(new, "verification", v)
        if new != text:
            open(path, "w").write(new)
            docs.append(os.path.relpath(path, HERE))
    print("Updated: " + (", ".join(docs) if docs else "nothing"))


if __name__ == "__main__":
    main()
