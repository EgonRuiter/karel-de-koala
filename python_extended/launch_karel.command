#!/usr/bin/env bash
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$DIR/karel.py"
[ -f "$SCRIPT" ] || SCRIPT="$DIR/desktop/karel.py"

if [ ! -f "$SCRIPT" ]; then
    echo "Fout: karel.py niet gevonden naast launch_karel.command."
    [ -t 0 ] && read -rp "Druk op Enter om te sluiten..."
    exit 1
fi

IS_MAC=0
[ "$(uname -s 2>/dev/null || true)" = "Darwin" ] && IS_MAC=1

if [ "$IS_MAC" -eq 1 ] && command -v xattr >/dev/null 2>&1; then
    xattr -dr com.apple.quarantine "$DIR" >/dev/null 2>&1 || true
fi

CANDS=()
if [ -x "/Library/Frameworks/Python.framework/Versions/Current/bin/python3" ]; then
    CANDS+=("/Library/Frameworks/Python.framework/Versions/Current/bin/python3")
fi
for P in /Library/Frameworks/Python.framework/Versions/3.*/bin/python3; do
    [ -x "$P" ] && CANDS+=("$P")
done
for P in \
    "/opt/homebrew/bin/python3" \
    /opt/homebrew/opt/python@3.*/bin/python3* \
    "/usr/local/bin/python3" \
    /usr/local/opt/python@3.*/bin/python3* \
    "$HOME/.pyenv/shims/python3" \
    "$HOME/miniforge3/bin/python3" \
    "$HOME/miniconda3/bin/python3" \
    "$HOME/anaconda3/bin/python3" \
    "/opt/local/bin/python3"; do
    [ -x "$P" ] && CANDS+=("$P")
done
PATH_PY3="$(command -v python3 2>/dev/null || true)"
if [ -n "$PATH_PY3" ] && [ "$PATH_PY3" != "/usr/bin/python3" ]; then
    CANDS+=("$PATH_PY3")
fi
PATH_PY="$(command -v python 2>/dev/null || true)"
if [ -n "$PATH_PY" ] && [ "$PATH_PY" != "/usr/bin/python" ]; then
    CANDS+=("$PATH_PY")
fi
if [ "$IS_MAC" -eq 0 ] || xcode-select -p >/dev/null 2>&1; then
    [ -x "/usr/bin/python3" ] && CANDS+=("/usr/bin/python3")
fi

pick_python() {
    local min_tk="$1"
    local cand
    for cand in "${CANDS[@]}"; do
        [ -n "$cand" ] && [ -x "$cand" ] || continue
        if "$cand" -c "import sys, tkinter; assert sys.version_info[0] >= 3 and float(getattr(tkinter, 'TkVersion', 0)) >= $min_tk" >/dev/null 2>&1; then
            printf '%s\n' "$cand"
            return 0
        fi
    done
    return 1
}

PY="$(pick_python 8.6 || true)"
[ -n "$PY" ] || PY="$(pick_python 0 || true)"

if [ -z "$PY" ]; then
    HINT="Installeer Python van python.org (aanbevolen op macOS) of via: brew install python-tk"
    if [ -x "/opt/homebrew/bin/python3" ] || [ -x "/usr/local/bin/python3" ]; then
        HINT="Homebrew Python gevonden zonder Tkinter! Run in Terminal:\n\nbrew install python-tk\n\nOf download Python van python.org."
    fi
    MSG="Karel de Koala kon geen Python 3 met Tkinter vinden.\n$HINT\nUbuntu/Debian: sudo apt install python3-tk"
    printf '%b\n' "$MSG"
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display dialog \"Karel de Koala heeft Python 3 met Tkinter nodig.\n\n$HINT\" buttons {\"OK\"} default button 1 with title \"Karel de Koala\"" >/dev/null 2>&1 || true
    elif command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Karel de Koala" --text="$MSG" >/dev/null 2>&1 || true
    fi
    [ -t 0 ] && read -rp "Druk op Enter om te sluiten..."
    exit 1
fi

LOG="${TMPDIR:-/tmp}/karel_de_koala.log"
nohup "$PY" "$SCRIPT" "$@" >"$LOG" 2>&1 &
PID=$!
sleep 0.35
if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID"
    RC=$?
    if [ "$RC" -ne 0 ]; then
        ERR="$(tail -n 8 "$LOG" 2>/dev/null || true)"
        echo "Karel kon niet starten (exit $RC): $ERR"
        if command -v osascript >/dev/null 2>&1; then
            osascript -e 'on run argv' -e 'display dialog ("Karel de Koala kon niet starten:\n\n" & item 1 of argv) buttons {"OK"} default button 1 with title "Karel de Koala"' -e 'end run' "$ERR" >/dev/null 2>&1 || true
        fi
        [ -t 0 ] && read -rp "Druk op Enter om te sluiten..."
        exit "$RC"
    fi
    exit 0
fi

disown "$PID" 2>/dev/null || true
exit 0
