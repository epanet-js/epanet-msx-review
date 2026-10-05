#!/bin/sh
# List the patches of a build, in the order they are applied. One path per line.
#
#   tools/patch-order.sh base          nothing
#   tools/patch-order.sh FIX-02        FIX-02 on its own (with any patch it names in Requires:)
#   tools/patch-order.sh fixes         FIX-01 to FIX-03
#   tools/patch-order.sh BIT-07        FIX-01 and FIX-02, which the bit-identical series
#                                      builds on, then BIT-01 to BIT-07
#   tools/patch-order.sh bit           FIX-01, FIX-02, BIT-01 to BIT-17
#   tools/patch-order.sh NEAR-02       bit, then NEAR-01 and NEAR-02
#   tools/patch-order.sh near          bit, then NEAR-01 to NEAR-03
#   tools/patch-order.sh only:NEAR-02  bit, then NEAR-02 alone
#   tools/patch-order.sh only:BIT-07   FIX-01, FIX-02, then BIT-07 alone (it may not apply)
#   tools/patch-order.sh all           every patch: FIX-01 to FIX-03, BIT-01 to BIT-17,
#                                      NEAR-01 to NEAR-03
#   tools/patch-order.sh bit+FIX-03    several names joined with "+": every patch they
#                                      name, in series order
#   tools/patch-order.sh near+my.patch a patch file of your own, applied last
#
# The series order is FIX-01 to FIX-03, BIT-01 to BIT-17, NEAR-01 to NEAR-03:
# the fixes first, then each bit-identical patch on top of the ones before it,
# then the near-identical patches, each of which applies on its own after the
# bit-identical series. A patch that needs one outside that order names it in
# its header (the text before the first "diff --git" line):
#   Requires: FIX-01
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
NAME=${1:?usage: patch-order.sh base|fixes|bit|near|all|ID|only:ID[+...]}

# Every patch of the series, in order
SERIES=$( (ls "$HERE"/3-bug-fixes/FIX-*/FIX-*.patch
           ls "$HERE"/1-bit-identical/BIT-*/BIT-*.patch
           ls "$HERE"/2-near-identical/NEAR-*/NEAR-*.patch) 2>/dev/null)
ids() { echo "$SERIES" | sed 's|.*/\([A-Z]*-[0-9]*\)\.patch$|\1|' | grep "^$1" || true; }
path_of() { echo "$SERIES" | grep "/$1\.patch\$" || true; }
requires() {
    awk '/^diff --git /{exit}
         /^Requires:/ { for (i = 2; i <= NF; i++) { gsub(",", "", $i); if ($i != "none") print $i } }' "$1"
}
upto() {   # the IDs of one category, from the first up to and including $2
    ids "$1" | awk -v last="$2" '{ print } $0 == last { exit }'
}
# The fixes the bit-identical series builds on: every Requires of a BIT patch
series_fixes() {
    for p in $(ids BIT-); do requires "$(path_of "$p")"; done | sort -u
}

# IDs (and patch files) named by one part of the name
part() {
    case "$1" in
        FIX-*|BIT-*|NEAR-*|only:*)
            [ -n "$(path_of "${1#only:}")" ] || { echo "No patch named ${1#only:}" >&2; exit 2; } ;;
    esac
    case "$1" in
        base) ;;
        fixes) ids FIX- ;;
        bit) series_fixes; ids BIT- ;;
        near) part bit; ids NEAR- ;;
        all) ids "" ;;
        only:BIT-*) series_fixes; echo "${1#only:}" ;;
        only:NEAR-*) part bit; echo "${1#only:}" ;;
        only:*) echo "${1#only:}" ;;
        FIX-*) echo "$1" ;;
        BIT-*) series_fixes; upto BIT- "$1" ;;
        NEAR-*) part bit; upto NEAR- "$1" ;;
        *.patch)
            [ -f "$1" ] || { echo "No patch file $1" >&2; exit 2; }
            echo "FILE:$(cd "$(dirname "$1")" && pwd)/$(basename "$1")" ;;
        *) echo "Unknown build name $1" >&2; exit 2 ;;
    esac
}

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
for p in $(echo "$NAME" | tr '+' ' '); do
    part "$p" >> "$TMP"
done
WANT=$(awk '!seen[$0]++' "$TMP")

# Add whatever the wanted patches require, until nothing changes
while :; do
    : > "$TMP"
    for id in $(echo "$WANT" | grep -v '^FILE:' || true); do
        p=$(path_of "$id")
        [ -n "$p" ] || { echo "No patch named $id" >&2; exit 2; }
        requires "$p" >> "$TMP"
    done
    NEW=$( (echo "$WANT"; cat "$TMP") | grep -v '^$' | awk '!seen[$0]++')
    [ "$NEW" = "$WANT" ] && break
    WANT=$NEW
done

# Series patches in series order, then patch files in the order given
for id in $(ids ""); do
    echo "$WANT" | grep -qx "$id" && path_of "$id"
done
echo "$WANT" | sed -n 's/^FILE://p' | awk '!seen[$0]++'
