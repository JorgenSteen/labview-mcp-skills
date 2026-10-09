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
| 1 Backbone | `SKILL.md`, `conventions/setup.md`, `conventions/dot-labview.md`, `conventions/templates/` | done |
| 2 Default conventions | `conventions/defaults/{naming,af-shapes,errors,layout,icons,hygiene}.md` | done (the icon-spec template moves to step 5 with `make_icons.py`, whose format changes) |
| 3 Knowledge + MCP index | `knowledge/actor-framework.md`, `knowledge/labview-mcp.md`, `MCP-CANDIDATES.md` | - |
| 4 Ops | `ops/{analysis,override,helper-loop,class-field,rename,icons,cleanup,sweep,run-checks,review}.md` | - |
| 5 Session + kit | `session/{brief,restart,close}.md`, `kit/` | - |

Choices made while building:
- **Rule ids** use the form `convention: <concern>.<rule-id>`, with a `source:` tag and an optional `area:` per rule
  (`conventions/dot-labview.md`).
- **`project.json` schema 2:** the tests and runs move to `checks.json`, `helpers_folder` is dropped, and
  `labview_version`, `save_version` and `git` are added.
- **No git** (PA-2 / X-4, open in the audit): setup asks to put the repo under git first. Otherwise `.labview/` lives
  outside the product tree.

Confirmed by the user 2026-10-09: the five choices above. Added on the user's request the same day:
- **Four setup levels:** small read, large read (offer to keep the result), minor edit (local mode, no setup),
  new code or a major change (setup for the touched concerns only).
- **Safety rules** (save version, git, one LabVIEW caller, the side-effects report) are separate from the
  conventions and cannot be switched off.
- **The name** "code of conduct" became **conventions** (`.labview/conventions/`), because CODE_OF_CONDUCT.md means
  contributor behaviour.

Step 2, settled by the user on 2026-10-09:
- `naming.class-library-names` is `<P>-<ABBR>-<name>` in snake_case. `naming.field-names` is camelCase without the
  prefix.
- Pre-launch settings: the child class owns the typedef and a public custom `writePrelaunchSettings` (class input
  optional, settings input required). The caller launches each child in a launch method (`launchHwm`), and the
  global events travel inside these settings.
- Actor Core returns the merged error including Call Parent's, so an error ends the actor by default.
- Still open: INI configuration, disabled instrumentation, and an actor template in the project. Not yet a
  convention; to be put to the user again.
