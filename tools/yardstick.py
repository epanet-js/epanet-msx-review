#!/usr/bin/env python3
"""Judge changes that are not bit-identical against how much EPANET-MSX's own results already
vary between platforms, and against a converged solution. Needs numpy.

  tools/yardstick.py run   [--builds base,base@nofma,base@fmafast,base@x86,bit@conv,only:NEAR-01,...]
                           [--cases main,output] [--tag yardstick] [--jobs 4] [--dumpevery N]
  tools/yardstick.py judge .build/results/yardstick.json      writes yardstick.md next to it
  tools/yardstick.py threads --builds only:NEAR-01,near [--cases main,output] [--threads 1,8,10]

run: every build runs every case once in solve mode, one thread, writing every concentration
after every step (bench -dump; with --dumpevery N, every Nth step, for large networks), the
report and the binary output file. The first build is the reference. Builds with a flavour
@nofma, @fmafast, @x86, @clang or @native are platform samples: the reference's source built
another way. A build with @conv is the converged reference (tools/converged.patch). Every
other build is a candidate, judged on its own against the reference: only:NEAR-02 is the
bit-identical series plus NEAR-02, and the bit-identical series gives the reference's results
bit for bit, so what moves is NEAR-02's doing. Every build is compared with the reference
(concentrations, report, mass balance) and with the converged reference (tools/compare.py).
Dumps of the reference, the samples and the converged reference are kept in
.build/yardstick/dumps/ and reused while their build is unchanged; a candidate's are deleted
once compared (--keep keeps them).

judge: the rule, per case, applied to every candidate:
  1. Where every platform sample is within tolerance (tier A or B for every species, see
     tools/compare.py), the candidate must be within tolerance too.
  2. Where a platform sample is not (a rounding change flipped a segment-merging decision,
     or a hydraulic event moved), the candidate must stay as close as the platforms: for
     every species, its 99th-percentile difference and its number of nodes and links beyond
     tier B may be at most twice the largest platform value (floors: the species' tier-A
     absolute limit, and 5 objects).
  3. Failing that, it passes if, for every species, it is no farther from the converged
     reference than the builds without it (the reference and the samples), within twice
     their largest value on the same two measures.
  The report and mass balance are judged alongside: the candidate's report may differ from
  the reference's only in printed values that move by at most one unit of their last digit,
  or by no more than twice as many units as a platform sample's; each mass-balance figure may
  move by at most 1e-5 of the species' largest figure (the report prints 6 significant
  digits), or twice the largest platform difference.

threads: each build at every thread count, and its @noomp twin, must give the same results
(hash of every concentration after every step, step mode) as itself at one thread.
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools'))


def need_numpy():
    """numpy is needed for the comparisons: if this Python has none, run again with one that has"""
    try:
        import numpy  # noqa: F401
        return
    except ImportError:
        pass
    if os.environ.get('YARDSTICK_REEXEC'):
        raise SystemExit('numpy is needed: pip install numpy')
    seen = {os.path.realpath(sys.executable)}
    for d in os.environ.get('PATH', '').split(os.pathsep) + [os.path.expanduser('~/.pyenv/shims')]:
        py = os.path.join(d, 'python3')
        if os.path.exists(py) and os.path.realpath(py) not in seen:
            seen.add(os.path.realpath(py))
            if subprocess.run([py, '-c', 'import numpy'], capture_output=True).returncode == 0:
                os.execve(py, [py] + sys.argv, dict(os.environ, YARDSTICK_REEXEC='1'))
    raise SystemExit('numpy is needed: pip install numpy')


need_numpy()
import compare  # noqa: E402
import bench    # noqa: E402

FLAVOURS = ('@nofma', '@fmafast', '@x86', '@clang', '@native')
SAMPLE_TITLES = {'@nofma': 'FMA off', '@fmafast': 'FMA across statements', '@x86': 'x86-64',
                 '@clang': 'clang', '@native': 'native'}
INTOL = ('IDENTICAL', 'A', 'B', 'A~', 'B~')
DUMPS = os.path.join(HERE, '.build', 'yardstick', 'dumps')


def role(b):
    if b.endswith('@conv'):
        return 'conv'
    if b.endswith(FLAVOURS):
        return 'sample'
    return 'candidate'


def title(b):
    return SAMPLE_TITLES.get(b[b.index('@'):], b) if '@' in b else b


def run_case(bdir, bname, case, keep, every):
    """one solve-mode run with dump, report and output file; returns paths and the RESULT line"""
    tag = bname.replace(':', '-').replace('/', '-')
    d = os.path.join(DUMPS, case['id'])
    os.makedirs(d, exist_ok=True)
    dump, rpt, out = (os.path.join(d, f'{tag}.{x}') for x in ('dump', 'rpt', 'out'))
    stampf = os.path.join(d, f'{tag}.stamp')
    stamp = open(os.path.join(bdir, 'stamp')).read().strip() + f' every {every}'
    if keep and os.path.exists(stampf) and open(stampf).read().strip() == stamp and os.path.exists(dump):
        return {'dump': dump, 'rpt': rpt, 'out': out, 'cached': True, **json.load(open(stampf + '.json'))}
    wd = os.path.join(HERE, '.build', 'work', 'yardstick', tag)
    os.makedirs(wd, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS='1')
    t0 = time.time()
    args = [os.path.join(bdir, 'bench'), case['inp'], case['msx'], '-mode', 'solve', '-dump', dump,
            '-rpt', rpt, '-out', out]
    if every > 1:
        args += ['-dumpevery', str(every)]
    p = subprocess.run(args, capture_output=True, text=True, env=env, cwd=wd)
    line = [l for l in p.stdout.splitlines() if l.startswith('RESULT')]
    f = line[0].split() if line else []
    info = {'rc': int(f[3]) if f else -1, 'steps': int(f[10]) if f else 0, 'hash': f[11] if f else '-',
            'seconds': round(time.time() - t0, 2)}
    if info['rc'] and not case.get('private'):
        info['err'] = p.stderr[-400:]
    if keep:
        open(stampf, 'w').write(stamp)
        json.dump(info, open(stampf + '.json', 'w'))
    return {'dump': dump, 'rpt': rpt, 'out': out, 'cached': False, **info}


def strip_where(cmp):
    for s in cmp.get('species', []):
        s.pop('maxabs_at', None)
        s.pop('maxabs_ref', None)
    return cmp


def cmd_run(a):
    specs = a.builds.split(',')
    ref = specs[0]
    convs = [b for b in specs if role(b) == 'conv']
    dirs = {b: bench.build(b) for b in specs}
    cases = bench.load_cases(a.cases, a.private_label)
    meta = {'builds': specs, 'ref': ref, 'samples': [b for b in specs[1:] if role(b) == 'sample'],
            'conv': convs[0] if convs else None,
            'candidates': [b for b in specs[1:] if role(b) == 'candidate'],
            'cases': [{'id': c['id'], 'name': c['name'], 'msx': os.path.relpath(c['msx'], HERE) if not c.get('private') else None}
                      for c in cases],
            'dumpevery': a.dumpevery, 'date': time.strftime('%Y-%m-%d'), 'machine': bench.machine(),
            'load_start': bench.loadavg()}
    res = {'meta': meta, 'results': {}}
    resdir = os.path.join(HERE, '.build', 'results')
    os.makedirs(resdir, exist_ok=True)
    path = os.path.join(resdir, a.tag + '.json')
    for case in cases:
        species = compare.read_species(case['msx'])
        print(f"{case['id']}: running {len(specs)} builds ...", flush=True)
        with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
            futs = {b: ex.submit(run_case, dirs[b], b, case, role(b) != 'candidate' or b == ref or a.keep, a.dumpevery)
                    for b in specs}
            runs = {b: f.result() for b, f in futs.items()}
        R = compare.read_dump(runs[ref]['dump'])
        C = compare.read_dump(runs[meta['conv']]['dump']) if meta['conv'] and runs[meta['conv']]['rc'] == 0 else None
        out = {}
        for b in specs:
            r = runs[b]
            rec = {k: r[k] for k in ('rc', 'steps', 'hash', 'seconds', 'cached') if k in r}
            if r['rc'] == 0:
                B = compare.read_dump(r['dump'])
                rec['vs_ref'] = compare.compare_dump_data(R, B, species)
                if C is not None:
                    rec['vs_conv'] = compare.compare_dump_data(C, B, species)
                rec['report'] = compare.compare_reports(runs[ref]['rpt'], r['rpt'])
                if case.get('private'):
                    strip_where(rec['vs_ref'])
                    if 'vs_conv' in rec:
                        strip_where(rec['vs_conv'])
                del B
            out[b] = rec
            v = rec.get('vs_ref', {}).get('verdict', 'ERROR')
            print(f"  {b:18s} rc={r['rc']} {r.get('seconds', 0):7.1f}s{' (cached)' if r['cached'] else ''}  vs ref {v}"
                  f"  vs conv {rec.get('vs_conv', {}).get('verdict', '-')}  report {rec.get('report', {}).get('verdict', '-')}",
                  flush=True)
        for b in specs:
            if role(b) == 'candidate' and b != ref and not a.keep:
                for k in ('dump', 'rpt', 'out'):
                    if os.path.exists(runs[b][k]):
                        os.remove(runs[b][k])
        res['results'][case['id']] = out
        json.dump(res, open(path, 'w'), indent=1)         # after every case, in case the run stops
    meta['load_end'] = bench.loadavg()
    json.dump(res, open(path, 'w'), indent=1)
    print(f'Results: {path}')
    judge(path)


# ---------------------------------------------------------------- judging

def floor_abs(sp):
    return min(0.5 * 10.0 ** -sp['precision'], sp['atol'])


def sp_of(cmp, sid):
    for s in cmp.get('species', []):
        if s['id'] == sid:
            return s
    return None


def limits(sid, sp, others):
    """the clause-2/3 limits for one species: (p99 limit, objects-beyond-B limit)"""
    os_ = [o for o in (sp_of(x, sid) for x in others) if o]
    return (max(2 * max([o['p99'] for o in os_] + [0.0]), floor_abs(sp)),
            max(2 * max([o['overB'] for o in os_] + [0]), 5))


def close_as(cand, others):
    """clause 2 / 3: per species, p99 and objects beyond tier B at most twice the others' largest"""
    why = []
    for s in cand.get('species', []):
        lp, lo = limits(s['id'], s, others)
        if s['p99'] > lp:
            why.append(f"{s['id']} p99 {s['p99']:.2g} > {lp:.2g}")
        if s['overB'] > lo:
            why.append(f"{s['id']} beyond B at {s['overB']} objects > {lo}")
    return why


