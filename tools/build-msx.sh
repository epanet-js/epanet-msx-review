#!/bin/sh
# Build EPANET-MSX and EPANET 2.2, with or without patches, and print the build folder.
#
#   tools/build-msx.sh base           unpatched MSX 85a303d     -> .build/85a303d/base
#   tools/build-msx.sh BIT-07         FIX-01, FIX-02, BIT-01 to BIT-07
#   tools/build-msx.sh bit|near|all   (any name tools/patch-order.sh knows, including
#                                     only:NEAR-02, FIX-02, bit+FIX-03, near+my.patch)
#   tools/build-msx.sh dev:bit        the same patches on another MSX version: SOURCE:NAME,
#                                     SOURCE a commit, tag, branch (origin/<branch>) or
#                                     pull/<number>    -> .build/<commit>/bit
#   tools/build-msx.sh dev:base       that version as it is
#   MSX_TREE=~/src/msx tools/build-msx.sh base
#                                     a local MSX source directory, as it is on disk
#                                     (src/ and CMakeLists.txt; EPANET from its EPANET2.2/
#                                     folder) -> .build/local-<dir>-<checksum>/base
#   tools/build-msx.sh bit@noomp      the same source built another way:
#       @noomp    without OpenMP (as when CMake finds no OpenMP)
#       @O0       no optimisation, as a plain "cmake -B build ." with the Makefile
#                 generator builds it (see BIT-01)
#       @nofma    -ffp-contract=off: no fused multiply-add, as x86-64 and MSVC /fp:precise
#       @fmafast  -ffp-contract=fast: fused multiply-add across statements, GCC's
#                 default on 64-bit ARM Linux
#       @x86      macOS only: built for x86-64 and run under Rosetta, without OpenMP
#                 (Homebrew's libomp is arm64 only; results do not depend on threads)
#       @clang    Linux: built with clang instead of the default compiler
#       @native   built for this processor (-march=native, or -mcpu=native on arm64)
#       @conv     the converged reference: tools/converged.patch applied after the
#                 series (tighter integrator and Newton tolerances, Euler replaced by
#                 RK5); for measuring how far results are from converged only
#       @asan     AddressSanitizer and UndefinedBehaviorSanitizer, -O1 -g, with OpenMP
#
# The build folder holds libepanet2 and libepanetmsx (shared libraries, as the
# project's CMake build makes by default), the benchmark driver bench (from
# tools/bench.c), runepanetmsx, and patches.txt, which records what happened to
# each patch: applied, applied (3-way merge), already in MSX, or does not apply.
#
# Sources are exported with git archive, so no checkout is ever changed. MSX and
# EPANET 2.2 are compiled with $CC (default cc) and $CFLAGS (default -O3 -DNDEBUG,
# CMake's Release flags), with OpenMP (-fopenmp; on macOS Homebrew's libomp, or
# $LIBOMP). A patch that does not apply as it stands is merged three ways, as git
# would rebase it; the objects it needs come from replaying the whole series on
# 85a303d once, in .build/objects/. The series stops at the first patch that does
# not apply, unless PARTIAL=1 is set: then the build keeps the patches before it.
# A fix (FIX-NN) that does not apply and that no other patch requires is skipped.
# APPLY_ONLY=1 stops after applying the patches (patches.txt), without compiling.
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
SPEC=${1:?usage: build-msx.sh [SOURCE:]NAME[@FLAVOUR]}
BUILD_VERSION=3            # bump when the compile steps below change
MEASURED=85a303dca05859389eced63fabd5ea145c096333
CC=${CC:-cc}
BASEFLAGS=${CFLAGS:--O3 -DNDEBUG}

# Split SOURCE:NAME@FLAVOUR (only:ID is a name, not a source)
FLAVOUR=""
case "$SPEC" in *@*) FLAVOUR=${SPEC##*@}; SPEC=${SPEC%@*} ;; esac
SOURCE=""
case "$SPEC" in
    only:*) NAME=$SPEC ;;
    *:*) SOURCE=${SPEC%%:*}; NAME=${SPEC#*:} ;;
    *) NAME=$SPEC ;;
esac
[ -n "$SOURCE" ] && export MSX_COMMIT="$SOURCE"

OS=$(uname)
if [ "$OS" = Darwin ]; then
    LIBOMP=${LIBOMP:-$(brew --prefix libomp 2>/dev/null || echo /opt/homebrew/opt/libomp)}
    OMPFLAGS="-Xpreprocessor -fopenmp -DUSE_OPENMP -I$LIBOMP/include"
    OMPLIB="-L$LIBOMP/lib -lomp -Wl,-rpath,$LIBOMP/lib"
else
    OMPFLAGS="-fopenmp -DUSE_OPENMP"; OMPLIB="-fopenmp"
