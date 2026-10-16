---
name: labview-temp-folder
description: LabVIEW only - where scratch output goes during work with the labview-mcp tools and agents. Every temporary file (AIXML exports, rendered diagrams, pylabview extractions, backups, helper or throwaway VIs, logs) goes to <repo>/mcp_temp/, which git ignores. This overrides any scratch location another skill or agent names. Use whenever a LabVIEW task (.vi .ctl .lvclass .lvlib .lvproj files, lvai_*/pylv_* tools, labview-mcp subagents) is about to write a temporary file. Do NOT use for anything unrelated to LabVIEW.
---

# LabVIEW scratch folder

All temporary output of LabVIEW work goes to `<repo>/mcp_temp/`, and git ignores it.
This rule wins over any other skill or agent that names a different scratch location (a scratchpad, `%TEMP%`,
a folder outside the repo). Pass the folder, as an absolute path, to every subagent as its scratch folder.

`<repo>` is the git root of the LabVIEW project being worked on. Outside git, it is the folder that holds the `.lvproj`.

Before the first temporary file is written, create the folder and make it ignore itself:

```bash
root=$(git -C "<project folder>" rev-parse --show-toplevel 2>/dev/null || echo "<project folder>")
mkdir -p "$root/mcp_temp"
[ -f "$root/mcp_temp/.gitignore" ] || printf '*\n' > "$root/mcp_temp/.gitignore"
```

The `.gitignore` containing `*` inside `mcp_temp/` hides the folder from git, so the repo's own `.gitignore`
and `git status` stay untouched.

`mcp_temp/` is the working directory for LabVIEW work: create any subfolders and files there, and overwrite or
delete inside it, as the work needs. Keep only its `.gitignore`.

- Paths given to LabVIEW are absolute and long-form (no 8.3 short names).
- Leave `mcp_temp/` in place at the end. The user deletes it.