def judge_case(rec, ref, samples, conv, cand):
    c = rec[cand]
    if c.get('rc', -1) != 0 or 'vs_ref' not in c:
        return 'ERROR', 'run failed', None
    sm = [rec[s]['vs_ref'] for s in samples if 'vs_ref' in rec.get(s, {})]
    cv = c['vs_ref']
    clause = 1
    if all(s['verdict'] in INTOL for s in sm):
        if cv['verdict'] in INTOL:
            j, why = 'PASS', 'within tolerance, as every platform is'
        else:
            j, why = 'EXCEEDS', 'beyond tolerance where every platform is within it'
    elif cv['verdict'] in INTOL:
        j, why = 'PASS', 'within tolerance where a platform is not'
    else:
        clause = 2
        w = close_as(cv, sm)
        if not w:
            j, why = 'PASS', 'as close as the platforms'
        elif conv and 'vs_conv' in c:
            clause = 3
            without = [rec[b]['vs_conv'] for b in [ref] + samples if 'vs_conv' in rec.get(b, {})]
            w3 = close_as(c['vs_conv'], without)
            if not w3:
                j, why = 'PASS', 'as close to the converged solution as the builds without it (' + '; '.join(w) + ')'
            else:
                j, why = 'EXCEEDS', '; '.join(w + ['converged: ' + x for x in w3])
        else:
            j, why = 'EXCEEDS', '; '.join(w)
    # report and mass balance
    rp = c.get('report', {})
    srp = [rec[s].get('report', {}) for s in samples]
    rwhy = []
    if rp.get('verdict') == 'FAIL':
        rwhy.append('report structure differs')
    elif rp.get('verdict') == 'DIGITS':
        lim = max([1.0] + [2 * s.get('max_last_digit_units', 0) for s in srp])
        if rp['max_last_digit_units'] > lim:
            rwhy.append(f"report values move by {rp['max_last_digit_units']:.3g} units of their last digit > {lim:.3g}")
        lim = max([1e-5] + [2 * s.get('mb_max_rel', 0) for s in srp])
        if rp['mb_max_rel'] > lim:
            rwhy.append(f"mass balance moves by {rp['mb_max_rel']:.2g} > {lim:.2g}")
        lim = max([1e-5] + [2 * s.get('mb_max_ratio_diff', 0) for s in srp])
        if rp['mb_max_ratio_diff'] > lim:
            rwhy.append(f"mass ratio moves by {rp['mb_max_ratio_diff']:.2g} > {lim:.2g}")
    if rwhy:
        j = 'EXCEEDS'
        why += '; ' + '; '.join(rwhy)
    return j, why, clause