fi
ARCH=""; EXTRA=""; SANITIZE=""
case "$FLAVOUR" in
    "")      ;;
    noomp)   OMPFLAGS=""; OMPLIB="" ;;
    O0)      BASEFLAGS="-O0" ;;
    nofma)   BASEFLAGS="$BASEFLAGS -ffp-contract=off" ;;
    fmafast) BASEFLAGS="$BASEFLAGS -ffp-contract=fast" ;;
    x86)     [ "$OS" = Darwin ] || { echo "@x86 needs macOS with Rosetta" >&2; exit 2; }
             ARCH="-arch x86_64"; OMPFLAGS=""; OMPLIB="" ;;
    clang)   CC=clang ;;
    native)  if [ "$(uname -m)" = arm64 ] || [ "$(uname -m)" = aarch64 ]; then
                 BASEFLAGS="$BASEFLAGS -mcpu=native"
             else
                 BASEFLAGS="$BASEFLAGS -march=native"
             fi ;;
    conv)    EXTRA=$HERE/tools/converged.patch ;;
    asan)    SANITIZE="-fsanitize=address,undefined -fno-sanitize-recover=undefined"
             BASEFLAGS="-O1 -g -fno-omit-frame-pointer $SANITIZE" ;;
    *)       echo "Unknown build flavour @$FLAVOUR" >&2; exit 2 ;;
esac

# Paths may contain spaces, so lists of files are split on newlines only
NL='
'
PATCHES=$("$HERE/tools/patch-order.sh" "$NAME")
[ -n "$EXTRA" ] && PATCHES=$(printf '%s\n%s' "$PATCHES" "$EXTRA" | grep -v '^$')
IFS=$NL

# --- where the sources come from
if [ -n "${MSX_TREE:-}" ]; then
    TREE=$(cd "$MSX_TREE" && pwd)
    [ -d "$TREE/src/solver" ] || { echo "$TREE has no src/solver: not an EPANET-MSX source tree" >&2; exit 2; }
    SUM=$( (cd "$TREE" && find src CMakeLists.txt EPANET2.2/SRC_engines -type f 2>/dev/null | LC_ALL=C sort |
            while IFS= read -r f; do echo "$f"; cat "$f"; done) | cksum | awk '{ printf "%07x", $1 % 268435456 }')
    COMMIT="local $TREE $SUM"
    KEY=local-$(basename "$TREE")-$SUM
    EPSRC=$(dirname "$("$HERE/tools/get-msx.sh")")/msx/EPANET2.2
    if [ -d "$TREE/EPANET2.2/SRC_engines" ]; then EPCOMMIT="local"; else EPCOMMIT=$("$HERE/tools/get-msx.sh" --epanet); fi
else
    SRC=$("$HERE/tools/get-msx.sh")
    COMMIT=$("$HERE/tools/get-msx.sh" --commit)
    EPCOMMIT=$("$HERE/tools/get-msx.sh" --epanet)
    EPSRC=$("$HERE/tools/get-msx.sh" --epanet-src)
    KEY=$(echo "$COMMIT" | cut -c1-7)
fi
OUT=$HERE/.build/$KEY/$(echo "$NAME" | tr ':/+' '--+')${FLAVOUR:+@$FLAVOUR}
# Long +-joined names (with patch files) are shortened to a checksum
case "$NAME" in *.patch*) OUT=$HERE/.build/$KEY/custom-$(echo "$NAME$FLAVOUR" | cksum | cut -d' ' -f1)${FLAVOUR:+@$FLAVOUR} ;; esac

# --- skip the build if nothing has changed since the last one. Only the diff
#     part of each patch counts, so editing a patch's description does not rebuild.
CCVER=$($CC --version 2>/dev/null | head -1)
STAMP=$( (echo "$BUILD_VERSION $COMMIT $EPCOMMIT $CC $CCVER $BASEFLAGS $ARCH $OMPFLAGS"
          cat "$HERE/tools/bench.c"
          for p in $PATCHES; do sed -n '/^diff --git /,$p' "$p"; done) | cksum)
if [ "${APPLY_ONLY:-0}" = 1 ]; then
    OUT=$OUT.apply-only
elif [ -f "$OUT/stamp" ] && [ "$(cat "$OUT/stamp")" = "$STAMP" ] &&
   { [ "${PARTIAL:-0}" = 1 ] || ! grep -q "does not apply$" "$OUT/patches.txt"; }; then
    echo "$OUT"
    exit 0
fi

# One build of a given name at a time
mkdir -p "$(dirname "$OUT")"
while ! mkdir "$OUT.lock" 2>/dev/null; do sleep 1; done
trap 'rmdir "$OUT.lock" 2>/dev/null || true' EXIT
if [ -f "$OUT/stamp" ] && [ "$(cat "$OUT/stamp")" = "$STAMP" ]; then echo "$OUT"; exit 0; fi

