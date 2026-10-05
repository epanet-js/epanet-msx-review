#!/usr/bin/env python3
"""Compare the results of two EPANET-MSX builds value by value, for changes that are not
bit-identical. Needs numpy.

  tools/compare.py REF.dump NEW.dump --msx FILE.msx          concentrations (bench -dump)
  tools/compare.py REF.rpt NEW.rpt                           report and mass balance
  add --json for the full result as JSON, and --no-where to leave out where the largest
  difference is (node or link number and time), as for private models

A dump (bench -dump) holds every node's and every link's concentration of every species
after every step, as float64. Each species is judged on its own terms, from the .msx file:

  tier A  below the species' report precision, and within tier B:
            |d| <= min(0.5 * 10^-precision, aTol + rTol*|c|)
  tier B  within the species' own tolerance:  |d| <= aTol + rTol*|c|
          (c is the reference value; aTol and rTol are the species' tolerances, or the
          ATOL / RTOL options, or MSX's defaults 0.01 and 0.001; precision is the [REPORT]
          precision, 2 by default). aTol is both the integrators' absolute tolerance and the
          threshold below which the transport merges two segments (MSXqual_isSame), so
          concentrations that differ by less than it are, to MSX, the same water.

Verdicts, per species and for the whole case (the worst species):
  IDENTICAL  every value equal
  A, B       every value within that tier
  A~, B~     the step times differ (a hydraulic event at another time), but every common
             step is within that tier
  FAIL       larger
Also reported per species: the largest absolute difference and where it is, the largest
relative difference (over values of at least aTol), the 99th percentile of the absolute
difference over all values, and the number of nodes and links beyond tier A and tier B at
some step.

Reports (EPANET's report file, which MSX writes into): every line is compared after the date
and time stamps are removed; for lines that differ, every number in them is compared, and
the mass balance of each species is compared figure by figure, relative to the largest
figure of that species' balance.
"""
import json
import math
import re
import struct
import sys

import numpy as np

MAGIC = 0x3158534d       # 'MSX1'
DEF_ATOL, DEF_RTOL, DEF_PREC = 0.01, 0.001, 2


def read_species(msxfile):
    """Species of a .msx file in input order: id, type, units, aTol, rTol, report precision."""
    sect = None
    species, opts, prec = [], {}, {}
    for raw in open(msxfile, errors='replace'):
        line = raw.split(';')[0].strip()
        if not line:
            continue
        if line.startswith('['):
            sect = line.upper()
            continue
        tok = line.split()
        if sect == '[OPTIONS]' and len(tok) >= 2:
            opts[tok[0].upper()] = tok[1]
        elif sect == '[SPECIES]' and len(tok) >= 3:
            sp = {'id': tok[1], 'type': tok[0].upper(), 'units': tok[2], 'atol': 0.0, 'rtol': 0.0}
            if len(tok) >= 4:
                sp['atol'] = float(tok[3])
            if len(tok) >= 5:
                sp['rtol'] = float(tok[4])
            species.append(sp)
        elif sect == '[REPORT]' and len(tok) >= 4 and tok[0].upper() == 'SPECIES':
            try:
                prec[tok[1].upper()] = int(tok[3])
            except ValueError:
                pass
    atol = float(opts.get('ATOL', DEF_ATOL))
    rtol = float(opts.get('RTOL', DEF_RTOL))
    for sp in species:
        if sp['atol'] == 0.0:
            sp['atol'] = atol
        if sp['rtol'] == 0.0:
            sp['rtol'] = rtol
        sp['precision'] = prec.get(sp['id'].upper(), DEF_PREC)
    return species


def read_dump(path):
    """int32 magic, nn, nl, ns; per step: int32 t, then per species nn node and nl link float64."""
    b = open(path, 'rb').read()
    magic, nn, nl, ns = struct.unpack('<4i', b[:16])
    if magic != MAGIC:
        raise ValueError(f'{path}: not a bench dump')
    dt = np.dtype([('t', '<i4'), ('v', '<f8', (ns, nn + nl))])
    nsteps = (len(b) - 16) // dt.itemsize
    rec = np.frombuffer(b, dt, nsteps, 16)
    return {'nn': nn, 'nl': nl, 'ns': ns, 't': rec['t'].copy(), 'v': rec['v']}


def where(nn, step_t, obj):
    return {'t': int(step_t), 'object': f'node {obj + 1}' if obj < nn else f'link {obj - nn + 1}'}