def worst(cmp):
    """the species with the largest ratio to its tier-B limit"""
    sps = [s for s in cmp.get('species', []) if s['verdict'] != 'IDENTICAL']
    return max(sps, key=lambda s: s['ratioB']) if sps else None


def cell(cmp):
    if not cmp:
        return '-'
    v = cmp['verdict']
    w = worst(cmp)
    if not w:
        return v
    s = f"{v}: {w['id']} max {w['maxabs']:.2g} (rel {w['maxrel']:.1g}), p99 {w['p99']:.2g}"
    nb = max(s_['overB'] for s_ in cmp['species'])
    if nb:
        s += f', beyond B {nb}'
    return s


def rcell(rp):
    if not rp:
        return '-'
    if rp['verdict'] == 'IDENTICAL':
        return 'identical'
    if rp['verdict'] == 'FAIL':
        return 'FAIL: ' + rp.get('reason', '')
    s = f"{rp['differ_lines']} lines" if rp['differ_lines'] else 'MSX tables identical'
    if rp.get('differ_lines_epanet'):
        s += f" (and {rp['differ_lines_epanet']} lines of EPANET's hydraulic log)"
    if rp['differ_numbers']:
        s += f", ≤{rp['max_last_digit_units']:.3g} last digit"
    if rp['mb_max_rel']:
        s += f"; mass balance {rp['mb_max_rel']:.1g}"
    return s


