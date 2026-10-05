#!/bin/sh
# Edit a patch in a clean copy of the source, then write it back.
#
#   tools/patch-workspace.sh BIT-07          create .build/edit/BIT-07 (a git repository
#                                            holding MSX 85a303d's src/ and CMakeLists.txt
#                                            and EPANET2.2/SRC_engines/, with the patches
#                                            before BIT-07 in its build committed and
#                                            BIT-07's own change applied on top) and
#                                            print its path
#   tools/patch-workspace.sh BIT-07 save     write the workspace's changes back to
#                                            BIT-07.patch, keeping the patch's header
#   tools/patch-workspace.sh my-idea --on bit
#                                            a workspace for a new patch, on top of any
#                                            build (bit, near, BIT-07, ...)
#   tools/patch-workspace.sh my-idea save    write it to .build/edit/my-idea.patch; try it
#                                            with tools/try.py bit+.build/edit/my-idea.patch
#
# The workspace is made once; delete .build/edit/<NAME> to start again. Changes to
# EPANET2.2/ are written as a patch to the EPANET2.2 submodule (paths starting with
# SRC_engines/), like BIT-16; a patch holds changes to one of the two only.
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
NAME=${1:?usage: patch-workspace.sh ID|NAME [save | --on BUILD]}
SRC=$("$HERE/tools/get-msx.sh")
COMMIT=85a303dca05859389eced63fabd5ea145c096333
EPCOMMIT=$(git -C "$SRC" ls-tree "$COMMIT" EPANET2.2 | awk '{ print $3 }')
WS=$HERE/.build/edit/$NAME

PATCH=$(ls "$HERE"/[123]-*/"$NAME"-*/"$NAME".patch 2>/dev/null | head -1 || true)
[ -n "$PATCH" ] || PATCH=$HERE/.build/edit/$NAME.patch
g() { (cd "$WS" && GIT_CEILING_DIRECTORIES=$(dirname "$WS") git -c user.name=edit -c user.email=edit@localhost "$@"); }
is_epanet() { grep -q '^diff --git a/SRC_engines/' "$1"; }

if [ "${2:-}" = "save" ]; then
    [ -d "$WS/.git" ] || { echo "No workspace $WS" >&2; exit 2; }
    HEADER=$(mktemp)
    if [ -f "$PATCH" ]; then
        # Everything before the first "diff --git" line is the description
        awk '/^diff --git /{exit} {print}' "$PATCH" > "$HEADER"
    else
        printf '%s: (describe the change)\n\nRequires: none\nResults: identical\n\n' "$NAME" > "$HEADER"
    fi
    g add -A
    if [ -n "$(g diff --cached --name-only -- EPANET2.2)" ]; then
        if [ -n "$(g diff --cached --name-only -- src CMakeLists.txt)" ]; then
            echo "The workspace changes both MSX and EPANET2.2: keep one patch to each" >&2
            exit 2
        fi
        BODY=$(g diff --cached --no-color --no-ext-diff --relative=EPANET2.2)
    else
        BODY=$(g diff --cached --no-color --no-ext-diff)
    fi
    { cat "$HEADER"; echo "$BODY"; } > "$PATCH.tmp"
    mv "$PATCH.tmp" "$PATCH"
    rm -f "$HEADER"
    echo "$PATCH"
    exit 0
fi

if [ ! -d "$WS/.git" ]; then
    if [ "${2:-}" = "--on" ]; then
        BEFORE=$("$HERE/tools/patch-order.sh" "${3:?usage: patch-workspace.sh NAME --on BUILD}")
        OWN=""
    elif [ -f "$PATCH" ] && [ "$PATCH" != "$HERE/.build/edit/$NAME.patch" ]; then
        # The patches of its build, without itself
        BEFORE=$("$HERE/tools/patch-order.sh" "$NAME" | grep -v "/$NAME\.patch\$" || true)
        OWN=$PATCH
    else
        echo "No patch named $NAME; for a new one, give a build to start from: --on bit" >&2
        exit 2
    fi
    mkdir -p "$WS/EPANET2.2"
    git -C "$SRC" archive "$COMMIT" src CMakeLists.txt | tar -x -C "$WS"
    git -C "$SRC/EPANET2.2" archive "$EPCOMMIT" SRC_engines | tar -x -C "$WS/EPANET2.2"
    g init -q
    g add -A
    g commit -q -m "EPANET-MSX 85a303d, EPANET 2.2 $(echo "$EPCOMMIT" | cut -c1-7)"
    NL='
'
    IFS=$NL
    for p in $BEFORE; do
        if is_epanet "$p"; then g apply --whitespace=nowarn --directory=EPANET2.2 "$p"; else g apply --whitespace=nowarn "$p"; fi
    done
    unset IFS
    if [ -n "$(g status --porcelain)" ]; then
        g add -A
        g commit -q -m "the patches before $NAME"
    fi
    if [ -n "$OWN" ] && grep -q '^diff --git ' "$OWN"; then
        if is_epanet "$OWN"; then g apply --whitespace=nowarn --directory=EPANET2.2 "$OWN"; else g apply --whitespace=nowarn "$OWN"; fi
    fi
fi
echo "$WS"