def compare_species(a, b, sp, times, nn):
    """a, b: [steps, objects] values of one species (a is the reference)."""
    # equal values (infinities included: LOG10 of a zero concentration is -inf) do not differ
    with np.errstate(invalid='ignore'):
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        d = np.where(same, 0.0, np.abs(a - b))
    d = np.where(np.isnan(d), np.inf, d)
    r = {'id': sp['id'], 'units': sp['units'], 'atol': sp['atol'], 'rtol': sp['rtol'], 'precision': sp['precision']}
    if not d.size or not d.any():
        r.update(verdict='IDENTICAL', maxabs=0.0, maxrel=0.0, p99=0.0, ratioA=0.0, ratioB=0.0,
                 overA=0, overB=0, differ=0)
        return r
    fin = np.isfinite(a)
    limB = np.where(fin, sp['atol'] + sp['rtol'] * np.abs(np.where(fin, a, 0.0)), sp['atol'])
    limA = np.minimum(0.5 * 10.0 ** -sp['precision'], limB)
    k = np.unravel_index(d.argmax(), d.shape)
    big = fin & (np.abs(np.where(fin, a, 0.0)) >= sp['atol'])
    rel = d[big] / np.abs(a[big]) if big.any() else np.zeros(1)
    r['maxabs'] = float(d.max())
    r['maxabs_at'] = where(nn, times[k[0]], k[1])
    r['maxabs_ref'] = float(a[k])
    r['maxrel'] = float(rel.max())
    r['p99'] = float(np.percentile(d, 99))
    r['ratioA'] = float((d / limA).max())
    r['ratioB'] = float((d / limB).max())
    r['overA'] = int((d > limA).any(axis=0).sum())
    r['overB'] = int((d > limB).any(axis=0).sum())
    r['differ'] = int((d > 0).any(axis=0).sum())
    r['verdict'] = 'A' if r['ratioA'] <= 1 else 'B' if r['ratioB'] <= 1 else 'FAIL'
    return r


ORDER = {'IDENTICAL': 0, 'A': 1, 'B': 2, 'FAIL': 3}


def compare_dump_data(A, B, species):
    res = {'nn': A['nn'], 'nl': A['nl'], 'objects': A['nn'] + A['nl']}
    if (A['nn'], A['nl'], A['ns']) != (B['nn'], B['nl'], B['ns']):
        res.update(verdict='FAIL', reason='different network or species')
        return res
    common, ia, ib = np.intersect1d(A['t'], B['t'], return_indices=True)
    res['steps'] = int(len(common))
    res['unmatched'] = [int(len(A['t']) - len(common)), int(len(B['t']) - len(common))]
    res['species'] = []
    for m, sp in enumerate(species[:A['ns']]):
        res['species'].append(compare_species(A['v'][ia, m, :], B['v'][ib, m, :], sp, common, A['nn']))
    worst = max((s['verdict'] for s in res['species']), key=ORDER.get, default='IDENTICAL')
    if res['unmatched'] != [0, 0]:
        res['verdict'] = worst + '~' if worst in ('A', 'B', 'IDENTICAL') else 'FAIL'
        if res['verdict'] == 'IDENTICAL~':
            res['verdict'] = 'A~'
        res['reason'] = 'step times differ'
    else:
        res['verdict'] = worst
    return res


def compare_dumps(ref, new, msxfile):
    return compare_dump_data(read_dump(ref), read_dump(new), read_species(msxfile))


# ---------------------------------------------------------------- reports

STAMP = re.compile(r'(Page \d+ .*\d\d:\d\d:\d\d \d{4})|Analysis (begun|ended)')
NUM = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?')
MB_FIELDS = (('Initial Mass:', 'initial'), ('Mass Inflow:', 'inflow'), ('Mass Outflow:', 'outflow'),
             ('Mass Reacted:', 'reacted'), ('Final Mass:', 'final'), ('Mass Ratio:', 'ratio'))


def report_lines(path):
    return [l.rstrip('\n') for l in open(path, errors='replace') if not STAMP.search(l)]


def mass_balance(lines):
    mb, cur = {}, None
    for l in lines:
        m = re.search(r'Water Quality Mass Balance: (\S+)', l)
        if m:
            cur = m.group(1)
            mb[cur] = {}
            continue
        if cur:
            for label, key in MB_FIELDS:
                if l.strip().startswith(label):
                    mb[cur][key] = float(l.split(':')[1])
    return mb


def last_digit_unit(s):
    """value of one unit in the last printed digit of the number string s"""
    mant, _, exp = s.lower().partition('e')
    dec = len(mant.split('.')[1]) if '.' in mant else 0
    return 10.0 ** (-dec + (int(exp) if exp else 0))