def detail(rec, ref, samples, conv, cand, clause):
    """per species: the candidate against each platform sample and the 2x limit (clause 2), and
    the same distances from the converged reference (clause 3)"""
    c = rec[cand]['vs_ref']
    sm = [rec[s]['vs_ref'] for s in samples if 'vs_ref' in rec.get(s, {})]
    L = ['| Species | Candidate p99 / beyond B | ' + ' | '.join(title(s) for s in samples) +
         ' | Limit (2x the largest) | Within |', '|' + ' --- |' * (len(samples) + 4)]
    for s in c.get('species', []):
        if s['verdict'] == 'IDENTICAL':
            continue
        lp, lo = limits(s['id'], s, sm)
        cells = []
        for x in sm:
            o = sp_of(x, s['id'])
            cells.append(f"{o['p99']:.2g} / {o['overB']}" if o else '-')
        ok = s['p99'] <= lp and s['overB'] <= lo
        L.append(f"| {s['id']} | {s['p99']:.2g} / {s['overB']} | " + ' | '.join(cells) +
                 f" | {lp:.2g} / {lo} | {'yes' if ok else '**no**'} |")
    if conv and 'vs_conv' in rec[cand]:
        cc = rec[cand]['vs_conv']
        without = [(b, rec[b]['vs_conv']) for b in [ref] + samples if 'vs_conv' in rec.get(b, {})]
        L += ['', f'Distance from the converged reference `{conv}` (p99 / beyond B), clause 3:', '',
              '| Species | Candidate | ' + ' | '.join(f'`{b}`' for b, _ in without) + ' | Limit | Within |',
              '|' + ' --- |' * (len(without) + 4)]
        for s in cc.get('species', []):
            if s['verdict'] == 'IDENTICAL' and all((sp_of(w, s['id']) or {}).get('verdict') == 'IDENTICAL' for _, w in without):
                continue
            lp, lo = limits(s['id'], s, [w for _, w in without])
            cells = []
            for _, w in without:
                o = sp_of(w, s['id'])
                cells.append(f"{o['p99']:.2g} / {o['overB']}" if o else '-')
            ok = s['p99'] <= lp and s['overB'] <= lo
            L.append(f"| {s['id']} | {s['p99']:.2g} / {s['overB']} | " + ' | '.join(cells) +
                     f" | {lp:.2g} / {lo} | {'yes' if ok else '**no**'} |")
    return L


