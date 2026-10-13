# Class fields: add, change or remove a field and its accessors

**When:** a task adds a private data field to a class that exists, changes one (another type, two fields into one
cluster), removes one, or needs an accessor that does not exist yet. Also when a new member must read or write a
field and has no accessor for it.

**What it gives:** the field in the class file with the intended type (typedefs bound, not copied), only the
accessors some code uses, in the right folder, scope and dispatch, every member executable, and membership unchanged.

**Not here:** a new class (labview-mcp's class-generator agent, "New classes" below); renaming a member
(`ops/rename.md`); the events typedef of an actor's helper loop (`ops/helper-loop.md`, which uses route A here). In
local mode, or when a concern is off, follow the surrounding code instead.

## Before you start

- **Setup level:** a field in an existing class is level 3 when it follows the class's own pattern; level 4 when it
  starts a new pattern there (e.g. the first typedef'd field). Conventions used: `layout.typedef-placement`,
  `layout.class-folders`, `layout.scope`, `layout.accessors-on-demand`, `layout.accessors-for-own-data`,
  `naming.field-names`, `naming.typedef-case`, `naming.accessor-names`.
- **Maintenance scope.** Touch only the field this task names and the callers of that field. On a class you did not
  build, turning existing storage into another shape (an untyped cluster into a typedef, separate refnum fields into
  one cluster) is a refactor: it moves every Unbundle caller. Propose it and ask; never do it on the way.
- **Loadability.** Binding, accessor creation and the private-data export load the class far enough to search for
  every dependency. On code this session did not build run `python <skill>/kit/lv_loadability.py <.lvclass>` first;
  anything unresolved: stop and report the packages (a bind hung 720 s behind a modal "Find the VI" dialog, audit L3).
  > MCP-candidate: offline-loadability
- **Save version:** these tools save more than the class. `lvai_create_accessors` and `lvai_add_to_library` save
  the whole library (11 files for one typedef in an actor's library). Scan every file of the owning library, not only
  the class (`knowledge/labview-mcp.md`, "Save version").
- **Project state** per step is named below; codes and the close rules: `knowledge/labview-mcp.md`, "Project open or
  closed, per kind of call". Commit before each structural step (typedef, field + bind, accessors, each caller moved,
  each removal).

## A. Add a field

Order: typedef → field and binding → accessors → the members that use it. Bind before any accessor exists for this
field: an accessor made earlier keeps the bare type for ever. (pilot rule 2)

1. **Name:** the field label per `convention: naming.field-names`; a new typedef's file per `naming.typedef-case`.
2. **Typedef** (enum, cluster, refnum, array; skip for a plain type): `lvai_create_typedef(ctlPath, type)` with no
   `projectPath`, the file flat in the class folder (`convention: layout.flat-files`). `verifiedFromFile` must say
   typedef and `needsLabviewSave false`. Spellings and the `overwrite` trap: `knowledge/labview-mcp.md`,
   "lvai_create_typedef, lvai_resave_ctl, lvai_describe_ctl".
   - **Default values** (e.g. U32 100, Boolean T): set them NOW, before the class membership and the bind, because a
     new field instance takes the typedef's default when it is made. A VI Server helper on the `.ctl`, project
     closed: `{LV.VI}` `Front Panel` → `{LV.Panel}` `Controls[]` → `{LV.Control}` write `Value` → `{LV.VI}` Invoke
     `Default Vals.Make Curr Default` → `Save.Instrument`; read `Default Value` back (measured in an evaluation, 2026-10).
     Copy `kit/example_ctl_defaults.xml` and give its `wanted` and `type template` constants your typedef's type.
   - **Owner** per `convention: layout.typedef-placement`. No labview-mcp tool adds a `.ctl` to a class: add it right after it is created,
     before anything uses it, with `kit/pa_class_folder_add_files.xml` (`class path`, `folder` = `TypeDefs`,
     `item paths` = the `.ctl`, `item type` = `VI`, which is right for a `.ctl` (measured); project open and active);
     added later it is renamed and its callers relink (`knowledge/labview-mcp.md`, "LabVIEW scripting quirks",
     "Class description, typedef membership, virtual folders"). Never fall back to the class or library root.
     The helper always CREATES the folder: when the class already has `TypeDefs`, `AddItem` (Type `Folder`) with the
     existing name is REFUSED with 56001 (nothing added, nothing saved; measured in an evaluation, 2026-10). Then add into the existing
     folder: `{LV.Library}` Invoke `Get All Descendents` (Type `Folder`) → the item whose `{LV.ProjectItem}` `Name`
     is `TypeDefs` → `{LV.ProjectItem}` Invoke `AddItem` (Name, Path, Type `VI`) on it, then Save All of the class
     (`kit/pa_class_folder_add_existing.xml`, same inputs as `pa_class_folder_add_files`). LabVIEW makes the added typedef public: set it private with `kit/set_scope.py`
     (project closed, `convention: layout.scope`), unless a file outside the class uses it, which then keeps it public.
     > MCP-candidate: add-to-class
   - Where the area keeps typedefs in its library: `lvai_add_to_library` into that folder (it refuses a missing
     folder, and saves every library member). > MCP-candidate: library-virtual-folder
   - Commit. **Sweep point 1:** cold sweep of the class folder (`ops/sweep.md`).
3. **Field and binding: one structural step, project OPEN and ACTIVE across it, no sweep in between.**
   - Plain type: `lvai_add_class_field(lvclassPath, fields="<type>.<name>", projectPath)`. Done.
   - Typedef: a placeholder `bool.<name>`, then `lvai_bind_class_fields(lvclassPath, bindingsJson=[{"field": "<name>",
     "ctlPath": "<ctl>"}], projectPath)`; `ok` is gated on `boundInFile`.
   - Class-typed: placeholder `string.<name>`, bind with `ctlPath` = the `.lvclass` and `force: true`. `ok: false` is
     the expected answer; `lvai_describe_class` shows `Refnum`, `RefType=UDClassInst`. (pilot rule 29)
   - Array of class: typedef `array{bool.<name>}`, then `<skill>/kit/pa_array_element_replace.xml` (`ctl path`,
     `element path` = the `.lvclass`; `is typedef after` true), placeholder `string.<name>`, commit, then a separate
     bind with no `force`. Never inside `lvai_create_class`: that crashed LabVIEW. (pilot rule 51)
   - Keep `nextFromField` from the add's answer: it is the field index for step 4.
   - `lvai_bind_class_fields` leaves the project OPEN on purpose (its answer: closing and then cycling the project
     killed LabVIEW). Follow the tool's answer: do not close right after the bind unless the next step needs it
     closed. Commit. **Sweep point 2** is a cold sweep and needs it closed: close it once for the sweep
     (`knowledge/labview-mcp.md`, "Opening and closing a project"), never close and reopen in a cycle (a single close
     after the bind did not crash, evaluation 2026-10).
   > MCP-candidate: typed-add-class-field
4. **Accessors, only when a member uses them** (`convention: layout.accessors-on-demand`,
   `layout.accessors-for-own-data`). A new member of the class reads and writes the field through its accessor, so
   the accessor is made when the first such member is built, in the direction it uses:
   `lvai_create_accessors(lvclassPath, fromField=<index>, fieldCount=1, budgetSeconds=1, accessUi="Read"|"Write",
   dynamicDispatch=false, virtualFolderName=<the class's accessor folder>, projectPath)`. `projectPath` is the
   project to tidy; the tool needs it open and active first (`lvai_open_file`), as its own text says (it opened a
   closed one anyway in an evaluation, 2026-10, answering `projectOpened`). When the user asks for the accessors
   outright, both directions are wanted: two calls, Read then Write.
   `<index>` = the field's 0-based position in the private data, which is the `nextFromField` the add answered (e.g.
   a class with fields `events` and `settings` added last: `settings` is 1). Then:
   - the answer must list one VI; if the wizard made both, remove the unused one (`remove_members.py` below, project
     closed). `accessUi` gives one direction (measured: `Read` made one VI, evaluation 2026-10).
     > MCP-candidate: accessor-options
   - **Names** stay the wizard's (`convention: naming.accessor-names`). A custom accessor that groups fields is a
     method (`lvai_add_class_method`), named per `naming.method-case`.
   - **Dispatch:** static. A private dynamic-dispatch VI is broken ("error of type 2000000"). (pilot rule 30)
   - **Scope** per `convention: layout.scope`: `python <skill>/kit/set_scope.py <.lvclass> <scope> "Read <f>.vi"`,
     project closed; check with `--check` or `lvai_describe_class`.
   - The value terminal is named after the `.ctl` (typedef field) or the class's qualified name (class field), not
     after the field: read it with `lvai_vi_terminals` before a caller uses it. (pilot rule 48)
   - Icons and diagram for the new accessor: `ops/icons.md`, `ops/cleanup.md` (only VIs this task made).
   - **Descriptions** per `convention: hygiene.descriptions`: the wizard writes only a generic text into an accessor,
     and a new typedef has none (evaluation 2026-10). Write both with `kit/pa_set_vi_descriptions.xml` (project
     closed; one record per file). On a `.ctl` the helper is unmeasured: read the description back.

## B. Change a field

Never edit a field in place. Add the new one, move every caller onto it, remove the old one last.

1. **Add** the new field by route A, keeping the old field and its accessors.
2. **Find the callers** of the old field's accessors, offline: `grep -a -l "Read <f>.vi\|Write <f>.vi"` over every
   `.vi` of the repository; members that Unbundle the class wire are found only by an export or `vi_nets.py`. Find
   string references too (`ops/rename.md`, step 1).
3. **Move each caller**, one commit each, nothing else in it:
   - a member that is not hooked anywhere: the labview-vi-editor agent, briefed with the new accessor's VI name and
     terminal names and the conventions above (`session/brief.md`). It regenerates the VI (layout and icon lost),
     and a re-add resets scope and virtual folder: check both afterwards and restore them with `set_scope.py` and the
     folder.
   - a member hooked into an override or called by a loaded member: unhook, regenerate, re-hook
     (`ops/override.md`, "change a hooked method"). > MCP-candidate: add-class-method-rerun
   - cold sweep of the caller and its callers.
4. **Remove** the old field by route C.

## C. Remove a field (last, when no caller uses it)

1. **Accessors out**, project CLOSED: `python <skill>/kit/remove_members.py <.lvclass> "Read <f>.vi" "Write <f>.vi"
   --delete-files` (the item first, then the file). Remove their AIXML sources. Commit.
2. **The field out**, project OPEN and ACTIVE: labview-mcp's `lvpdc_export.xml` (`class path`, `out name`; an
   unlisted `.ctl` in the class folder) → `<skill>/kit/pa_ctl_delete_fields.xml` (`ctl path`, `field 1`, `field 2`;
   `labels after` lists the fields that stay) → `lvpdc_import.xml` (`class path`, `ctl path`). `lvai_describe_class`:
   the field is gone and the other bindings remain. Commit the `.lvclass` only; close the project; delete the export
   `.ctl` as a plain file. > MCP-candidate: remove-class-field
