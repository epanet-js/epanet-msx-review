#!/usr/bin/env python3
"""Check a newer EPANET-MSX against the patches, and write status.md.

  tools/check.py                 the dev branch as it is on GitHub now
  tools/check.py pull/28         a pull request
  tools/check.py v2.0.0          a tag, branch or commit
  tools/check.py --quick         one checked run per build (the default; --reps 3 for best of 3)
  tools/check.py --prs           also list the open pull requests and how far the series
                                 applies to each (no build, no timing)

It fetches the version from GitHub into the msx submodule, finds the EPANET 2.2 commit that
version pins, and records what happens to each patch there: applied, applied after a
three-way merge, already in MSX, or does not apply (the series stops there). Each fix is
also applied on its own. Then tools/try.py times 85a303d, its bit-identical and
near-identical builds, the newer version, and the newer version with the same patches, on
the 7 main cases, and checks whether the bit-identical patches still leave the newer
version's results unchanged. The outcome goes to status.md, compared with the check it
replaces; commit it to keep it, or discard it with git checkout status.md.

Tests for the fixes come with the fixes' write-ups; until then a fix that no longer applies
is reported as such, not as fixed.
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import bench  # noqa: E402

REPO = "https://github.com/USEPA/EPANETMSX"
API = "https://api.github.com/repos/USEPA/EPANETMSX"
MEASURED = "85a303dca05859389eced63fabd5ea145c096333"


def sh(*args, env=None):
    return subprocess.run(list(args), capture_output=True, text=True, env=env)


def msxenv(ref):
    return dict(os.environ, MSX_COMMIT=ref)


def states(ref, name):
    """what happens to each patch of a build on ref, without compiling"""
    p = sh(os.path.join(HERE, "tools", "build-msx.sh"), f"{ref}:{name}",
           env=dict(os.environ, APPLY_ONLY="1", PARTIAL="1"))
    if p.returncode:
        return None
    out = p.stdout.strip().splitlines()[-1]
    return [l.split(" ", 1) for l in open(os.path.join(out, "patches.txt")).read().splitlines() if l]


def series_ids():
    return [os.path.basename(p).replace(".patch", "")
            for p in sh(os.path.join(HERE, "tools", "patch-order.sh"), "all").stdout.split()]


def open_prs():
    try:
        with urllib.request.urlopen(API + "/pulls?state=open&per_page=100", timeout=30) as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"Could not list pull requests: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ref", nargs="?", default="dev")
    ap.add_argument("--quick", action="store_true", default=True)
    ap.add_argument("--reps", type=int, default=None, help="best of N interleaved runs instead of one checked run")
    ap.add_argument("--prs", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "status.md"))
    a = ap.parse_args()
    ref = a.ref

    print(f"Fetching {ref} from GitHub ...", flush=True)
    sh(os.path.join(HERE, "tools", "get-msx.sh"), "--fetch", env=msxenv(ref))
    p = sh(os.path.join(HERE, "tools", "get-msx.sh"), "--commit", env=msxenv(ref))
    if p.returncode:
        raise SystemExit(p.stderr)
    sha = p.stdout.strip()
    ep = sh(os.path.join(HERE, "tools", "get-msx.sh"), "--epanet", env=msxenv(ref)).stdout.strip()
    src = sh(os.path.join(HERE, "tools", "get-msx.sh")).stdout.strip()
    subject = sh("git", "-C", src, "log", "-1", "--format=%cs %s", sha).stdout.strip()
    upstream = sh("git", "-C", src, "log", "--format=%h %cs %s", f"{MEASURED}..{sha}").stdout.strip().splitlines()

    # each patch on ref: the series in order (it stops at the first that does not apply), and each fix alone
    allst = states(sha, "all") or []
    fixes = [i for i in series_ids() if i.startswith("FIX-")]
    alone = {f: (states(sha, f) or [[f, "?"]])[-1][1] for f in fixes}

    # speed and results: tools/try.py
    short = sha[:7]
    targets = ["bit", "near", short, f"{short}:bit", f"{short}:near"]
    cmd = [os.path.join(HERE, "tools", "try.py")] + targets + ["--no-fetch", "--no-tolerance"]
    cmd += ["--reps", str(a.reps)] if a.reps else ["--quick"]
    print("Timing: " + " ".join(cmd[1:]), flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, PARTIAL="1"))
    m = re.search(r"Written: (\S+)\.md", p.stdout)
    tr = json.load(open(m.group(1) + ".json")) if m else None
    if not tr:
        sys.stderr.write(p.stdout[-2000:] + p.stderr[-2000:])

    prs = None
    if a.prs:
        prs = []
        for pr in open_prs() or []:
            n = pr["number"]
            sh(os.path.join(HERE, "tools", "get-msx.sh"), "--fetch", env=msxenv(f"pull/{n}"))
            psha = sh(os.path.join(HERE, "tools", "get-msx.sh"), "--commit", env=msxenv(f"pull/{n}")).stdout.strip()
            st = states(psha, "all") if psha else None
            prs.append({"number": n, "title": pr["title"], "updated": pr["updated_at"][:10], "sha": psha, "states": st})

    # previous check, to say what changed
    prevf = os.path.join(HERE, "results", "status.json")
    prev = json.load(open(prevf)) if os.path.exists(prevf) else None
    cur = {"date": time.strftime("%Y-%m-%d"), "ref": ref, "sha": sha, "epanet": ep, "patches": allst, "fixes_alone": alone,
           "prs": prs, "try": os.path.relpath(m.group(1) + ".json", HERE) if m else None}

    # ---- write status.md
    L = ["# Status against the latest EPANET-MSX", "", "[All changes](README.md)", ""]
    L.append(f"Checked on {time.strftime('%-d %B %Y')} against EPANET-MSX `{ref}` at [{short}]({REPO}/commit/{sha}) "
             f"({subject}), with `tools/check.py`. It pins EPANET 2.2 at {ep[:7]}"
             f"{', as 85a303d does' if ep.startswith('1e2fc3d') else ''}.")
    if tr:
        L[-1] += (f" {tr['machine']}; {'one checked run per build' if tr.get('quick') else 'best of several interleaved runs'} "
                  f"on the 7 main cases; load average {tr['start']['load'][0]} at the start and {tr['end']['load'][0]} at the end.")
        if tr["start"]["load"][0] > (os.cpu_count() or 8):
            L[-1] += (" The machine was busy (a load average above its core count), so treat the speed-ups as rough; "
                      "`tools/check.py --reps 3` measures them again more carefully.")
    L += ["", f"## Upstream changes since 85a303d", ""]
    if upstream:
        L += [f"- `{u.split(' ', 2)[0]}` {u.split(' ', 2)[1]}: {u.split(' ', 2)[2]}" for u in upstream]
    else:
        L += ["None."]
    if tr:
        recs = tr["results"]
        base = tr["baseline"]

        def med(t, mode, th):
            xs = [r["builds"][base]["best"] / r["builds"][t]["best"] for r in recs
                  if r["mode"] == mode and r["threads"] == th and r["builds"].get(t, {}).get("best")
                  and r["builds"][base].get("best")]
            xs.sort()
            return f"{xs[len(xs) // 2]:.2f}x" if xs else "-"
        cols = [(short, short), ("85a303d + bit-identical", "bit"), (f"{short} + bit-identical", f"{short}:bit"),
                ("85a303d + near-identical", "near"), (f"{short} + near-identical", f"{short}:near")]
        L += ["", "## Speed", "", "Median speed-up over 85a303d, per case:", "",
              "| How MSX is run | " + " | ".join(c[0] for c in cols) + " |", "| --- |" + " ---: |" * len(cols)]
        for mode, th, label in (("step", 1, "Step, 1 thread"), ("step", 8, "Step, 8 threads"), ("solve", 1, "Solve, 1 thread")):
            L.append(f"| {label} | " + " | ".join(med(c[1], mode, th) for c in cols) + " |")
    L += ["", "## The patches on this version", ""]
    counts = {}
    for i, s in allst:
        counts.setdefault(s, []).append(i)
    order = ["applied", "applied (3-way merge)", "already in MSX", "does not apply (a fix; skipped)", "does not apply"]
    for s in order + [k for k in counts if k not in order]:
        if s in counts:
            ids = counts[s]
            L.append(f"- {s[0].upper() + s[1:]}: {len(ids)}" + (f" ({', '.join(ids)})" if len(ids) <= 4 else ""))
    L += ["", "Each fix on its own (a fix that no longer applies may be fixed upstream another way; its README says "
          "what is known, and its test, once added, will tell):", "", "| Fix | On this version |", "| --- | --- |"]
    for f, s in alone.items():
        d = next((d for d in os.listdir(os.path.join(HERE, "3-bug-fixes")) if d.startswith(f)), "")
        L.append(f"| [{f}](3-bug-fixes/{d}/) | {s.replace(' (a fix; skipped)', '')} |")
    if tr:
        v = tr["verdict"]
        own = tr["own_base"]
        L += ["", "## Results", ""]
        bt = f"{short}:bit"
        if bt in v:
            n = sum(1 for r in recs if r["builds"].get(bt))
            L.append(f"- With the bit-identical patches, {short}'s results are "
                     + ("unchanged in all " + str(n) + " runs." if v[bt]["identical"] else "**not** unchanged; see the try summary."))
        if short in v:
            d = [r for r in recs if r["builds"][short]["check"].get("hash") != r["builds"][base]["check"].get("hash")
                 or r["builds"][short]["check"].get("out_md5") != r["builds"][base]["check"].get("out_md5")
                 or r["builds"][short]["check"].get("rpt_md5") != r["builds"][base]["check"].get("rpt_md5")]
            L.append(f"- {short}'s own results " + (f"differ from 85a303d's in {len(d)} of {len(recs)} runs; "
                                                    "upstream changes account for this, not the patches."
                                                    if d else f"are the same as 85a303d's in all {len(recs)} runs."))
    L += ["", "## Each patch", "", "| Patch | State |", "| --- | --- |"] + [f"| {i} | {s} |" for i, s in allst]
    if prs is not None:
        L += ["", "## Open pull requests", "",
              "Whether the series applies on top of each open pull request (FIX-01 to NEAR-03 in order; no build).", "",
              "| Pull request | Updated | Series |", "| --- | --- | --- |"]
        for pr in prs:
            st = pr["states"]
            if st is None:
                s = "could not be checked"
            else:
                bad = [i for i, x in st if x == "does not apply"]
                merged = [i for i, x in st if "3-way" in x]
                skipped = [i for i, x in st if "skipped" in x]
                s = (f"stops at {bad[0]}, which does not apply" if bad else "every patch applies") + \
                    (f"; {', '.join(merged)} after a three-way merge" if merged else "") + \
                    (f"; {', '.join(skipped)} skipped (does not apply)" if skipped else "")
            L.append(f"| [#{pr['number']}]({REPO}/pull/{pr['number']}) {pr['title']} | {pr['updated']} | {s} |")
    if prev and prev.get("sha") != sha:
        was = dict((i, s) for i, s in prev.get("patches", []))
        changed = [f"{i}: {was.get(i, '-')} → {s}" for i, s in allst if was.get(i) != s]
        L += ["", "## Since the last check", "", f"The last check was of {prev['ref']} at {prev['sha'][:7]} on {prev['date']}.", ""]
        L += [f"- {c}" for c in changed] if changed else ["- No patch changed state."]
    open(a.out, "w").write("\n".join(L) + "\n")
    os.makedirs(os.path.dirname(prevf), exist_ok=True)
    json.dump(cur, open(prevf, "w"), indent=1)
    print("\n".join(L))
    print(f"\nWritten: {a.out}")


if __name__ == "__main__":
    main()