def judge(path):
    res = json.load(open(path))
    m = res['meta']
    ref, samples, conv, cands = m['ref'], m['samples'], m['conv'], m['candidates']
    names = {c['id']: c['name'] for c in m['cases']}
    L = [f"Reference `{ref}`; platform samples " + ', '.join(f'`{s}`' for s in samples) +
         (f"; converged reference `{conv}`" if conv else '') + f". {m['machine']}, {m['date']}." +
         (f" Every {m['dumpevery']}th step compared." if m.get('dumpevery', 1) > 1 else ''), '']
    L += ['### Platform variation', '',
          'Each sample against the reference: the verdict, then the species furthest from it relative to its '
          'tier-B limit, with its largest absolute difference (and the largest relative difference), its 99th '
          'percentile, and the most nodes and links beyond tier B for any species. Concentrations in the '
          "species' own units. Report: lines that differ, and how far printed values and the mass balance move.", '',
          '| Case | ' + ' | '.join(title(s) for s in samples) + ' | Reports |',
          '|' + ' --- |' * (len(samples) + 2)]
    for cid, rec in res['results'].items():
        L.append(f'| {names[cid]} | ' + ' | '.join(cell(rec.get(s, {}).get('vs_ref')) for s in samples) + ' | ' +
                 '; '.join(f"{title(s)}: {rcell(rec.get(s, {}).get('report'))}" for s in samples) + ' |')
    if conv:
        L += ['', '### Distance from the converged reference', '',
              f'Every build against `{conv}` (integrator tolerances 1000 times tighter, Newton to 8 significant '
              'digits, Euler replaced by RK5; segments merged as before). The same measures as above.', '',
              '| Case | ' + ' | '.join(f'`{b}`' for b in [ref] + samples + cands) + ' |',
              '|' + ' --- |' * (len(samples) + len(cands) + 2)]
        for cid, rec in res['results'].items():
            L.append(f'| {names[cid]} | ' + ' | '.join(cell(rec.get(b, {}).get('vs_conv')) for b in [ref] + samples + cands) + ' |')
    counts = {}
    bad = 0
    details = []
    for c in cands:
        L += ['', f'### `{c}`', '', '| Case | Candidate | Report | Judgement | Why |', '| --- | --- | --- | --- | --- |']
        for cid, rec in res['results'].items():
            if c not in rec:
                continue
            j, why, clause = judge_case(rec, ref, samples, conv, c)
            counts[j] = counts.get(j, 0) + 1
            bad += j != 'PASS'
            rec[c]['judgement'] = [j, why, clause]
            L.append(f"| {names[cid]} | {cell(rec[c].get('vs_ref'))} | {rcell(rec[c].get('report'))} | {j} | {why} |")
            if clause and clause >= 2:
                details += ['', f'#### `{c}` on {names[cid]}', '',
                            f'Clause {clause} applied. Per species, the 99th percentile of the difference from the '
                            'reference and the number of nodes and links beyond tier B, for the candidate and each '
                            'platform sample:', ''] + detail(rec, ref, samples, conv, c, clause)
    if counts:
        L += ['', 'Totals: ' + ', '.join(f'{k} {v}' for k, v in sorted(counts.items()))]
    if details:
        L += ['', '### Cases judged by clause 2 or 3'] + details
    md = '\n'.join(L) + '\n'
    out = os.path.splitext(path)[0] + '.md'
    open(out, 'w').write(md)
    json.dump(res, open(path, 'w'), indent=1)
    print(md)
    print(f'Written: {out}')
    return bad


