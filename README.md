# labview skill: build status

Not loaded by Claude; this is for the people maintaining the skill. `SKILL.md` is the entry point. The design is in
`../ARCHITECTURE-PROPOSAL.md` (decided 2026-10-09). The sources are the 12 `lv-*` skills, af-patterns.md and
05-toolchain-rules.md in pilot project, the helper kit, and the settled proposals in `../proposals/`, with the
user's answers in `../answers.md` overriding all of them.

**Install** (only once steps 1–2 are done): copy or link this folder to `~/.claude/skills/labview/`. pilot project keeps
its own repo-local `lv-*` skills until it is moved to this skill. While both exist, the repo-local ones win inside
pilot project.

| Step | Files | State |
|---|---|---|
| 1 Backbone | `SKILL.md`, `conduct/setup.md`, `conduct/dot-labview.md`, `conduct/templates/` | done |
| 2 Default conduct | `conduct/defaults/{naming,af-shapes,errors,layout,icons,hygiene}.md`, icon-spec template | - |
| 3 Knowledge + MCP index | `knowledge/actor-framework.md`, `knowledge/labview-mcp.md`, `MCP-CANDIDATES.md` | - |
| 4 Ops | `ops/{analysis,override,helper-loop,class-field,rename,icons,cleanup,sweep,run-checks,review}.md` | - |
| 5 Session + kit | `session/{brief,restart,close}.md`, `kit/` | - |

Choices made while building that the user has not yet confirmed:
- **Rule ids** use the form `conduct: <concern>.<rule-id>`, with a `source:` tag and an optional `area:` per rule
  (`conduct/dot-labview.md`).
- **`project.json` schema 2:** the tests and runs move to `checks.json`, `helpers_folder` is dropped, and
  `labview_version`, `save_version` and `git` are added.
- **No git** (PA-2 / X-4, open in the audit): setup asks to put the repo under git first. Otherwise `.labview/` lives
  outside the product tree.
