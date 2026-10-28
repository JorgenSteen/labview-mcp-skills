# Icons: make, apply and read back

**When:** at the end of a step that added or regenerated VIs, classes or libraries (`convention: icons.when`); after
a regeneration that lost an icon; when the user asks for icons for classes they name (`convention:
icons.existing-icons`).

**What it gives:** the VIs this task added or regenerated carry an icon by the project's standard: the class or
library template (an `NI_Library` layer) plus the VI's own glyph. Proved by a pixel read-back (0 px), unchanged file
versions and a sweep that matches the one before. Existing icons stay as they are.

**Not here:** the standard itself (`conventions/defaults/icons.md`; the project's copy in
`.labview/conventions/icons.md`). In local mode, or when the icons concern is off, follow the surrounding code
instead: copy a sibling's icon or re-apply the class template (mode **adopt** below). Settling abbreviations, colours
and class glyphs with the user is `conventions/setup.md`, section 4.

## Before you start

- **Level:** it writes. New code is level 4 with the icons concern set up; local mode is level 3.
- **The list:** only the VIs this task added or regenerated, written down before step 1. Never a tree.
- **Mode, per class or library:**

  | Mode | When | What happens |
  |---|---|---|
  | **new** | a class or library this task created | generated from `icon-spec.json`: `icons.banner`, `icons.class-glyph`, `icons.vi-glyph`, `icons.library-icon` |
  | **adopt** | an existing class with icons, local mode, or the concern off | `icons.existing-icons`: nothing is redrawn. A new or regenerated VI gets a sibling's icon copied or only its own glyph, then the class's existing template re-applied. The class icon is not set. |
  | **on request** | existing classes the user named | as **new**, for those classes only, after a BEFORE read-back |

- **Tools draw icons by default:** `lvai_generate_vi` (`icon: "none"` skips it), `lvai_create_accessors`
  (`setIcons: false`), `lvai_add_class_method` (a derived icon, no opt-out). With the concern off, pass the opt-outs
  and report the rest as side effects (measured 2026-10-26).
- **LabVIEW is running** (`session/start.md`), no other LabVIEW agent, project **closed** for every class and
  library icon call (open: Error 1562; close as `knowledge/labview-mcp.md`, "Opening and closing a project" says).
- **Commit before you start and after each class or library** (or record `HEAD` when the tree is clean).
- **Loadability:** on a class or library this session did not build, `python <skill>/kit/lv_loadability.py <folder>`
  first; stop on anything unresolved (`ops/sweep.md`, step 2). > MCP-candidate: offline-loadability
- **Save version, this op's variant.** The icon helpers save with the project closed, which writes the IDE's version
  (measured: 6 member VIs and the `.lvclass` went from 2020 to 2026). Scan the VIs and the `.lvclass`/`.lvlib`
  first with `python <skill>/kit/lv_save_version.py`. If the project is older than the IDE, that is a conflict:
  **ask the user before the first save** and do not choose. Facts to give: a `.lvversion` file or a class/library
  Save version may prevent it (documented by NI, not measured here); `lvai_set_vi_icon` saves the VI in place with
  the same risk. Re-scan after each class. Route: `knowledge/labview-mcp.md`, "Save version".
  > MCP-candidate: save-version-check

## Icon standard: the per-project icon-spec.json

It lives in `.labview/conventions/icon-spec.json`, beside the project's `icons.md`. `icons.md` holds the rules;
the spec holds the values `<skill>/kit/make_icons.py` draws from. Start from `<skill>/kit/icon-spec.example.json`
(its `_doc` explains each key).

**Keys the engine reads today** (`$schema_version` 1):

