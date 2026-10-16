# labview-mcp-skills

> **Disclaimer: early phase.** This skill is new and still being tested. It is detailed by design, so using it is
> probably token-heavy and time-consuming: it reads conventions, checks, sweeps and verifies at almost every step.
> Several of its routes are marked unmeasured. Expect to adjust it as it meets real projects.

The `labview` Claude Code skill: LabVIEW and Actor Framework development with the labview-mcp tools. Claude does not
load this README; `SKILL.md` is the skill's entry point (the router). The repository also holds one small companion
skill, `labview-temp-folder` (in its own folder), which sends all LabVIEW scratch output to `<repo>/mcp_temp/`.

## Install

Link the repository root as a global skill (Windows, from a shell with rights to create a junction):

```
mklink /J "%USERPROFILE%\.claude\skills\labview" "<path to this repository>"
```

Link the companion skill the same way, as its own folder (a skill nested inside `labview` is not found):

```
mklink /J "%USERPROFILE%\.claude\skills\labview-temp-folder" "<path to this repository>\labview-temp-folder"
```

Claude Code then lists the skill `labview` in every session, and loads its files only for LabVIEW work. A
repository with its own repo-local `lv-*` skills (the pilot project) keeps them until it is moved to this skill;
while both exist, the repo-local ones win inside that repository.

## Layout

| Path | What it holds |
|---|---|
| `SKILL.md` | the router: setup levels, safety rules, the task → file table |
| `conventions/` | how a product repo's `.labview/` is set up (`setup.md`, `dot-labview.md`), the default conventions (`defaults/`, seven concerns) and templates |
| `knowledge/` | project-independent facts: `actor-framework.md`, `labview-mcp.md` |
| `ops/` | procedures: analysis, override, helper loop, class field, rename, icons, cleanup, sweep, run checks, review |
| `session/` | start, brief, restart, close |
| `kit/` | helper VIs (AIXML) and scripts the procedures run (`kit/README.md`) |
| `MCP-CANDIDATES.md` | every labview-mcp gap the skill works around, written to be contributed upstream |
| `labview-temp-folder/` | the companion skill: LabVIEW scratch output goes to `<repo>/mcp_temp/`, which ignores itself |

## How it works, in short

- A product repo keeps its own conventions in `.labview/conventions/` (committed). Precedence: what the project
  already does (`observed`) > what was chosen in planning (`decided`) > this skill's defaults (`default`).
- A project new to the skill gets one question: how deep to analyse (None / Quick / Standard / Full, with cost).
- Small edits run in local mode (follow the surrounding code); new code sets up only the concerns it touches.
- Safety rules are always on: save version, git as the undo, one LabVIEW caller, the user's LabVIEW is the user's,
  every side effect reported.

## Where it came from

Built on 2026-10-09 from a skills audit: its design proposal, the user's decisions Q1–Q47 (which override everything
else), the settled proposals, and the 12 skills, AF patterns and toolchain rules of a pilot project. The `close` shape,
the Stop Core lifecycle facts and the kit's `pa_close_join.xml` were measured that day.

## Open work

- `kit/README.md`, "Kit TODO": `make_icons.py` (RT-style banner, class glyph), `check_membership.py` and others.
- Unmeasured shapes, marked in the ops files: `createResources`' case structure, E-after with three terminals,
  Handle Last Ack Core, class/library/typedef renames.
- `MCP-CANDIDATES.md`: check against the newest labview-mcp release, then contribute with the user's go-ahead.
