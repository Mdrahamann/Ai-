#!/usr/bin/env bash
# Re-runnable pipeline. Order: voices+sound -> timeline (real clips only) -> quality check.
# Usage: KOKORO_DIR=/path/to/kokoro ./run.sh [--subtitles]
set -euo pipefail
cd "$(dirname "$0")"
python3 audio.py
python3 timeline.py "$@"
OUT=../final/the_wrong_delivery_pilot.mp4
if [ -f "$OUT" ]; then python3 qc.py final "$OUT"; else echo "No final file (see messages above)."; exit 1; fi
