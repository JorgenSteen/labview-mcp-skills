---
name: labview
description: LabVIEW development with the labview-mcp tools - Actor Framework actors and overrides, helper loops, classes and fields, renames, icons, Clean Up Diagram, sweeps, test runs, reviews, briefs for LabVIEW subagents, LabVIEW restarts, session close, and each project's conventions in its .labview/ folder. Use whenever the task touches LabVIEW files (.vi .ctl .lvclass .lvlib .lvproj), the Actor Framework, or lvai_*/pylv_* tools; also "/labview <part>" (setup, review, close, ...). Do NOT use for anything unrelated to LabVIEW.
---

# LabVIEW development

This file is the router. Everything else is in files beside it; read only those the task needs.
`<skill>` below means this skill's folder. A project's conventions live in its repo, in `<repo>/.labview/`
(format: `<skill>/conventions/dot-labview.md`).

## LabVIEW must answer first

Before the first LabVIEW call of a session, run `session/start.md`: it checks that LabVIEW and the labview-mcp
service answer and starts them if not. Every other file assumes LabVIEW is running. A subagent that loses LabVIEW
during its work stops and reports; it never starts or restarts LabVIEW itself.

## How much setup a task needs

Decide the level before the first LabVIEW call. If the level is unclear, ask the user.

| Level | Task | What happens |
|---|---|---|
| **1 Small read** | a question, an explanation, a look at a few VIs | Nothing is set up and nothing is written. |
| **2 Large read** | a full analysis of the code or its documentation, a review of a whole tree, documenting a library | Do the read. At the end, offer once to keep what was learned. Either it goes into `.labview/` as observed conventions (`conventions/setup.md`, section 3, which reuses this read rather than redoing it), or it is added to the project's documentation. Write only on a yes. |
| **3 Minor edit** | a change inside existing VIs or classes, with no new class, actor or library; or the user asks for no best-practice rules | **Local mode:** no analysis and no setup. Follow the pattern of the VI being changed and its neighbours. The safety rules below still apply. If the project has no `.labview/`, offer once at the end to record `"conventions_mode": "local"`, so the question does not come back. |
| **4 New code or a major change** | a new class, actor, library or subsystem, or a large rework | Run `conventions/setup.md`, but only for the concerns the task touches. For example, a new actor needs af-shapes, naming and layout; icons only if icons are made. Concerns already in `.labview/conventions/` are not asked again. |

If `project.json` says `"conventions_mode": "local"`, level 4 does not start setup on its own. Ask the user whether
this change should get conventions (and for which concerns), or follow the surrounding code.

When the conventions exist: read `project.json`, then only the convention files the task touches. A concern marked
`status: off` has no rules for this project.

## Safety rules (always on, every level that writes)

These protect the files and the toolchain. They are not conventions and cannot be switched off.

- **Save version.** Before the first save, scan the version of the files to be saved, and make sure the save cannot
  upgrade them. Use the project's Save version (`project.json` `save_version`, or what the files show), and save
  through the open project. Re-scan after the step: any file newer than the project's version means stop and report.
  A one-VI fix saved from a newer LabVIEW makes that VI unloadable in the project's version. Route:
  `knowledge/labview-mcp.md`, "Save version".
- **Git is the only undo.** Commit before every structural step. If there is no git, see `dot-labview.md`, "No git".
- **One LabVIEW caller at a time.** Make calls strictly in sequence. A crash or a hung call stops the work and is
  reported, with no retry loops (`knowledge/labview-mcp.md`).
- **Side effects are reported.** Every item removed, file re-saved or upgraded, or project file rewritten is listed
  in the end-of-session report (`session/close.md`).

## Rules that always apply

- **Scope (maintenance).** Conventions apply to new code. On existing code, change only what the task needs. Files
  and parts the task does not touch stay as they are, even where they break the conventions, unless the user asks.
  Findings in untouched parts are reported, not fixed.
- **New code in an old area.** A small change inside existing code follows that area's existing pattern; the local
  setup is the boss. A major change means asking the user which pattern to use before building.
- **Precedence.** Rules come from three sources: (1) what the project already does (`observed`), (2) what was
  chosen during planning or development (`decided`), (3) this skill's defaults (`default`). The order is settled
  once, when a convention file is written, so the convention files are the only place to read. The defaults in
  `<skill>/conventions/defaults/` are templates and are never followed directly.
- **New rules during work.** If a rule the conventions do not cover comes up, propose it to the user. Once chosen,
  log it in `.labview/decisions.md` and add it with a `decided` tag. Do not invent conventions silently.
- **Architecture is the user's call.** That covers the class hierarchy, base actors and the error-handling plan. Propose,
  then ask.
- **labview-mcp's own agents** (class-generator, vi-editor, the test agents, doc-generator, DQMH) do the work they
  are made for. They do not know the project's conventions, so give them the rules that apply in the prompt
  (in local mode: the local pattern to follow), and check their result afterwards.

## Where things are

| Task | Read |
|---|---|
| Set up or extend `.labview/conventions/`; swap a convention | `conventions/setup.md` |
| The `.labview/` folder: files, keys, tags | `conventions/dot-labview.md` |
| How the Actor Framework behaves (call order, Stop Core inside Call Parent, stop/destroy hazards) | `knowledge/actor-framework.md` |
| labview-mcp operating rules and known gaps, by tool; the save-version route | `knowledge/labview-mcp.md` |
| Analyse an existing project (writes `.labview/analysis/`) | `ops/analysis.md` |
| Create an AF override and put hook VIs into it | `ops/override.md` |
| Build an actor's helper loop | `ops/helper-loop.md` |
| Add, change or remove a class field and its accessors | `ops/class-field.md` |
| Rename a class member | `ops/rename.md` |
| Icons: standard, apply, read back | `ops/icons.md` |
| Clean Up Diagram on generated VIs | `ops/cleanup.md` |
| Cold sweep: every VI runnable, membership consistent | `ops/sweep.md` |
| Run the project's test VIs and behaviour runs | `ops/run-checks.md` |
| Review an AF design or a built actor against the conventions | `ops/review.md` |
| LabVIEW or the labview-mcp service does not answer; start of a session | `session/start.md` |
| Write a brief for a LabVIEW subagent, or brief a labview-mcp agent | `session/brief.md` |
| Restart LabVIEW unattended | `session/restart.md` |
| End a session: status, side-effects report, commit | `session/close.md` |
| Scripts and helper VIs (AIXML) | `kit/README.md` |
| What could move into labview-mcp | `MCP-CANDIDATES.md` |

If a task spans several rows, read the files in parallel.

## Markers in these files

- `convention: <concern>.<rule-id>` means "apply this project's rule", e.g. `convention: af-shapes.stop-site`. Look
  it up in `<repo>/.labview/conventions/<concern>.md`. In local mode, or when the concern is off, follow the
  surrounding code instead. The ops never restate a rule's content.
- `> MCP-candidate: <id>` marks a passage that works around a labview-mcp gap. Once labview-mcp ships the tool listed
  under that id in `MCP-CANDIDATES.md`, the passage is replaced by a call to it.
