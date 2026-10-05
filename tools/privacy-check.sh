#!/bin/sh
# Fail if any file tracked by git, or any commit message, names a private model.
#
#   tools/privacy-check.sh            check every tracked file and commit message
#   tools/privacy-check.sh --staged   also check the commit message in .git/COMMIT_EDITMSG
#
# The patterns come from the files in models/private/ (which git ignores): each
# file's name without its extension, and the first word of that name (split at
# "-", "_", "." or a space), ignoring words under four letters and a few generic
# ones. Put a file models/private/.patterns (one word per line) to add more,
# such as a utility's name or node IDs. Run it before every commit.
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
cd "$HERE"
PAT=$(mktemp)
trap 'rm -f "$PAT" "$PAT.hits"' EXIT

find models/private -type f ! -name README.md ! -name .gitignore ! -name .patterns |
while IFS= read -r f; do
    b=$(basename "$f"); stem=${b%.*}
    echo "$stem"
    echo "$stem" | sed 's/[-_. ].*//'
done | awk 'length($0) >= 4' |
grep -v -i -x -E 'model|models|network|private|cases|test|tests|chlorine|chloramine|bacteria|arsenic|example|utility' |
sort -u > "$PAT"
if [ -f models/private/.patterns ]; then grep -v '^ *$' models/private/.patterns >> "$PAT" || true; fi

if [ ! -s "$PAT" ]; then
    echo "privacy-check: no private models in models/private/, nothing to check"
    exit 0
fi

# Tracked files, without the submodule (mode 160000), searched case-insensitively
git ls-files -s | awk '$1 != "160000" { sub(/^[^\t]*\t/, ""); print }' |
    tr '\n' '\0' | xargs -0 grep -I -i -n -F -f "$PAT" -- > "$PAT.hits" 2>/dev/null || true
git log --all --format='commit %h: %B' 2>/dev/null | grep -i -F -f "$PAT" >> "$PAT.hits" || true
if [ "${1:-}" = "--staged" ] && [ -f .git/COMMIT_EDITMSG ]; then
    grep -i -F -f "$PAT" .git/COMMIT_EDITMSG | sed 's/^/COMMIT_EDITMSG: /' >> "$PAT.hits" || true
fi
if [ -s "$PAT.hits" ]; then
    echo "privacy-check: FAILED. These lines name a private model:" >&2
    # show where, not the words themselves
    cut -d: -f1-2 "$PAT.hits" | sort -u >&2
    exit 1
fi
echo "privacy-check: OK ($(wc -l < "$PAT" | tr -d ' ') patterns, $(git ls-files | wc -l | tr -d ' ') tracked files)"
