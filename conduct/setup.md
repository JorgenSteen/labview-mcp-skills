# Conduct setup: fill `.labview/` before work starts

**When:** before the first LabVIEW work in a repo whose `.labview/conduct/` is missing or incomplete, when the user
asks to set up or revisit the conduct, or when a convention is swapped. It runs during planning: no LabVIEW file is
changed until it has finished.

**What it gives:** one conduct file per concern in which every rule's source is settled (`observed` > `decided` >
`default`). After that, the ops read only these files. Format: `conduct/dot-labview.md`.

**Who decides:** the user. Setup proposes and shows evidence; it never picks a convention for an existing project on
its own, and never overrides what the project already does without asking.

## 1. Find out where you are

| State | Route |
|---|---|
| `.labview/conduct/` has all six files | Done. Read the ones the task needs. |
| Some conduct files are missing | Section 3 or 4, for the missing concerns only. |
| `.labview/project.json` is schema 1 (the pilot project pilot) | Offer the migration (`dot-labview.md`). Without the user's yes, read it as it is and write conduct beside it. |
| No `.labview/`, and LabVIEW code exists | Section 2, then section 3. |
| No `.labview/`, and no or almost no LabVIEW code | Section 2, then section 4. |
| The repo is not under git | Ask first (`dot-labview.md`, "No git"). |

## 2. Project facts

Collect the facts for `project.json` (template `conduct/templates/project.json`), detecting what you can without
LabVIEW:
- `project_file`: the `.lvproj` files in the repo. If there are several, ask which ones are in scope.
- `labview_version` and `save_version`: read them from the files' version stamps and the `.lvproj`'s
  `NI.LV.All.SaveVersion`. The scan script is in `kit/`. The user confirms them, because a wrong value here upgrades
  the whole project on the first save.
- `prefix`: the dominant file-name prefix in `source_root`. For a new project, ask.
- `source_root` and `git`: from the tree.

Write `project.json` and commit it.

## 3. Existing project: observe, then fill the gaps

1. **Run the analysis** (`ops/analysis.md`). It writes `.labview/analysis/`, one file per item, holding evidence
   only.
2. **Derive the observed rules** per concern. A convention counts as observed when the code follows it
   consistently in an area. Where areas differ (e.g. RT core vs GUI), write one entry per area (`area:`). A pattern
   that is followed in some places and broken in others is not observed. Show it to the user as an inconsistency,
   with counts.
3. **List what is left open** per concern: rules the defaults have but the analysis found no convention for.
4. **Settle the open rules with the user, one concern at a time.** Show the observed rules, and for each gap the
   default with a one-line reason. The user accepts the default, gives another rule (`decided`, logged in
   `decisions.md`), or switches the whole concern off (`status: off`). Hold back on large concerns: a default for
   new code in an existing project is a proposal, and the maintenance rule still applies (the local pattern wins
   for small changes inside existing code).
5. **Observed vs default.** If the code does X and the default says Y, the observed rule wins and is written. The
   default is not mentioned again unless the user asks to change the project's convention, which is then a
   `decided` rule for new areas only.

## 4. New project: choose from the defaults

Go through the six concerns in this order: naming, layout, af-shapes, errors, icons, hygiene. Per concern, show
the default file's rules in short form. The user accepts them, changes single rules (`decided` + `decisions.md`), or
switches the concern off. For icons, also settle the per-class banner abbreviations and colours, and the class
glyphs, in `icon-spec.json` (`ops/icons.md`, "Icon standard").

## 5. Write and commit

1. For each concern, copy `<skill>/conduct/defaults/<concern>.md` to `.labview/conduct/<concern>.md`, then replace
   or annotate each rule with the settled version and its `source`. Rules the user removed are deleted, not left
   in commented out. Add `written: <date>`.
2. `decisions.md`: one entry per `decided` rule (template `conduct/templates/decisions.md`).
3. Commit the `.labview/` changes alone, with a message such as `docs(labview): set up code of conduct`.
4. Report to the user:
   - per concern, the counts of `observed` / `decided` / `default` rules
   - the inconsistencies found
   - the concerns switched off
   - anything left open

## Swapping or changing a convention later

- **Swap a whole concern** (e.g. another naming scheme): replace `.labview/conduct/<concern>.md` with the new file,
  which keeps the same rule ids where the meaning matches. Log the swap in `decisions.md`.
- **Change one rule:** edit it, set `source: decided <date>`, and log it.
- **Switch off:** set `status: off`. The ops then apply none of its rules, and the review reports none of them.
- Existing code is not migrated to the new rule unless the user asks (maintenance rule).
