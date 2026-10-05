#!/bin/sh
# Make every measurement in results/ again, then write the tables into the READMEs.
#
#   tools/run-all.sh                 every step (about 6 hours on an Apple M1 Pro)
#   tools/run-all.sh series near     only these steps
#   tools/run-all.sh --list          list the steps
#   SKIP_DONE=1 tools/run-all.sh     skip steps whose results are already in .build/results/
#   QUICK=1 tools/run-all.sh         one timed run per build instead of the best of 5 (or 3),
#                                    and no waiting for a quiet machine: about 2.5 hours,
#                                    noisier, enough to fill every table
#
# Steps run one after another, never two at once, and every build is compiled
# first, so that no compilation overlaps a timing run. Results are written to
# .build/results/ and copied to results/ at the end (private models: only an
# anonymous summary). Leave the machine as it is; each result records the load
# average at its start and end.
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd)
cd "$HERE"

SERIES=base,FIX-01,FIX-02,FIX-03
for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17; do SERIES="$SERIES,BIT-$i"; done
NEAR=bit,only:NEAR-01,only:NEAR-02,only:NEAR-03,near
SAMPLES=base,base@nofma,base@fmafast
if [ "$(uname)" = Darwin ]; then SAMPLES="$SAMPLES,base@x86"; else SAMPLES="$SAMPLES,base@clang,base@native"; fi
LIST() { echo "$1" | tr , ' '; }
R5=5; R3=3
[ "${QUICK:-0}" = 1 ] && { R5=1; R3=1; }

STEPS="builds series yardstick threads near output-groups headline-step headline-solve output-headline
       flavours scaling verify-solve verify-noomp real yardstick-real private"