echo "Building MSX ($SPEC${FLAVOUR:+@$FLAVOUR}) in $OUT ..." >&2
rm -rf "$OUT"
mkdir -p "$OUT/src" "$OUT/epanet" "$OUT/obj"
if [ -n "${MSX_TREE:-}" ]; then
    (cd "$TREE" && tar -cf - src CMakeLists.txt) | tar -x -C "$OUT/src"
    if [ "$EPCOMMIT" = local ]; then
        (cd "$TREE/EPANET2.2" && tar -cf - SRC_engines) | tar -x -C "$OUT/epanet"
    else
        git -C "$EPSRC" archive "$EPCOMMIT" SRC_engines | tar -x -C "$OUT/epanet"
    fi
    MSXOBJ=$(cd "$HERE/msx" && cd "$(git rev-parse --git-common-dir)" && pwd)/objects
else
    git -C "$SRC" archive "$COMMIT" src CMakeLists.txt | tar -x -C "$OUT/src"
    git -C "$EPSRC" archive "$EPCOMMIT" SRC_engines | tar -x -C "$OUT/epanet"
    MSXOBJ=$(cd "$SRC" && cd "$(git rev-parse --git-common-dir)" && pwd)/objects
fi
EPOBJ=$(cd "$EPSRC" && cd "$(git rev-parse --git-common-dir)" && pwd)/objects

# Each exported tree is made a git repository whose objects come from the
# source clone, so that a patch that no longer applies as it stands can still
# be merged three ways (git apply --3way)
g() {   # g TREE git-args...: the ceiling stops git from finding an enclosing repository
    _g=$1; shift
    (cd "$_g" && GIT_CEILING_DIRECTORIES=$(dirname "$_g") git -c user.name=build -c user.email=build@localhost "$@")
}
for t in "$OUT/src" "$OUT/epanet"; do
    g "$t" init -q
    case "$t" in */src) echo "$MSXOBJ" ;; *) echo "$EPOBJ" ;; esac > "$t/.git/objects/info/alternates"
    g "$t" add -A
    g "$t" commit -qm "source"
done