def compare_reports(ref, new):
    a, b = report_lines(ref), report_lines(new)
    res = {'lines': len(a), 'lines_new': len(b)}
    if len(a) != len(b):
        res.update(verdict='FAIL', reason='different number of lines')
        return res
    # MSX's own report starts at its first page header; the lines before it are EPANET's (its
    # header and, when the input file asks for it, the hydraulic status log), which MSX changes
    # cannot affect but the platform samples (EPANET built differently) do
    msx0 = next((i for i, l in enumerate(a) if 'EPANET-MSX' in l and 'Page' in l), 0)
    ndiff, nums, maxunits, maxabs, struct_diff, epdiff = 0, 0, 0.0, 0.0, 0, 0
    for i, (x, y) in enumerate(zip(a, b)):
        if x == y:
            continue
        if i < msx0:
            epdiff += 1
            continue
        ndiff += 1
        if any(x.strip().startswith(label) for label, _ in MB_FIELDS):
            continue                            # judged with the mass balance below
        nx, ny = NUM.findall(x), NUM.findall(y)
        if len(nx) != len(ny) or NUM.sub('#', x) != NUM.sub('#', y):
            struct_diff += 1
            continue
        for u, v in zip(nx, ny):
            if u != v:
                nums += 1
                d = abs(float(u) - float(v))
                maxabs = max(maxabs, d)
                maxunits = max(maxunits, d / last_digit_unit(u))
    res.update(differ_lines=ndiff, differ_lines_epanet=epdiff, differ_numbers=nums, max_abs=maxabs, max_last_digit_units=round(maxunits, 3),
               structure_differs=struct_diff)
    ma, mb = mass_balance(a), mass_balance(b)
    mbres = {}
    for sp in ma:
        fa, fb = ma[sp], mb.get(sp, {})
        scale = max([abs(fa[k]) for k in fa if k != 'ratio'] + [0.0])
        rel = {k: (abs(fa[k] - fb.get(k, math.nan)) / scale if scale > 0 else abs(fa[k] - fb.get(k, math.nan)))
               for k in fa if k != 'ratio'}
        mbres[sp] = {'max_rel': max(rel.values()) if rel else 0.0,
                     'ratio_diff': abs(fa.get('ratio', 0.0) - fb.get('ratio', math.nan)),
                     'ratio': [fa.get('ratio'), fb.get('ratio')]}
    res['mass_balance'] = mbres
    res['mb_max_rel'] = max([v['max_rel'] for v in mbres.values()] + [0.0])
    res['mb_max_ratio_diff'] = max([v['ratio_diff'] for v in mbres.values()] + [0.0])
    if struct_diff:
        res['verdict'] = 'FAIL'
        res['reason'] = 'report structure differs'
    elif ndiff == 0 and epdiff == 0:
        res['verdict'] = 'IDENTICAL'
    else:
        res['verdict'] = 'DIGITS'
    return res


# ---------------------------------------------------------------- text

def g(x):
    return f'{x:.2g}'


def fmt_dump(r, where=True):
    s = f"VERDICT={r['verdict']}"
    if 'reason' in r:
        s += f" ({r['reason']})"
    if 'steps' in r:
        s += f" steps={r['steps']} unmatched={r['unmatched'][0]}/{r['unmatched'][1]} objects={r['objects']}"
    lines = [s]
    for sp in r.get('species', []):
        if sp['verdict'] == 'IDENTICAL':
            lines.append(f"  {sp['id']:8s} IDENTICAL")
            continue
        at = sp['maxabs_at']
        loc = f" ({at['object']} t={at['t']}, ref {g(sp['maxabs_ref'])})" if where else ''
        lines.append(f"  {sp['id']:8s} {sp['verdict']:4s} max {g(sp['maxabs'])}{loc}"
                     f" maxrel {g(sp['maxrel'])} p99 {g(sp['p99'])} ratioA {g(sp['ratioA'])} ratioB {g(sp['ratioB'])}"
                     f" beyond A/B {sp['overA']}/{sp['overB']} of {r['objects']} (differ {sp['differ']})")
    return '\n'.join(lines)


def fmt_report(r):
    s = f"VERDICT={r['verdict']}"
    if 'reason' in r:
        s += f" ({r['reason']})"
    if 'differ_lines' in r:
        s += (f" lines {r['differ_lines']}/{r['lines']} differ (and {r['differ_lines_epanet']} of EPANET's), {r['differ_numbers']} numbers, largest "
              f"{g(r['max_abs'])} ({r['max_last_digit_units']} units of the last digit); mass balance: largest "
              f"{g(r['mb_max_rel'])} of the species' largest figure, ratio {g(r['mb_max_ratio_diff'])}")
    return s


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    msx = None
    if '--msx' in sys.argv:
        msx = sys.argv[sys.argv.index('--msx') + 1]
        args = [a for a in args if a != msx]
    if len(args) != 2:
        raise SystemExit(__doc__)
    if args[0].endswith('.dump'):
        if not msx:
            raise SystemExit('--msx FILE.msx is needed to compare dumps')
        r = compare_dumps(args[0], args[1], msx)
        if '--no-where' in sys.argv:
            for sp in r.get('species', []):
                sp.pop('maxabs_at', None)
                sp.pop('maxabs_ref', None)
        text = fmt_dump(r, '--no-where' not in sys.argv)
    else:
        r = compare_reports(args[0], args[1])
        text = fmt_report(r)
    print(json.dumps(r, indent=1) if '--json' in sys.argv else text)
    sys.exit(1 if r['verdict'].startswith('FAIL') else 0)
