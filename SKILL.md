---
name: labview
description: LabVIEW development with the labview-mcp tools - Actor Framework actors and overrides, helper loops, classes and fields, renames, icons, Clean Up Diagram, sweeps, test runs, reviews, briefs for LabVIEW subagents, LabVIEW restarts, session close, and each project's code of conduct in its .labview/ folder. Use whenever the task touches LabVIEW files (.vi .ctl .lvclass .lvlib .lvproj), the Actor Framework, or lvai_*/pylv_* tools; also "/labview <part>" (setup, review, close, ...). Do NOT use for anything unrelated to LabVIEW.
---

# LabVIEW development

This file is the router. Everything else is in files beside it; read only those the task needs.
`<skill>` below means this skill's folder.

## Before any LabVIEW work in a repository

1. **Find the code of conduct.** It lives in the product repo: `<repo>/.labview/conduct/`. All work follows what it
   says. If it is missing or incomplete, run `<skill>/conduct/setup.md` first. Setup fills it from the project
   itself, from the user's choices, or from this skill's defaults. A read-only question needs no setup. If a
   read-only task would profit from the conduct, ask before writing anything into the repo.
2. **Read the project facts** in `<repo>/.labview/project.json` (format: `<skill>/conduct/dot-labview.md`).
3. **Read the conduct files the task touches.** They are one file per concern (naming, af-shapes, errors, layout,
   icons, hygiene). A concern marked `status: off` has no rules for this project.

## Rules that always apply

- **Scope (maintenance).** The conduct applies to new code. On existing code, change only what the task needs.
  Files and parts the task does not touch stay as they are, even where they break the conduct, unless the user
  asks. Findings in untouched parts are reported, not fixed.
- **New code in an old area.** A small change inside existing code follows that area's existing pattern; the local
  setup is the boss. A major change (a new subsystem, a large rework) means asking the user which pattern to use
  before building. The conduct's defaults are for genuinely new areas.
- **Precedence.** Rules come from three sources: (1) what the project already does (`observed`), (2) what was
  chosen during planning or development (`decided`), (3) this skill's defaults (`default`). The order is settled
  once, when a conduct file is written, so the conduct files are the only place to read. The defaults in
  `<skill>/conduct/defaults/` are templates and are never followed directly.
- **New rules during work.** If a rule the conduct does not cover comes up, propose it to the user. Once chosen, log
  it in `.labview/decisions.md` and add it to the conduct file with a `decided` tag. Do not invent conduct
  silently.
- **Architecture is the user's call.** That covers the class hierarchy, base actors and the error-handling plan. Propose,
  then ask.
- **One LabVIEW caller at a time.** A crash stops the work and is reported, with no retry loops. Commit before every
  structural step, since git is the only undo. Every side effect (items removed, files re-saved or upgraded) is
  listed in the end-of-session report. The details are in `<skill>/knowledge/labview-mcp.md` and
  `<skill>/session/close.md`.
- **labview-mcp's own agents** (class-generator, vi-editor, the test agents, doc-generator, DQMH) do the work they
  are made for. They do not know the project's conduct, so give them the conduct rules that apply in the prompt,
  and check their result against those rules afterwards.

## Where things are

| Task | Read |
|---|---|
| No or incomplete `.labview/conduct/`; "set up the conduct"; a convention to swap | `conduct/setup.md` |
| The `.labview/` folder: files, keys, tags | `conduct/dot-labview.md` |
| How the Actor Framework behaves (call order, Stop Core inside Call Parent, stop/destroy hazards) | `knowledge/actor-framework.md` |
| labview-mcp operating rules and known gaps, by tool | `knowledge/labview-mcp.md` |
| Analyse an existing project (writes `.labview/analysis/`) | `ops/analysis.md` |
| Create an AF override and put hook VIs into it | `ops/override.md` |
| Build an actor's helper loop | `ops/helper-loop.md` |
| Add, change or remove a class field and its accessors | `ops/class-field.md` |
| Rename a class member | `ops/rename.md` |
| Icons: standard, apply, read back | `ops/icons.md` |
| Clean Up Diagram on generated VIs | `ops/cleanup.md` |
| Cold sweep: every VI runnable, membership consistent | `ops/sweep.md` |
| Run the project's test VIs and behaviour runs | `ops/run-checks.md` |
| Review an AF design or a built actor against the conduct | `ops/review.md` |
| Write a brief for a LabVIEW subagent, or brief a labview-mcp agent | `session/brief.md` |
| Restart LabVIEW unattended | `session/restart.md` |
| End a session: status, side-effects report, commit | `session/close.md` |
| Scripts and helper VIs (AIXML) | `kit/README.md` |
| What could move into labview-mcp | `MCP-CANDIDATES.md` |

If a task spans several rows, read the files in parallel.

## Markers in these files

- `conduct: <concern>.<rule-id>` means "apply this project's rule", e.g. `conduct: af-shapes.stop-site`. Look it up in
  `<repo>/.labview/conduct/<concern>.md`. The ops never restate a rule's content.
- `> MCP-candidate: <id>` marks a passage that works around a labview-mcp gap. Once labview-mcp ships the tool listed
  under that id in `MCP-CANDIDATES.md`, the passage is replaced by a call to it.
