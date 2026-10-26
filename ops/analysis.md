# Analyse an existing project (read-only)

**When:** before new work on an existing project that has no `.labview/analysis/` for the items the task needs
(setup, `conventions/setup.md` section 3); a level-2 read ("analyse the code", "what conventions does this project
follow"); or when the user asks for an analysis.

**What it gives:** evidence of what the project does, per item and per area: counts, file paths, examples, and what
could not be read. Never rules: setup derives the `observed` conventions from it, with the user. With the user's
yes, it is written to `<repo>/.labview/analysis/`, one file per item.

**Not here:** turning evidence into conventions (`conventions/setup.md`); judging code against conventions
(`ops/review.md`); execState of a tree (`ops/sweep.md`); behaviour (`ops/run-checks.md`). Conventions do not apply
here: the analysis records what the code does, whatever the convention files say.

## Before you start

- **Level 2** (`SKILL.md`): read only. Nothing in the product tree is written until the user says yes at the end.
  Work files (extractions, CSVs, nets) go to `<repo>/mcp_temp/` (`labview-temp-folder/SKILL.md`), which git
  ignores. `git status --short` before and after must be identical.
- **Offline first.** Every item below can be read from the files with no LabVIEW call, except the parts marked
  "needs LabVIEW". Loading foreign code is what hangs the service (`knowledge/labview-mcp.md`, "A failed, hung or
  blocked call"); a cold sweep of an unloadable library cost about 30 s per VI in the audit.
- **Depth** (`project.json` `analysis_depth`, the user's answer to the first-contact question in `SKILL.md`):
  **quick** = inventory, versions, loadability, naming, layout; **standard** = quick + af-shapes, errors,
  configuration; **full** = standard + icons, tests and the "needs LabVIEW" parts. Never go deeper than chosen
  without asking; say what the chosen depth left out.
- **Items in scope:** the concerns the task touches (`conventions/setup.md`, section 1), or all on request. If this
  session already read the code at level 2, write that evidence instead of reading again.
- **Exclude** spike, trash, `_old`, template and test folders from the counts (count them separately), and say which.

## Steps

1. **Inventory** (seconds): parse every `.lvclass`, `.lvlib` and `.lvproj` as XML. Per class: parent and interfaces
   (`Parent Libraries`; an interface has `NI.LVClass.IsInterface`), library (`NI.Lib.ContainingLib`), members with
   virtual folder, disk folder, scope (`NI.ClassItem.MethodScope`: 1 public, 2 private, 3 protected, 4 community),
   static or dynamic, override flag, description (`NI.Lib.Description`). Classify actors (ancestry to
   `Actor.lvclass`), messages, plain classes and interfaces.
2. **Areas.** Group by deployable tree and subsystem (source subtrees, the projects that hold them). Every count below
   is per area where the areas differ: a pattern followed in one area and not in another is two entries, not one.
3. **Loadability first** (about 5 s for 5800 files in the audit): `python <skill>/kit/lv_loadability.py <tree>`
   resolves every link against the installed LabVIEW and the tree, and lists per class and library "loadable" or
   the missing packages and the load chain. It decides which items may use LabVIEW at all.
4. **The items** (table below), each from the files.
5. **Draft** each item in the scratch folder, then show the user a summary: per item the main counts, the
   inconsistencies, and what could not be read.
6. **On the user's yes:** write `.labview/analysis/<item>.md`, commit the `.labview/` change alone (`convention:
   hygiene.commit-messages`, e.g. `docs(labview): project analysis`). No git: `conventions/dot-labview.md`, "No git".
   On a no: offer the project's documentation instead, or keep nothing.

## Items

| item (`analysis/<file>`) | what to record | read from (offline) | needs LabVIEW |
|---|---|---|---|
| `naming.md` | prefix per file and owner; case style of methods, function VIs, typedefs, classes, libraries, private data labels; role names (loop VIs, events typedef, launch methods); drift (copied prefixes, template names) | file names, the inventory, private data decoded from `NI.LVClass.FlattenedPrivateDataCTL` with the pylabview bundled with labview-mcp | no |
| `versions.md` | the version stamp of every file (counts per version); `NI.LV.All.SaveVersion` per `.lvproj`, `.lvlib`, `.lvclass`; `.lvversion` files above or in the tree | version bytes in the files; the XML property | no |
| `loadability.md` | per class and library: loadable or not; missing packages with the files linking them and the classes they block; load chains | step 3 | which load path raises a dialog |
| `af-shapes.md` | per actor: overrides and where Call Parent sits; helper-loop location and naming; stop mechanism and stop site; close/destroy site; Register/Unregister placement and its error source; Handle Error order and hooks; HLAC; events storage (typedef, field, accessors, global events); Timeout frames and values; launch sites and the launch tree; pre-launch settings; dependency direction | `python <skill>/kit/vi_nets.py` on overrides, loop VIs and launch VIs; link info; the inventory | frame names and Timeout values pylabview cannot decode; whether a shape hangs (a run) |
| `errors.md` | Handle Error handlers; `Send Error Report` and the application's own error messages; logger links; Clear Errors use; unwired `error out`s; custom error codes and where they are documented; "no plan" statements | nets (an `error out` with no wire), link info, `NI.Lib.Description`, the docs | constant values (the code a Clear Errors clears) |
| `configuration.md` | settings files (INI or other) and their naming; config classes (parent, children); metadata sections; who reads which file | the tree, the inventory, links to configuration-file VIs | no |
| `icons.md` | banner text, colour and font per owner; class and library icons; layers vs flattened; glyph use; default icons | `NI.Lib.Icon` in the XML, the icon and icon-editor blocks of each VI; contact sheets | no |
| `layout.md` | library per actor; virtual folder names per kind of class; typedef owners (class folder vs library folder); disk layout (flat or mirrored); scope distribution; accessors present (which fields, direction, dispatch); orphan VIs | the inventory, `python <skill>/kit/check_membership.py <folder>` | no |
| `tests.md` | test VIs, their library and project; framework (Caraya, VI Tester, LUnit, none); the pass indicator and other outputs; the kind (round trip, driver) | links of the test VIs, their front panels (pylabview) | whether they pass (`ops/run-checks.md`) |

Also worth one line each where present: Conditional Disable symbols (on which project targets, used in which VIs,
with or without a bookmark comment; read from the decompressed diagram), and the class descriptions that exist.

## Format of an analysis file

```markdown
# Analysis: <item>
written: <date> by ops/analysis.md   scope: <trees>   excluded: <spike/test/template folders>
method: <scripts and reads>   LabVIEW calls: 0   not read: <n files, why>

## <area>
- <observation>: <count> of <base>, e.g. <path>, <path>
- inconsistent: <pattern A> <n> vs <pattern B> <n>, e.g. <paths>

## Could not be determined offline
- <question> (what would settle it)
```

Evidence only: no "should", no verdict. Paths relative to the repo root, with forward slashes.

## Checks / evidence

- Every count has its base (`12 of 14 actors`) and at least one example path.
- Every file the scripts could not read is listed (pylabview failed on 24 of 4182 VIs in the audit, all in
  `LVdatatype.checkSanity`).
- `git status --short` is unchanged until the write in step 6; after it, only `.labview/analysis/` changed.

## Kit status (the scripts this file uses)

- **In the kit now:** `vi_nets.py` (wires with typed endpoints, offline), `check_membership.py`, `sweep_paths.py`,
  `read_saved_answer.py`, `aixml_frames.py`. The window list is labview-mcp's `lvai_labview_state`.
- **Being ported:** `lv_loadability.py`, from the audit's dependency closure (link scan, closure, "why" chain).
  Until it is in the kit, ask before any LabVIEW call on foreign code. > MCP-candidate: offline-loadability
- **Still to port** (audit scripts, no kit file yet): the version-byte scan (`lv_save_version.py`, named in
  `knowledge/labview-mcp.md`); the XML inventory and the private-data decoder; the link-info reader and the
  Conditional Disable scan; the override, loop and stop-shape scans built on `vi_nets.py`; the icon decoder and its
  contact sheets. Until then, write a small script per item on the same reads, in the scratch folder.
  > MCP-candidate: af-describe-actor > MCP-candidate: nets-dump

## What the audit measured (sizing)

The skills audit read a 4182-VI product (two trees, 437 classes, 157 libraries) this way, with no LabVIEW call:

| item | method | cost or yield |
|---|---|---|
| inventory, naming, layout | XML parse; private data decoded with pylabview | all 437 classes; field labels of every actor |
| loadability | link-info closure | ~5 s for 5792 files; predicted every later LabVIEW hang |
| AF shapes, errors | pylabview extraction and `vi_nets.py` | 3764 VIs extracted; 1411 VIs as nets in ~55 min |
| icons | icon blocks decoded, contact sheets rendered | 4182 VIs, 0 decode errors |
| tests, Conditional Disable | link info, front panels, decompressed diagrams | 35 test VIs; symbols in 45 VIs |

(audit agents A–G, 2026-10-07)

## Report

```
analysis <repo> <trees>   areas <list>   items <list>   LabVIEW calls <n>   time ~<min> min
loadable <n>/<n> classes (actors <n>/<n>); missing packages <list>
per item: <one line: the main counts and inconsistencies>
not read: <n files, why>   undetermined offline: <n questions>
written: .labview/analysis/<files> (commit <hash>) | not written (the user said no) | added to the project docs
```

## Traps

- A raw grep of a `.vi` hits inherited help text and a typedef's cached owner type: count dependencies from link
  info, and take only the first path of each link entry (later ones are stale auxiliaries).
- Whether a library loads its child classes decides whether a package blocks them. Record both counts (strict and
  lazy) when the closure gives both.
- String constants and most diagram constants are compressed in a `.vi`: an item that depends on them is
  "undetermined offline", not "absent".
- A pattern the code follows in some places and breaks in others is an inconsistency to show the user, with counts.
  Never pick the majority as the observed rule.
- Typedefs used only inside the flattened private data are missed by a link scan; decode the private data too.
