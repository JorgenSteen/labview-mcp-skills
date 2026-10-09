# Rename a class member, class, library or typedef

**When:** the task or the user names an item to rename: a member VI of a class (method, hook, accessor), and, with
the user's go-ahead for the first one, a class, a library or a typedef. Also when a naming rule the user chose
changes one named item's file name.

**What it gives:** the item under its new name, renamed **through LabVIEW** with every user loaded, so the change
cascades into each user's link. The class keeps the member's entry, scope, virtual folder, icon and panel flags.
The old file is gone, and nothing refers to the old name.

**Not here:** the name itself (`convention: naming.method-case`, `naming.function-case`, `naming.typedef-case`,
`naming.class-library-names`, `naming.accessor-names`); renaming a private data field (that is a change of field,
`ops/class-field.md`, route B). In local mode, or when the naming concern is off, follow the surrounding code
instead.

## The rule (the user's, without exception)

- **Only through LabVIEW.** Never rename on disk, in Explorer or with `git mv` for a `.vi`, `.ctl`, `.lvclass` or
  `.lvlib`: the owner lists the item by its file URL, and every user stores the link by name. Only an AIXML source
  (`.xml`, a text file) is renamed with git.
- **Every user is in the project and loaded before the rename.** That means every class, library and VI that calls,
  contains, inherits from or overrides the item. Then LabVIEW relinks each one.
- **A user that is not in the project, or cannot load:** list it and ask the user. Adding it to the project changes
  their `.lvproj`; leaving it out leaves it broken. Do not rename until the user has answered.
- **Scope.** Rename only the items the task names or the user asks for, one at a time. No style sweep over a class
  or a tree, even where names break the naming convention (maintenance rule, `SKILL.md`).
- **Never renamed:** AF and interface overrides keep the parent's name (`convention: naming.override-names`), and so
  do Message Maker products.

## Before you start

- **Setup level 3** (a minor edit) for a rename the user asked for; the new name follows the convention files, or
  the neighbours in local mode. A rename that a naming change drives over several items is level 4: ask first.
