# The `.labview/` folder in a product repo

Everything project-specific lives here, in the product repo, and is committed. The skill itself stays general and
reads this folder; it carries no project names.

```
<repo>/.labview/
  project.json      facts: what and where the project is
  conventions/      the conventions in force; the ops read only this
    naming.md  af-shapes.md  errors.md  layout.md  configuration.md  icons.md  hygiene.md
    icon-spec.json  the machine-readable icon standard that icons.md refers to
  decisions.md      rules proposed and chosen during planning or development
  analysis/         what the project analysis observed (evidence, never instructions)
  checks.json       the test VIs and behaviour runs (ops/run-checks.md)
  sessions/<id>/    session files (status, briefs, MCP report) when project.json names no other place
  skills/  rules/   repo-specific skills and rules, if any
```

Templates are in `<skill>/conventions/templates/`. Setup (`conventions/setup.md`) creates the folder.

## project.json (facts)

Schema version 2. All paths are relative to the repo root and use forward slashes.

| Key | Meaning | Required |
|---|---|---|
| `$schema_version` | `2` | yes |
| `project_name` | human name | yes |
| `prefix` | file-name prefix of hand-written files, e.g. `ZM` (the naming conventions say how it is used) | yes |
| `source_root` | the LabVIEW source tree | yes |
| `project_file` | the main `.lvproj`; `project_files` (list) if there are several | yes |
| `labview_version` | the LabVIEW version the project is developed in, e.g. `"2020"` | yes |
| `save_version` | the version files must be saved as, e.g. `"20.0"` (the safety rules in SKILL.md say how it is enforced) | yes |
| `git` | `true`, or `false` with `product_root` (see "No git" below) | yes |
| `conventions_mode` | `full` (the conventions in `conventions/` apply) or `local` (no conventions; every change follows the pattern of the code around it; see `SKILL.md`, "How much setup a task needs") | yes |
| `restart_go_ahead` | `ask` (default) or `always`: the user's standing go-ahead to restart LabVIEW for this project, with `restart_go_ahead_note` (who, when, the user's words). Set only by the user; a kill always needs its own go-ahead (`session/restart.md`) | no |
| `analysis_depth` | `none`, `quick`, `standard` or `full`: the user's answer to the first-contact question (`SKILL.md`, "First time in a project"; `ops/analysis.md`) | yes |
| `proof_folder`, `proof_prefix` | where throwaway measurements and skill tests go, and their name prefix | no |
| `briefs_folder` | where briefs are saved; `<X>` = the session id | no |
| `status_file` | the session hand-over file | no |
| `mcp_reports_folder` | one labview-mcp report per session | no |
| `knowledge_files` | the project's own measured-rules or field-guide files, if it keeps any | no |
| `commit_attribution` | a trailer line for commit messages, if the project wants one | no |

Machine facts (the installed LabVIEW and its bitness, the labview-mcp version, `LVAutoSave` paths) are not stored
here. They are read from `lvai_status` at the start of a session.

**Schema 1** (the pilot project) is read as it is. Setup migrates it only when the user agrees. The migration moves
`tests`/`runs` into `checks.json`, drops `helpers_folder` (the kit is in the skill), turns `rules_file`, `guide_file`
and `mcp_suggestions_file` into `knowledge_files`, and adds the new keys.

## conventions/*.md (the conventions)

There is one file per concern, and each file can be swapped or switched off on its own:

| File | Concern |
|---|---|
| `naming.md` | file and member names, prefix and abbreviation, fixed-role names |
| `af-shapes.md` | actor structure: helper loops, the stop, `close`, Pre Launch Init settings, events, Handle Error, launching, dependency direction, messages, Timeout |
| `errors.md` | the error policy: default behaviour, logging, errors ignored on purpose, the "no plan" statement |
| `layout.md` | library and class layout, virtual folders, typedef placement, scope, accessors |
| `icons.md` | the icon standard (+ `icon-spec.json`) and when icons are made |
| `configuration.md` | how settings are stored and read: INI files, the configuration class, metadata, who reads |
| `hygiene.md` | Clean Up Diagram policy, tests, commit messages, Conditional Disable comments |

The safety rules (save version, commit before a structural step, one LabVIEW caller, the side-effects report) are
not conventions. They live in `SKILL.md` and cannot be switched off.

Format of each file:

```markdown
# Convention: <concern>
status: in force            # or: off (the ops apply no rule of this concern)
written: 2026-10-09 by conventions/setup.md

## <rule-id>
<the rule, stated in full, so it can be read without any other file>
source: default | decided 2026-10-09 (decisions.md#D3) | observed (analysis/naming.md#methods)
area: src/rt/**             # optional; without it the rule applies to the whole project
```

- **Rule ids** (`stop-site`, `method-case`, ...) are stable. The ops and the review cite them as
  `convention: <concern>.<rule-id>`. The defaults define the ids, and a project may add its own.
- **`source`** records the precedence decision. `observed` beats `decided`, which beats `default`. Setup writes only
  the winning rule. If observed code contradicts a decided or default rule, the user is asked (see setup).
- **`area`** handles projects whose parts follow different conventions (e.g. RT core vs GUI). The same rule-id may
  appear once per area. Code outside every area falls back to the entry without one.

## decisions.md

A log of choices made during planning or development. It is the record behind every `decided` tag.

```markdown
## D3 (2026-10-09): Handle Error calls the parent first
Rule: af-shapes.handle-error-order
Chosen: Call Parent first, then the actor's own handler
Instead of: (default) / (what the code did) / (the alternative)
Why: <the user's reason, quoted when possible>
```

## analysis/

These files are written by `ops/analysis.md`, one per item (naming, versions, loadability, shapes, errors, icons,
layout, tests). They hold evidence: counts, file paths, examples. They are not rules. Setup derives the `observed`
conventions from them.

## checks.json

```json
{ "$schema_version": 1, "tests": [ ... ], "runs": [ ... ] }
```

Entry format: `ops/run-checks.md`. A test VI reports a named Pass Boolean plus `error out` (`convention:
hygiene.test-convention`).

## No git

The audit left this case open; the handling below is this skill's choice.
- If the product repo is not under git, setup first asks the user to put it under git.
- If the user declines, or the tree must not be written at all (a reference copy, say), `.labview/` is kept in a
  folder the user names, outside the product tree. `project.json` then records `"git": false` and
  `"product_root"` (the product tree's absolute path).
- Each session is told where that folder is; it cannot be found from the product tree. Sessions work only on
  copies and compare against a manifest after each LabVIEW save.
