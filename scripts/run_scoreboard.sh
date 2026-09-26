#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m must_cite_rlm.scoreboard "$@"