| Key | Meaning |
|---|---|
| `paths.src`, `paths.out` | the source tree and the output folder. Keep `out` short (MAX_PATH). See the first trap. |
| `classes` | owner → `banner` (A–Z 0–9 `- _ . >` space, at most 7 characters), `colour` (RRGGBB, web-safe: multiples of 0x33, or LabVIEW shifts it), `lib_glyph`. The owner is the class folder name, a flat folder, the top-level owner or a library owner. |
| `libs` | library name → `banner`, `colour`, `lib_glyph` |
| `no_template` | `classes` entries without a `.lvclass` (test folders, launchers) |
| `library_owners` | owners whose `.lvlib` is the template of their VIs (also listed in `no_template`) |
| `flat_folders`, `top_level_owner` | first-level folders drawn flat; the owner of VIs directly in `src` |
| `overrides` | owner → VI file name → `glyph` (and `lib_glyph`) |
| `rules` | ordered name rules: `match` (`contains`, `prefix`, `suffix`, `equals`), `pattern`, `glyph`; `first: true` runs before the built-in Read/Write/Send/Do rules. `use_builtin_rules` (default true). |
| `glyphs`, `lib_glyphs`, `palette` | 16x16 and 10x10 glyphs as row strings over palette keys (`.` is transparent); extra palette keys (one character → RRGGBB) |
| `planned` | VIs not built yet (drawn with `--include-planned`) |
| `preview.label_remove` | prefixes cut from the preview labels |

**Keys the standard adds** (`icons.banner`, `icons.class-glyph`, `icons.library-icon`):