# The objects a three-way merge needs: the series replayed on 85a303d, one
# commit per patch, so that every patch's preimage blobs exist
seed_objects() {
    S=$HERE/.build/objects
    SEEDSTAMP=$( (ls "$HERE"/3-bug-fixes/FIX-*/*.patch "$HERE"/1-bit-identical/BIT-*/*.patch \
                     "$HERE"/2-near-identical/NEAR-*/*.patch | while IFS= read -r p; do sed -n '/^diff --git /,$p' "$p"; done) | cksum)
    if [ ! -f "$S/stamp" ] || [ "$(cat "$S/stamp")" != "$SEEDSTAMP" ]; then
        echo "Replaying the series on 85a303d for three-way merges ..." >&2
        MSRC=$("$HERE/tools/get-msx.sh")
        MEP=$(git -C "$MSRC" ls-tree "$MEASURED" EPANET2.2 | awk '{ print $3 }')
        rm -rf "$S"; mkdir -p "$S/msx" "$S/epanet"
        git -C "$MSRC" archive "$MEASURED" src CMakeLists.txt | tar -x -C "$S/msx"
        git -C "$MSRC/EPANET2.2" archive "$MEP" SRC_engines | tar -x -C "$S/epanet"
        for st in "$S/msx" "$S/epanet"; do g "$st" init -q; g "$st" add -A; g "$st" commit -qm base; done
        for sp in $("$HERE/tools/patch-order.sh" all); do
            st=$S/msx; grep -q '^diff --git a/SRC_engines/' "$sp" && st=$S/epanet
            g "$st" apply --index --whitespace=nowarn "$sp" && g "$st" commit -qm "$(basename "$sp" .patch)"
        done
        echo "$SEEDSTAMP" > "$S/stamp"
    fi
    for pair in "$OUT/src:$S/msx" "$OUT/epanet:$S/epanet"; do
        tree=${pair%%:*}; seed=${pair#*:}
        grep -qx "$seed/.git/objects" "$tree/.git/objects/info/alternates" ||
            echo "$seed/.git/objects" >> "$tree/.git/objects/info/alternates"
    done
}

# Every Requires: of the patches in this build, to know which fixes can be skipped
REQUIRED=$(for p in $PATCHES; do awk '/^diff --git /{exit} /^Requires:/ { for (i = 2; i <= NF; i++) print $i }' "$p"; done)

: > "$OUT/patches.txt"
STOPPED=""
for p in $PATCHES; do
    id=$(basename "$p" .patch)
    t=$OUT/src
    grep -q '^diff --git a/SRC_engines/' "$p" && t=$OUT/epanet
    if [ -n "$STOPPED" ]; then
        state="not applied (series stopped at $STOPPED)"
    elif g "$t" apply --check "$p" 2>/dev/null; then
        g "$t" apply --index --whitespace=nowarn "$p"
        state=applied
    elif g "$t" apply --check --reverse "$p" 2>/dev/null; then
        state="already in MSX"
    elif seed_objects && g "$t" apply --3way --whitespace=nowarn "$p" > /dev/null 2>&1; then
        state="applied (3-way merge)"
    else
        g "$t" reset -q --hard
        case "$id" in
            FIX-*) if ! echo "$REQUIRED" | grep -qx "$id"; then
                       echo "$id does not apply (a fix; skipped)" >> "$OUT/patches.txt"
                       continue
                   fi ;;
        esac
        state="does not apply"
        if [ "${PARTIAL:-0}" != 1 ]; then
            echo "$id $state" >> "$OUT/patches.txt"
            echo "Patch $id does not apply to EPANET-MSX $(echo "$COMMIT" | cut -c1-7)." >&2
            echo "Set PARTIAL=1 to build the patches before it." >&2
            exit 3
        fi
        STOPPED=$id
    fi
    case "$state" in applied*) g "$t" commit -qm "$id" ;; esac
    echo "$id $state" >> "$OUT/patches.txt"
done
unset IFS
if [ "${APPLY_ONLY:-0}" = 1 ]; then echo "$OUT"; exit 0; fi

# --- compile
EP=$OUT/epanet/SRC_engines
MS=$OUT/src/src/solver
if [ "$OS" = Darwin ]; then SO=dylib; SHARED="-dynamiclib -install_name @rpath/"; else SO=so; SHARED="-shared -Wl,-soname,"; fi
LOG=$OUT/build.log
: > "$LOG"
fail() { tail -30 "$LOG" >&2; echo "Build of $SPEC failed (see $LOG)" >&2; exit 5; }

# EPANET 2.2, with the same flags. CMake generates epanet2_export.h; this is what
# it generates for macOS and Linux.
printf '#ifndef DLLEXPORT\n#define DLLEXPORT __attribute__((visibility("default")))\n#endif\n' > "$OUT/obj/epanet2_export.h"
for f in "$EP"/src/solver/*.c; do
    o=$OUT/obj/ep_$(basename "$f" .c).o
    ($CC $BASEFLAGS $ARCH -fPIC -w -I"$OUT/obj" -I"$EP/include" -c "$f" -o "$o" > "$o.log" 2>&1 || touch "$OUT/failed") &
done
wait
for f in "$MS"/*.c; do
    o=$OUT/obj/msx_$(basename "$f" .c).o
    ($CC $BASEFLAGS $ARCH $OMPFLAGS -fPIC -w -I"$OUT/obj" -I"$MS/include" -I"$EP/include" -I"$MS" \
        -c "$f" -o "$o" > "$o.log" 2>&1 || touch "$OUT/failed") &
done
wait
cat "$OUT"/obj/*.log >> "$LOG" 2>/dev/null || true
[ -f "$OUT/failed" ] && fail
$CC $ARCH $SANITIZE ${SHARED}libepanet2.$SO -o "$OUT/libepanet2.$SO" "$OUT"/obj/ep_*.o -lm >> "$LOG" 2>&1 || fail
$CC $ARCH $SANITIZE ${SHARED}libepanetmsx.$SO -o "$OUT/libepanetmsx.$SO" "$OUT"/obj/msx_*.o \
    -L"$OUT" -lepanet2 $OMPLIB -lm >> "$LOG" 2>&1 || fail

# The drivers
INC="-I$OUT/obj -I$MS/include -I$EP/include"
$CC -O2 $ARCH $SANITIZE -w $INC "$HERE/tools/bench.c" -o "$OUT/bench" \
    -L"$OUT" -lepanetmsx -lepanet2 -Wl,-rpath,"$OUT" -lm >> "$LOG" 2>&1 || fail
$CC -O2 $ARCH $SANITIZE -w $INC "$OUT/src/src/run/msxmain.c" -o "$OUT/runepanetmsx" \
    -L"$OUT" -lepanetmsx -lepanet2 -Wl,-rpath,"$OUT" -lm >> "$LOG" 2>&1 || fail

cat > "$OUT/info.txt" <<EOF
msx $COMMIT
epanet $EPCOMMIT
cc $CC: $CCVER
cflags $BASEFLAGS $ARCH $OMPFLAGS
EOF
echo "$STAMP" > "$OUT/stamp"
echo "$OUT"