step() {
    case "$1" in
    builds)    # compile everything the timing steps need, before any of them runs
        for b in $(LIST "$SERIES") only:NEAR-01 only:NEAR-02 only:NEAR-03 bit near \
                 base@O0 base@noomp bit@noomp near@noomp $(LIST "$SAMPLES"); do
            tools/build-msx.sh "$b" > /dev/null || return 1
        done
        for b in $(LIST "$SERIES") only:NEAR-01 only:NEAR-02 only:NEAR-03; do
            tools/build-msx.sh "$b@noomp" > /dev/null || return 1
        done ;;
    series)    # each group against the series before it: 1 and 8 threads, step mode, best of 5
        tools/bench.py --builds "$SERIES" --threads 1,8 --reps $R5 --tag series ;;
    near)      # each near-identical change alone on bit, and all of them
        tools/bench.py --builds "$NEAR" --threads 1,8 --reps $R5 --tag near-series ;;
    output-groups)   # the output groups on the output-heavy cases
        tools/bench.py --builds base,BIT-13,BIT-14,BIT-15,BIT-16 --cases output --modes solve,read \
            --threads 1,8 --reps $R5 --tag output-groups ;;
    headline-step)
        tools/bench.py --builds base,bit,near --threads 1,8,default --reps $R5 --tag headline-step ;;
    headline-solve)
        tools/bench.py --builds base,bit,near --modes solve --threads 1,8,default --reps $R5 --tag headline-solve ;;
    output-headline)
        tools/bench.py --builds base,bit,near --cases output --modes solve,read --threads 1,8 --reps $R5 \
            --tag output-headline ;;
    flavours)  # build options: no optimisation (BIT-01), no OpenMP
        tools/bench.py --builds base,base@O0,base@noomp,bit@noomp,bit,near@noomp,near --threads 1 --reps $R3 \
            --tag flavours ;;
    scaling)
        tools/bench.py --builds base,bit,near --threads 1,2,4,6,8,10 --reps $R3 --tag scaling ;;
    verify-solve)    # result checks not covered by the timing runs (one checked run each)
        tools/bench.py --builds "$SERIES,$NEAR" --cases main,output --modes solve --threads 1,8 --reps 0 \
            --tag verify-solve &&
        tools/bench.py --builds "$SERIES,$NEAR" --cases output --modes step,read --threads 1,8 --reps 0 \
            --tag verify-output ;;
    verify-noomp)    # every build without OpenMP, against base with OpenMP
        B=base
        for b in $(LIST "$SERIES") only:NEAR-01 only:NEAR-02 only:NEAR-03 near; do B="$B,$b@noomp"; done
        tools/bench.py --builds "$B" --cases main,output --modes step --threads 1 --reps 0 --tag verify-noomp ;;
    yardstick) # near-identical changes: each alone, and all of them, against the platform samples
        tools/yardstick.py run --builds "$SAMPLES,bit@conv,only:NEAR-01,only:NEAR-02,only:NEAR-03,near" \
            --cases main,output --tag yardstick --jobs 4 ;;
    threads)   # same bits at 1, 8 and 10 threads and without OpenMP
        tools/yardstick.py threads --builds only:NEAR-01,only:NEAR-02,only:NEAR-03,near,bit \
            --cases main,output --tag threads ;;
    real)      # the larger public networks: one checked run each
        tools/bench.py --builds base,bit,near --cases real --threads 1,8 --reps 0 --tag real ;;
    yardstick-real)
        tools/yardstick.py run --builds "$SAMPLES,bit@conv,only:NEAR-01,only:NEAR-02,only:NEAR-03,near" \
            --cases real --tag yardstick-real --jobs 4 --dumpevery 6 ;;
    private)   # your own models in models/private/, if there are any
        if ls models/private/*.inp > /dev/null 2>&1; then
            tools/bench.py --builds base,bit,near --cases private --threads 1,8 --reps 0 \
                --private-label "Utility model" --tag private &&
            tools/private-summary.py .build/results/private.json > .build/results/private-summary.json
        else
            echo "No models in models/private/: skipped"
        fi ;;
    *) echo "Unknown step $1" >&2; return 2 ;;
    esac
}

# Wait, up to QUIET_WAIT minutes (default 30), for the one-minute load average to fall
# below QUIET_LOAD (default: the number of cores). Nothing is closed or stopped; the wait
# only avoids starting a timing run in the middle of someone else's burst of work.
quiet() {
    limit=${QUIET_LOAD:-$(python3 -c 'import os; print(os.cpu_count())')}
    waited=0
    while [ "$waited" -lt "$(( ${QUIET_WAIT:-30} * 60 ))" ]; do
        load=$(python3 -c 'import os; print(int(os.getloadavg()[0]))')
        [ "$load" -lt "$limit" ] && break
        sleep 30; waited=$((waited + 30))
    done
    [ "$waited" -gt 0 ] && echo "   (waited $((waited / 60)) min for the load average to fall below $limit)"
    return 0
}

if [ "${1:-}" = "--list" ]; then echo $STEPS; exit 0; fi
[ $# -gt 0 ] && STEPS="$*"
mkdir -p .build/results
FAILED=""
for s in $STEPS; do
    case "$s" in
        builds|series|near|output-groups|headline-step|headline-solve|output-headline|flavours|scaling|real|private)
            tag=$s; [ "$s" = near ] && tag=near-series ;;
        verify-solve) tag=verify-output ;;
        *) tag=$s ;;
    esac
    if [ "${SKIP_DONE:-0}" = 1 ] && [ -f ".build/results/$tag.json" ]; then
        echo "== $s: done before, skipped"
        continue
    fi
    [ "$s" = builds ] || [ "${QUICK:-0}" = 1 ] || quiet
    echo "== $s: started $(date '+%Y-%m-%d %H:%M'), load $(uptime | sed 's/.*load averages*: //')"
    if step "$s"; then
        echo "== $s: finished $(date '+%Y-%m-%d %H:%M')"
    else
        echo "== $s: FAILED $(date '+%Y-%m-%d %H:%M')"
        FAILED="$FAILED $s"
    fi
done

# Copy what was measured to results/, and write the tables into the READMEs
mkdir -p results
for t in series near-series output-groups headline-step headline-solve output-headline flavours scaling \
         verify-solve verify-output verify-noomp yardstick threads real yardstick-real; do
    for f in .build/results/$t.json .build/results/$t.md; do [ -f "$f" ] && cp "$f" results/; done
done
[ -f .build/results/private-summary.json ] && cp .build/results/private-summary.json results/private.json
tools/update-docs.py || FAILED="$FAILED update-docs"
if [ -n "$FAILED" ]; then echo "Failed:$FAILED" >&2; exit 1; fi
