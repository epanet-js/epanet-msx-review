#!/usr/bin/env python3
"""Reduce a tools/bench.py run on private models to what can be shared.

  tools/private-summary.py .build/results/private.json > private-summary.json

Keeps, per case, mode and thread count: the case label ("Utility model 1, chloramine
(ROS2)"), each build's best time and return code, its speed-up over the first build, whether
its results were identical to the first build's, and the load average. Drops the models'
sizes, peak memory, result hashes, output-file and report checksums, error messages, file
names and paths, so nothing in the output depends on the models' contents other than how
long they took to run and whether builds agreed.
"""
import json
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    d = json.load(open(sys.argv[1]))
    out = {"builds": d["builds"], "threads": d["threads"], "modes": d["modes"], "reps": d["reps"],
           "machine": d.get("machine"), "date": d.get("date"), "start": d.get("start"), "end": d.get("end"),
           "results": []}
    for r in d["results"]:
        rec = {"case": r["case"], "name": r["name"].split(" [")[0], "mode": r["mode"], "threads": r["threads"],
               "load_start": r.get("load_start"), "load_end": r.get("load_end"), "builds": {}}
        for b, v in r["builds"].items():
            rec["builds"][b] = {"best": v.get("best"), "best_Q": v.get("best_Q"),
                                "rc": v.get("rc"), "speedup": v.get("speedup"), "identical": v.get("identical")}
        out["results"].append(rec)
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
