# iterm-claude-colored-tabs

Mirror Claude Code's `/color` session color onto the iTerm2 tab, so you can
tell your Claude sessions apart from the tab bar.

Type `/color blue` in Claude Code → the iTerm tab holding that session turns
the same blue within half a second. `/color default` clears it. When the
session exits, the tab color resets.

## Why this isn't built in (and how this works around it)

`/color` is session-local UI state inside Claude Code. It is **not** exposed
anywhere external: not in `settings.json`, not in the statusline JSON, not in
hook input, not as an environment variable. Claude Code also never emits any
terminal escape sequence for it.

But every `/color <name>` you type **is** recorded in the session transcript
(`~/.claude/projects/<project>/<session-id>.jsonl`) as a user entry:

```
<command-name>/color</command-name>
<command-message>color</command-message>
<command-args>blue</command-args>
```

So this tool installs a Claude Code `SessionStart` hook that spawns one tiny
detached watcher per terminal tab. The watcher:

1. polls that session's transcript (twice a second, incremental reads),
2. when a `/color` entry appears, maps the name to Claude Code's own palette
   RGB values, and
3. writes iTerm2's proprietary tab-color escape sequence
   (`OSC 6;1;bg;…`) directly to the Claude process's pty.

It exits — and resets the tab — as soon as the Claude process dies. There is
no daemon: watchers live and die with their sessions. A `SessionEnd` hook
cleans up as well.

## The palette

Exact values extracted from the Claude Code binary (v2.1.251, default
dark/light themes — `/color` and subagent colors share this palette):

| name   | rgb             | hex       |
| ------ | --------------- | --------- |
| red    | 220, 38, 38     | `#DC2626` |
| blue   | 106, 155, 204   | `#6A9BCC` |
| green  | 22, 163, 74     | `#16A34A` |
| yellow | 202, 138, 4     | `#CA8A04` |
| purple | 130, 125, 189   | `#827DBD` |
| orange | 217, 119, 87    | `#D97757` |
| pink   | 196, 102, 134   | `#C46686` |
| cyan   | 8, 145, 178     | `#0891B2` |

## Install

```sh
./install.sh
```

This symlinks `iterm-claude-tab-color` into `~/.local/bin` and adds
`SessionStart`/`SessionEnd` hooks to `~/.claude/settings.json` (idempotent;
the settings file is backed up first). `./install.sh --uninstall` reverses
everything and clears any live tab colors.

Requires macOS's stock `python3`, iTerm2, and Claude Code ≥ 2.1.205 (when
`/color` shipped). New sessions pick it up immediately; sessions already
running when you install get it after a restart or `/clear`.

## Manual use

```sh
iterm-claude-tab-color set pink      # any palette name, or #RRGGBB
iterm-claude-tab-color reset
```

## Limitations

- **Bare `/color` (random) can't be mirrored.** Claude picks the random color
  in memory and the transcript records empty args, so the watcher ignores it.
  Use an explicit color name.
- **`--resume` re-applies the transcript's last color to the tab, but Claude
  Code itself forgets `/color` on resume** — so the tab may show the color of
  the previous run while the prompt bar is back to default. `/color default`
  (or picking a color again) re-syncs.
- iTerm2 tab color is per **tab**; with split panes running multiple Claude
  sessions, the last one to change color wins.
- Inside tmux the escape is sent with passthrough wrapping, which needs
  `set -g allow-passthrough on` — best effort, untested.
- The palette is hardcoded from v2.1.251. If Anthropic re-tunes the theme
  colors, update `PALETTE` in `iterm-claude-tab-color`. If a future Claude
  Code stops writing `/color` to the transcript (or exposes the color
  properly, e.g. in statusline JSON), this tool should be revisited.

## Tests

```sh
python3 tests/test_parse.py
```