def cmd_threads(a):
    cases = bench.load_cases(a.cases, a.private_label)
    threads = a.threads.split(',')
    ok = True
    rows = []
    for b in a.builds.split(','):
        dirs = {b: bench.build(b), b + '@noomp': bench.build(b + '@noomp')}
        for case in cases:
            hashes = {}
            for name, d in dirs.items():
                for th in (threads if name == b else ['1']):
                    wd = os.path.join(HERE, '.build', 'work', 'threads', name.replace(':', '-'))
                    os.makedirs(wd, exist_ok=True)
                    env = dict(os.environ, OMP_NUM_THREADS=th)
                    p = subprocess.run([os.path.join(d, 'bench'), case['inp'], case['msx'], '-check'],
                                       capture_output=True, text=True, env=env, cwd=wd)
                    f = [l for l in p.stdout.splitlines() if l.startswith('RESULT')]
                    hashes[f'{name} {th}t'] = f[0].split()[11] if f else 'ERROR'
            same = len(set(hashes.values())) == 1
            ok &= same
            rows.append({'build': b, 'case': case['id'], 'name': case['name'], 'same': same,
                         'runs': sorted(hashes), 'hashes': None if case.get('private') else hashes})
            print(f"{b:16s} {case['id']:14s} {'same' if same else 'DIFFERENT'}  " +
                  ' '.join(f'{k}={v[:8]}' for k, v in hashes.items()), flush=True)
    os.makedirs(os.path.join(HERE, '.build', 'results'), exist_ok=True)
    json.dump({'builds': a.builds.split(','), 'threads': threads, 'date': time.strftime('%Y-%m-%d'),
               'all_same': ok, 'rows': rows},
              open(os.path.join(HERE, '.build', 'results', a.tag + '.json'), 'w'), indent=1)
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--builds', default='base,base@nofma,base@fmafast,base@x86,bit@conv,near')
    r.add_argument('--cases', default='main,output')
    r.add_argument('--tag', default='yardstick')
    r.add_argument('--jobs', type=int, default=4)
    r.add_argument('--dumpevery', type=int, default=1)
    r.add_argument('--keep', action='store_true', help="keep the candidates' dumps too")
    r.add_argument('--private-label', default='Private model')
    j = sub.add_parser('judge')
    j.add_argument('path')
    t = sub.add_parser('threads')
    t.add_argument('--builds', required=True)
    t.add_argument('--cases', default='main,output')
    t.add_argument('--threads', default='1,8,10')
    t.add_argument('--tag', default='threads')
    t.add_argument('--private-label', default='Private model')
    a = ap.parse_args()
    if a.cmd == 'run':
        cmd_run(a)
    elif a.cmd == 'judge':
        sys.exit(1 if judge(a.path) else 0)
    else:
        cmd_threads(a)


if __name__ == '__main__':
    main()