| Key | Meaning |
|---|---|
| `banner_font` | `small_fonts` (default: LabVIEW Small Fonts, as the reference icons) or `3x5` (only on the user's request) |
| `banner_text_colour` | default `000000` (black) |
| `class_glyph` | in each `classes` entry: a key into `glyphs`, drawn on the right of the body. Banner + class glyph = the class template, the start of every VI of the class. A VI glyph may overlap it. |
| `lib_glyph` | optional for libraries and classes: `null` allowed; the banner is always required |
| `libraries` | `keep` (existing library icons are not touched) or `generate` |
| `messages` | `keep` (message classes keep their icons) or `generate` |

> **Kit TODO.** `make_icons.py` does not implement these yet: it draws a white 3x5 banner, puts a 10x10 `lib_glyph`
> at the left of the body in place of a class glyph, refuses `lib_glyph: null`, ignores `libraries`/`messages`, and
> has no option to draw only listed VIs. Until the kit is updated, generation uses the current engine, and the
> preview goes to the user for approval with these differences named. A banner-only owner needs a fully
> transparent 10x10 glyph as a stand-in for `null`. (KT-4) > MCP-candidate: icon-generator

## Steps

1. **Spec** (mode new or on request; once per project, again when a row changes).
   - Missing spec: write it from the example with the values setup settled. Derive what setup did not settle
     (banner height, colours, glyph style) from the reference icons, `convention: icons.reference`: read a few
     back with `lvai_read_icons` (classes and libraries too) into the scratch folder and compare.
   - `python <skill>/kit/make_icons.py --spec <spec> --src <src> --out <out> --check`: exit 1 lists every spec
     error; it prints per owner the VIs and glyphs it would draw.
2. **Generate:** the same command without `--check`. It writes PNGs only (offline), for the whole `src`; only the
   listed VIs are applied later. Output in `out`: one composite PNG per VI (mirroring `src`), `_own/` (the VI's
   glyph layer), `_classes/`, `_libs/`, `manifest.json` (per VI: `composite`, `own`, `class`), `preview.png`.
   **Show `preview.png` to the user and get approval** the first time and after every spec change; commit the
   approved spec and `out`.
3. **BEFORE read-back** (every class whose existing members or icon this op will save): `lvai_read_icons` with
   `paths` = the listed VIs plus the class and library files, `outDir` = `<rb>_before\` (a **short** absolute folder),
   `baseDir` = `<src>`. One call; this makes any change measurable beside git.
4. **The VI's own layer,** only for a VI without one (new, regenerated, or still LabVIEW's default icon):
   - mode new: `lvai_set_vi_icon` with `iconImagePath` = its `_own` PNG and a `readBackPath` in the scratch folder.
     It flattens the icon, so it always comes before the template.
   - mode adopt: read a sibling's icon (`lvai_read_icons`) and set it the same way, or the VI's own glyph only.
   - A VI that already has an `NI_Library` layer plus its own layer skips this step; steps 5–6 re-apply the template
     and change only the banner pixels (or `lvai_set_vi_icon` with `keepOwnLayer: true` for that one VI).
   - A VI with no class or library template (a launcher, a test VI) gets its composite PNG here and is done.
5. **Class or library template, and 6. apply to the listed members** (mode new or on request, or when the class's
   spec row changed; never in mode adopt, never for a library under `libraries: keep`), one call per owner:
   `lvai_set_owner_icon(ownerPath, pngPath, applyToMembers: true, memberPaths, readBackDir)`.
   - `ownerPath` = the `.lvclass`, or a plain `.lvlib`; `pngPath` = `_classes/<class>.png` or `_libs/<lib>.png`. A
     library that holds a class has its own icon, set here only when the library is new or its row changed (then
     without `applyToMembers`).
   - `memberPaths` = the listed VIs, one absolute path per line: naming only this task's VIs keeps the other members
     untouched on disk. `readBackDir` short, in the scratch folder.
   - It refuses with the project open (`projectOpen`), opens every member, applies the template layer, saves each
     member and the owner, and reads back: `ownerIcon.pixelsDifferent` 0 and `templateMissing` 0 on every member,
     every member code 0. It reports `ownerLvVersionBefore/After`: a change is a save-version conflict (above).
7. **Read back the listed VIs:** `lvai_read_icons` with `paths` = the listed VIs, `outDir` = a short folder `<rb>`,
   `baseDir` = `<src>`, `expectedDir` = `<out>` (the generated composites). `written` true and status `OK` for every
   VI (it refuses a PNG path over 259 characters and checks that each PNG was written). In mode adopt, compare the
   class icon with `<rb>_before\`: 0 px.
8. **Verify:** re-scan the versions; sweep the touched folder (`ops/sweep.md`) and compare with the sweep before;
   `git status` shows at most the listed VIs, the `.lvclass`/`.lvlib` and `out`. Commit. An apply can also re-save ANOTHER class's
   `.lvclass` (BOM and `FlattenedPrivateDataCTL` only, a harness run 2026-10): restore it from git with the project closed and report
   it.

**Changing one class's icons later** is existing code: only on the user's request (`icons.existing-icons`). Edit the
row, regenerate, show the preview, then steps 3–8 for that class.

## Report

```
icons <n> VIs  mode <new | adopt | on request> per owner  spec <path> (new | existing)  preview approved <yes | no>
before read-back <yes | not needed>  own layers <n> (skipped: <n> with a layer)  templates: classes <n> libraries <n>
applied <n>: member codes all 0, templateMissing 0 <yes | no>   read-back <ok>/<n> OK (written <n>)   owners <ok>/<n> 0 px
versions <unchanged | conflict: asked, <answer>>   sweep <same as before | changed>   git <files>   commits <hashes>
kit TODO differences shown to the user: <list | none>   LabVIEW calls <n>   issues: <exact text | none>
```
Every re-saved file and version change also goes into the end-of-session side effects (`session/close.md`).

## Traps

- **Spec location and paths.** `make_icons.py` resolves `paths.src`/`paths.out` against the parent of `.labview/`
  only when the spec sits directly in `.labview/`. From `.labview/conventions/` they resolve against that folder:
  always pass `--spec`, `--src` and `--out`.
- **Owner by folder name.** The engine takes a VI's owner from its folder name and builds `<folder>.lvclass` from
  it. If the class file is named differently, run per class with `--src` = the class folder and `top_level_owner` =
  the class name (KT-3).
- **1562 from `lvai_set_owner_icon` with the project closed and nothing visibly locked:** the class is probably held
  by an earlier `LVClass.Open` in this LabVIEW. The cure is a restart with that call first, only with the user's
  go-ahead (`session/restart.md`). Fallback, only with the user's ok (`convention: icons.labview-template`):
  `lvai_set_vi_icon` with each member's composite (same look, no `NI_Library` layer, the class icon stays old).
  Details: `knowledge/labview-mcp.md`, "lvai_set_vi_icon and icon work".
- `lvai_set_owner_icon` with over 100 members (its list-file helper) is unmeasured.
- Any regeneration of a VI drops its icon: steps 4–7 again for it.
