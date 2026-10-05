#!/bin/sh
# Find the EPANET-MSX source and commit that the other scripts build.
#
#   tools/get-msx.sh               print the path of the MSX git repository
#   tools/get-msx.sh --commit      print the MSX commit to build, as a full hash
#   tools/get-msx.sh --fetch       update the msx submodule from GitHub, then
#                                  print the commit to build
#   tools/get-msx.sh --epanet      print the EPANET 2.2 commit that this MSX
#                                  commit pins (its EPANET2.2 submodule)
#   tools/get-msx.sh --epanet-src  print the path of the EPANET 2.2 git repository
#
# The repository is the MSX clone in $MSX_SRC if it is set, otherwise the msx
# submodule, which is fetched the first time if this repository was cloned
# without --recurse-submodules.
#
# The commit is $MSX_COMMIT if it is set, otherwise 85a303d, the commit the
# patches were written against. It can be a commit, a tag, a branch such as dev
# (read from origin/dev, which --fetch updates) or pull/<number> for a pull
# request. EPANET 2.2 is always taken at the commit the MSX commit pins.
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
MEASURED=85a303dca05859389eced63fabd5ea145c096333
REF=${MSX_COMMIT:-$MEASURED}
MODE=${1:-}

if [ -n "${MSX_SRC:-}" ]; then
    SRC=$MSX_SRC
else
    SRC=$HERE/msx
    if [ ! -e "$SRC/.git" ]; then
        echo "Fetching the msx submodule ..." >&2
        git -C "$HERE" submodule update --init --recursive msx >&2 || true
    fi
fi

if [ ! -e "$SRC/.git" ] && [ ! -d "$SRC/objects" ]; then
    echo "No EPANET-MSX git repository at $SRC." >&2
    echo "Run 'git submodule update --init --recursive', or set MSX_SRC to an EPANET-MSX clone." >&2
    exit 2
fi

if [ -z "$MODE" ]; then
    echo "$SRC"
    exit 0
fi

if [ "$MODE" = "--fetch" ]; then
    if [ -n "${MSX_SRC:-}" ]; then
        echo "Using $SRC as it is; fetch there to update it." >&2
    else
        echo "Updating the msx submodule from GitHub ..." >&2
        git -C "$SRC" fetch -q origin
        case "$REF" in
            pull/*) git -C "$SRC" fetch -q origin "+refs/$REF/head:refs/remotes/origin/$REF" ;;
        esac
    fi
fi

# A branch name means the branch on GitHub (origin/<name>), not a local copy
# that may be out of date
SHA=$(git -C "$SRC" rev-parse -q --verify "refs/remotes/origin/$REF^{commit}" 2>/dev/null ||
      git -C "$SRC" rev-parse -q --verify "$REF^{commit}" 2>/dev/null) || {
    echo "EPANET-MSX commit '$REF' was not found in $SRC." >&2
    if [ -z "${MSX_SRC:-}" ]; then
        echo "Download it with: MSX_COMMIT=$REF tools/get-msx.sh --fetch" >&2
    fi
    exit 2
}

case "$MODE" in
    --commit|--fetch)
        echo "$SHA" ;;
    --epanet|--epanet-src)
        EPSRC=$SRC/EPANET2.2
        if [ ! -e "$EPSRC/.git" ]; then
            git -C "$SRC" submodule update --init EPANET2.2 >&2 || true
        fi
        if [ "$MODE" = "--epanet-src" ]; then
            echo "$EPSRC"
            exit 0
        fi
        PIN=$(git -C "$SRC" ls-tree "$SHA" EPANET2.2 | awk '{ print $3 }')
        if [ -z "$PIN" ]; then
            echo "EPANET-MSX $SHA has no EPANET2.2 submodule." >&2
            exit 2
        fi
        if ! git -C "$EPSRC" cat-file -e "$PIN^{commit}" 2>/dev/null; then
            echo "Fetching EPANET 2.2 $PIN ..." >&2
            git -C "$EPSRC" fetch -q origin >&2 || true
        fi
        git -C "$EPSRC" cat-file -e "$PIN^{commit}" || {
            echo "EPANET 2.2 commit $PIN (pinned by EPANET-MSX $SHA) was not found in $EPSRC." >&2
            exit 2
        }
        echo "$PIN" ;;
    *)
        echo "usage: get-msx.sh [--commit|--fetch|--epanet|--epanet-src]" >&2
        exit 2 ;;
esac
