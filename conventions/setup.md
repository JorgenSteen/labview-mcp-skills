# Conventions setup: fill `.labview/` before new work starts

**When:**
- at level 4 (new code or a major change; `SKILL.md`, "How much setup a task needs"), for the concerns the task
  touches;
- at level 2, when the user said yes to keeping what a large read learned;
- when the user asks to set up, extend or swap a convention.

Setup runs during planning, and no LabVIEW file is changed until it has finished. Level 1 and level 3 (local mode)
never run it.

**What it gives:** one file per concern in which every rule's source is settled (`observed` > `decided` >
`default`). After that, the ops read only these files. Format: `conventions/dot-labview.md`.

**Who decides:** the user. Setup proposes and shows evidence. It never picks a convention for an existing project on
its own, and never overrides what the project already does without asking.

## 1. Find out where you are

| State | Route |
|---|---|
| The convention files for the concerns in scope exist | Done. Read them. |
| Some concerns in scope are missing | Section 3 or 4, for those concerns only. |
| `project.json` says `"conventions_mode": "local"` | Ask the user first: conventions for this change (which concerns), or follow the surrounding code. On "conventions", set the mode to `full` and continue. |
| `.labview/project.json` is schema 1 (the pilot project pilot) | Offer the migration (`dot-labview.md`). Without the user's yes, read it as it is and write the conventions beside it. |
| No `.labview/`, and LabVIEW code exists | Section 2, then section 3. |
| No `.labview/`, and no or almost no LabVIEW code | Section 2, then section 4. |
| The repo is not under git | Ask first (`dot-labview.md`, "No git"). |

**Concerns in scope:** what the task touches, not all six:

| Task | Concerns |
|---|---|
| A new actor or actor tree | af-shapes, naming, layout, errors |
| A new plain class or library | naming, layout |
| New VIs in an existing class | naming (and layout if new folders or typedefs) |
| Icons made or changed | icons |
| Tests added | hygiene |
| The user asks for "the whole set" | all six |

## 2. Project facts

Collect the facts for `project.json` (template `conventions/templates/project.json`), detecting what you can
without LabVIEW:
- `project_file`: the `.lvproj` files in the repo. If there are several, ask which ones are in scope.
- `labview_version` and `save_version`: read them from the files' version stamps and the `.lvproj`'s
  `NI.LV.All.SaveVersion`. The scan script is in `kit/`. The user confirms them, because a wrong value here upgrades
  the whole project on the first save.
- `prefix`: the dominant file-name prefix in `source_root`. For a new project, ask.
- `source_root` and `git`: from the tree.
- `conventions_mode`: `full`.

Write `project.json` and commit it.

## 3. Existing project: observe, then fill the gaps

1. **Analyse** (`ops/analysis.md`) for the concerns in scope only. It writes `.labview/analysis/`, one file per item,
   holding evidence only. If the evidence came from a level-2 read in this session, write that into
   `analysis/` instead of reading the code again. Run the analysis only for items the read did not cover.
2. **Derive the observed rules** per concern. A convention counts as observed when the code follows it
   consistently in an area. Where areas differ (e.g. RT core vs GUI), write one entry per area (`area:`). A pattern
   that is followed in some places and broken in others is not observed. Show it to the user as an inconsistency,
   with counts.
3. **List what is left open** per concern: rules the defaults have but the analysis found no convention for.
4. **Settle the open rules with the user, one concern at a time.** Show the observed rules, and for each gap the
   default with a one-line reason. The user accepts the default, gives another rule (`decided`, logged in
   `decisions.md`), or switches the whole concern off (`status: off`). A default for new code in an existing
   project is a proposal, and the maintenance rule still applies: the local pattern wins for small changes inside
   existing code.
5. **Observed vs default.** If the code does X and the default says Y, the observed rule wins and is written. The
   default is not mentioned again unless the user asks to change the project's convention, which is then a
   `decided` rule for new areas only.

## 4. New project: choose from the defaults

Go through the concerns in scope in this order: naming, layout, af-shapes, errors, icons, hygiene. Per concern,
show the default file's rules in short form. The user accepts them, changes single rules (`decided` +
`decisions.md`), or switches the concern off. For icons, also settle the per-class banner abbreviations and
colours, and the class glyphs, in `icon-spec.json` (`ops/icons.md`, "Icon standard").

## 5. Write and commit

1. For each concern settled, copy `<skill>/conventions/defaults/<concern>.md` to
   `.labview/conventions/<concern>.md`, then replace or annotate each rule with the settled version and its
   `source`. Rules the user removed are deleted, not left in commented out. Drop the "Default template"
   note at the top, and add `written: <date>`. Rules marked "Not settled by the user; setup asks" are always
   asked.
2. `decisions.md`: one entry per `decided` rule (template `conventions/templates/decisions.md`).
3. Commit the `.labview/` changes alone, with a message such as `docs(labview): set up naming and layout
   conventions`.
4. Report to the user:
   - per concern, the counts of `observed` / `decided` / `default` rules
   - the inconsistencies found
   - the concerns switched off
   - the concerns not yet set up (out of scope this time)

## Swapping or changing a convention later

- **Swap a whole concern** (e.g. another naming scheme): replace `.labview/conventions/<concern>.md` with the new
  file, which keeps the same rule ids where the meaning matches. Log the swap in `decisions.md`.
- **Change one rule:** edit it, set `source: decided <date>`, and log it.
- **Switch off:** set `status: off`. The ops then apply none of its rules, and the review reports none of them.
- **Back to local mode:** set `"conventions_mode": "local"`. The convention files stay, unused, until the mode is
  `full` again.
- Existing code is not migrated to the new rule unless the user asks (maintenance rule).
