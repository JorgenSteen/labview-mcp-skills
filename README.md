# labview-mcp-skills

> **Disclaimer: early phase.** This skill is new and still being tested. It is detailed by design, so using it is
> probably token-heavy and time-consuming: it reads conventions, checks, sweeps and verifies at almost every step.
> Several of its routes are marked unmeasured. Expect to adjust it as it meets real projects.

The `labview` Claude Code skill: LabVIEW and Actor Framework development with the labview-mcp tools. Claude does not
load this README; `SKILL.md` is the skill's entry point (the router). This repository holds only this skill.

## Install

Link the repository root as a global skill (Windows, from a shell with rights to create a junction):

```
mklink /J "%USERPROFILE%\.claude\skills\labview" "<path to this repository>"
```

Claude Code then lists one skill, `labview`, in every session, and loads its files only for LabVIEW work. A
repository with its own repo-local `lv-*` skills (the pilot project pilot) keeps them until it is moved to this skill;
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

## How it works, in short

- A product repo keeps its own conventions in `.labview/conventions/` (committed). Precedence: what the project
  already does (`observed`) > what was chosen in planning (`decided`) > this skill's defaults (`default`).
- A project new to the skill gets one question: how deep to analyse (None / Quick / Standard / Full, with cost).
- Small edits run in local mode (follow the surrounding code); new code sets up only the concerns it touches.
- Safety rules are always on: save version, git as the undo, one LabVIEW caller, the user's LabVIEW is the user's,
  every side effect reported.

## Where it came from

Built on 2026-10-09 from the skills audit in `skills-audit`: its design
(`ARCHITECTURE-PROPOSAL.md`), the user's decisions Q1–Q47 (`answers.md`, which override everything else), the settled
proposals (`proposals/`), and the 12 pilot skills, `af-patterns.md` and `05-toolchain-rules.md` of pilot project. The
`close` shape, the Stop Core lifecycle facts and the kit's `pa_close_join.xml` were measured that day
(`skillsaudit/measure/PB-CLOSE`).

## Open work

- `kit/README.md`, "Kit TODO": `make_icons.py` (RT-style banner, class glyph), `check_membership.py` and others.
- Unmeasured shapes, marked in the ops files: the helper loop's error case inside the loop, `createResources`'
  case structure, E-after with three terminals, Handle Last Ack Core, class/library/typedef renames.
- `MCP-CANDIDATES.md`: check against the newest labview-mcp release, then contribute with the user's go-ahead.
