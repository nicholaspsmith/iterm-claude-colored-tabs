#!/usr/bin/env bash
# Install (or --uninstall) iterm-claude-colored-tabs:
#  - symlinks iterm-claude-tab-color into ~/.local/bin
#  - adds SessionStart/SessionEnd hooks to ~/.claude/settings.json (idempotent,
#    backs the file up first)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
LINK="$BIN_DIR/iterm-claude-tab-color"
SETTINGS="$HOME/.claude/settings.json"

uninstall=false
[[ "${1:-}" == "--uninstall" ]] && uninstall=true

edit_settings() {  # $1 = add|remove
  python3 - "$1" "$SETTINGS" <<'EOF'
import json, sys, time, os

mode, path = sys.argv[1], sys.argv[2]
HOOK_CMDS = {
    "SessionStart": "~/.local/bin/iterm-claude-tab-color hook",
    "SessionEnd": "~/.local/bin/iterm-claude-tab-color session-end",
}

settings = {}
if os.path.exists(path):
    with open(path) as f:
        settings = json.load(f)

changed = False
hooks = settings.setdefault("hooks", {})
for event, cmd in HOOK_CMDS.items():
    entries = hooks.setdefault(event, [])
    present = any(
        "iterm-claude-tab-color" in h.get("command", "")
        for e in entries for h in e.get("hooks", [])
    )
    if mode == "add" and not present:
        entries.append({
            "matcher": "*",
            "hooks": [{"type": "command", "command": cmd, "timeout": 5}],
        })
        changed = True
    elif mode == "remove" and present:
        for e in entries:
            e["hooks"] = [
                h for h in e.get("hooks", [])
                if "iterm-claude-tab-color" not in h.get("command", "")
            ]
        hooks[event] = [e for e in entries if e.get("hooks")]
        if not hooks[event]:
            del hooks[event]
        changed = True

if changed:
    if os.path.exists(path):
        backup = path + ".bak-ictc-" + time.strftime("%Y%m%d%H%M%S")
        with open(path) as src, open(backup, "w") as dst:
            dst.write(src.read())
        print(f"  backed up settings to {backup}")
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    print(f"  {mode}ed hooks in {path}")
else:
    print(f"  hooks already {'present' if mode == 'add' else 'absent'}, settings untouched")
EOF
}

if $uninstall; then
  echo "Uninstalling iterm-claude-colored-tabs..."
  edit_settings remove
  # stop any running watchers and clear their tab colors
  for pf in "$HOME/.cache/iterm-claude-colored-tabs"/*.pid; do
    [[ -e "$pf" ]] || continue
    pid=$(cat "$pf" 2>/dev/null || true)
    tty="/dev/$(basename "$pf" .pid)"
    if [[ -n "$pid" ]] && ps -o command= -p "$pid" 2>/dev/null | grep -q iterm-claude-tab-color; then
      kill "$pid" 2>/dev/null || true
    fi
    printf '\033]6;1;bg;*;default\a' > "$tty" 2>/dev/null || true
    rm -f "$pf"
  done
  [[ -L "$LINK" ]] && rm "$LINK" && echo "  removed $LINK"
  echo "Done. Existing Claude Code sessions keep their colors until they exit."
  exit 0
fi

echo "Installing iterm-claude-colored-tabs..."
mkdir -p "$BIN_DIR"
ln -sf "$REPO_DIR/iterm-claude-tab-color" "$LINK"
echo "  linked $LINK -> $REPO_DIR/iterm-claude-tab-color"
edit_settings add
echo "Done. New Claude Code sessions will mirror /color onto their iTerm tab."
echo "(Already-running sessions pick it up after a restart or /clear.)"