3. **Re-save every member**, project CLOSED: `python <skill>/kit/sweep_paths.py <class folder> --no-control --json`
   → `<skill>/kit/pa_resave_vis.xml` (`vi paths`; omit `project path`); `ok count` = the VI count. Members keep the
   old field names in their link info until then. Saved with no project open, so check the save version first and
   ask if it would upgrade (`knowledge/labview-mcp.md`, "Save version", step 3). (pilot rule 68)
4. **The old typedef out** (if no other user): `remove_members.py <owner> "<old>.ctl" --delete-files`, project
   closed, owner item before the file. Commit.

## After any route

- Cold sweep of the class and its callers, and `python <skill>/kit/check_membership.py <class folder>` (`ops/sweep.md`).
- **Round-trip test** (`convention: hygiene.test-after-edit`): if `.labview/checks.json` lists a test whose
  `class_under_test` is this class, run it (`ops/run-checks.md`). It must pass as before.
- Re-scan the versions; list every file re-saved in the side effects.

## New classes: brief the class-generator agent

labview-mcp's `labview-class-generator` makes classes, typedef fields and accessors. Brief it (`session/brief.md`)
with the class name (`naming.class-library-names`), each field in the user's words with its label
(`naming.field-names`), the target folder (`layout.library-per-actor`, `layout.flat-files`), the parent and
interfaces (the user's call, `af-shapes.architecture-by-user`), the `.lvproj`, and these rules in the prompt:
- **accessors:** by default it makes every accessor, dynamic dispatch. Say "make only: `<field> Read|Write`, static,
  `<scope>`" or "no accessors" (`layout.accessors-on-demand`, `layout.scope`);
- typedef owner and folders (`layout.typedef-placement`, `layout.class-folders`), typedef names
  (`naming.typedef-case`), a description (`hygiene.descriptions`), the project's save version;
- the test hand-off: name the framework that is installed, or say "no hand-off". A round-trip test only for a class
  that packs data, in the test library (`hygiene.test-convention`, `hygiene.test-library`).
**Check afterwards:** `lvai_describe_class` (fields, bound typedefs), the `.lvclass` items (accessors made, their
scope and dispatch, folders), `check_membership.py`, a cold sweep, the version scan, and the `.lvproj` (a class
created with a parent adds the parent as a top-level item: `lvproj_drop.py`, project closed). Accessors nobody asked
for: remove them (route C, step 1).

## Report

```
field <add|change|remove> <class> <field> <plain|typedef|class|array-of-class>
typedef <ctl> (new|existing) owner <class folder|library> (created|added)  bound <describe_class reading>
accessors made <list: name, R/W, scope, static>  callers moved <n> (regenerated <n>, re-hooked <n>)  removed: <...>
re-save <ok>/<n>  sweep <ok>/<n>, control 0 7, membership ok  round-trip test <pass|none>  versions unchanged yes/no
side effects: <library files re-saved, project items>   commits <hashes>
```

## Traps

- `lvai_add_class_field` takes plain types only, and appends; `fromField: -1` on `lvai_create_accessors` resumes from
  the member count, wrong on a class with methods: pass the index. (pilot rule 37)
- `lvai_bind_class_fields` runs its import after a failed export and blames the `.ctl` in its note: read the steps.
  > MCP-candidate: bind-fields-step-errors
- The `accessorsAlreadyPresent` warning counts every accessor of the class; it matters only for this field's own.
- `lvpdc_export` answering 1073 with the project open may be a degraded LabVIEW, not the project state: report it.
- A placeholder for an array-of-class terminal is a scalar `path`: make that stub with `array{path}`.
  > MCP-candidate: placeholder-array-of-class