- **What is measured:** the member route below (`Save.Instrument` to the new path with the class and the callers
  loaded; pilot rules 64, 85). **Classes, libraries and typedefs: the user renames them in the Project Explorer**
  (the user's choice, 2026-10-09). The skill does everything around it: steps 1–4 (every user found, loadable, in the
  project, committed, versions scanned), then hands the user the list of users to load and the new name, and after
  the user's rename runs steps 6–8 (old file gone, string references, checks). A scripted route is measured on a
  scratch copy only if the user asks for one.
  > MCP-candidate: rename-member (proposal: extend it to `.lvclass`, `.lvlib` and `.ctl`, with the same "load every
  > user, report each relink" contract)
- **A dynamic-dispatch member** that child classes override: each override must be renamed with it, or the children
  break. That is several renames in one step and is unmeasured: list the overrides and ask.
- LabVIEW is running (`session/start.md`). Git is clean or committed; record `HEAD`.

## Steps

1. **Find every user, offline** (no LabVIEW call).
   - **Callers:** `grep -a -l "<old file name>"` over every `.vi`, `.vim`, `.ctl`, `.lvclass` and `.lvlib` of the
     **whole repository**, not only the class's tree: in a product with several trees the callers sit in other
     actors' libraries (5 callers in 2 trees for one method). The link is stored in the caller by file name. Subtract
     the item itself and any VI whose description only mentions it. For a class or library, grep its qualified name
     (`<Lib>.lvlib:<Class>.lvclass`) as well. (pilot rule 87)
   - **Children** (for a dynamic member or a class): the `.lvclass` files whose `Parent Libraries` name the class.
   - **String references** (qualified-name constants, path constants) are not visible in a `.vi`, because the
     diagram is compressed. Grep the AIXML sources (`.xml`) and the docs. Without sources, export only the callers
     and the class's own members, and only those that load (step 2), with `lvai_convert_vi_to_aixml` into a scratch
     folder outside the repo; never export a whole tree. Report the rest as "string references outside the callers:
     not checked".
2. **Every user must load.** Run `python <skill>/kit/lv_loadability.py` on the class and on every user found
   (`knowledge/labview-mcp.md`, "A failed, hung or blocked call"). A user with an unresolved dependency cannot be
   relinked: list it with its missing packages and ask (see the rule). > MCP-candidate: offline-loadability
3. **Choose the project.** The product project that holds the class and every user. If no project holds them all,
   list the users outside it and ask: add them to that project (their `.lvproj` changes), or use a scratch `.lvproj`
   outside the product tree that holds only the class's library and the users' libraries (members only; a renamed
   class or library must be renamed in the real project). A large project opens slowly: `timeoutSeconds` 300 or more
   (`knowledge/labview-mcp.md`, "Opening and closing a project").
4. **Commit**, then check the save version of every file the rename saves (the class, the item, each caller):
   `knowledge/labview-mcp.md`, "Save version".
5. **Rename** (member route), project OPEN and ACTIVE:
   - Load every caller except one **in the project's instance**: `lvai_open_file` with `viPath` = the caller and the
     project pair (`projectPath` + `projectName`). A loose open lands in another instance and does not relink.
   - Run `<skill>/kit/pa_rename_member.xml` with `vi path` (old), `new vi path`, `caller path` (the remaining caller),
     `class path`. Every error output reads 0, `vi path after` is the new path and `vi name after` the new qualified
     name. **No caller at all:** pass the renamed VI itself as `caller path` (unmeasured: check every output).
   - Save the other callers: `<skill>/kit/pa_resave_vis.xml` with `vi paths`, `project path` = any text (the active
     project's instance). The relink reaches a caller's file only with this save.
6. **Old file and source**, project CLOSED (`knowledge/labview-mcp.md`, "Opening and closing a project"):
   - delete the old `.vi` with `git rm` (it is no longer a member); `python <skill>/kit/check_membership.py
     <class folder>` reads 0 not a member, and the old name is not listed;
   - `git mv` its AIXML source, if one exists, and change the names inside it as text.
7. **String references** from step 1, each in the VI and in its `.xml` source: a constant with `lvai_set_constant`;
   a VI description with `<skill>/kit/pa_replace_description.xml` (`vi path`, `search`, `replace`; project closed);
   docs as text. These go through LabVIEW, like the rename.
8. **Check** (below), then commit the new file, the deletion, the callers, the `.lvclass` and the sources together.

## Checks / evidence

- `grep -a -l "<new file name>"` hits every caller found in step 1; `grep -a -l "<old file name>"` hits nothing but
  history files.
- Cold sweep of the class folder and every caller (`ops/sweep.md`): state 1, the negative control reads `0 7`,
  membership 0 missing. A caller missed by the rename reads state 0: "VI has an error of type 2000000" while the old
  file exists, "Missing subVI <lib>:<class>:<old>.vi" after it is deleted.
- `lvai_describe_class`: the new name, in the old virtual folder, with the old scope.
- Re-scan the versions (`knowledge/labview-mcp.md`, "Save version", step 4).
- Tests or runs that use the class (`.labview/checks.json`): run them, same result as before (`ops/run-checks.md`).

## Report

```
rename <kind> <owner>: <old> -> <new>   users <n> (callers <n>, children <n>) relinked <n>   errors all 0: yes/no
not renamed: <users not in project or not loadable, asked: <answer>> | none
old file deleted yes/no   source renamed yes/no/none   string refs fixed <n> | not checked outside callers
sweep <ok>/<n> state 1, control 0 7, membership ok   versions unchanged yes/no   tests: same result | none
side effects: <project items, .lvproj/.aliases rewritten, files re-saved>   commits <hashes>
```

## Traps

- **A caller not loaded during the rename keeps the old link, silently.** The helper still answers all 0, and opening
  the caller later shows no dialog: it loads and stays broken. Hence step 2 and the grep for the new name after the
  save. (pilot rule 85)
- **Repair of a missed caller** (measured): `lvai_swap_subvis` cannot repair a missing-subVI node (it reads 1055 as
  `noActiveProject`). `lvai_close_vi` on the caller, re-run `lvai_add_class_method` from its AIXML, then swap the stub
  onto the new VI; this loses the caller's layout and icon. Cheaper, unmeasured: restore the old file from git with
  the project closed and rename again with the caller loaded. (pilot rule 86) > MCP-candidate: swap-subvis-fixes
- **The old file stays on disk** after `Save.Instrument` to a new path: step 6 deletes it.
- **Never rename by regeneration** (an AIXML round trip to a new path): it drops the icon and the layout, and a re-add
  resets scope and folder (`knowledge/labview-mcp.md`, "lvai_add_class_method").
- **Opening the project writes it** (App Builder specs migrated, `.aliases` rewritten; the close saves the
  `.lvproj`): list it in the side effects (pilot L4 audit run).
