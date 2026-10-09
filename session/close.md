# Close: end a LabVIEW session so the next one starts from files alone

**When:** "close the session", "wrap up", "write the status", "write the MCP report", "hand over", or before the last
commit of a session. Every session that made LabVIEW calls or changed files closes, a short or docs-only one too.

**What it gives:** a status file the next session (often a fresh bot with no memory) can start from, an MCP report,
a side-effects list the user can read in one place, a knowledge audit, and a final commit. Nothing learned may live
only in a scratchpad, a transcript or an agent's memory. The close itself makes **no LabVIEW call**.

**Not here:** closing LabVIEW (`session/restart.md`; a LabVIEW this session started may be closed there, otherwise it
stays running); the last sweep, tests and runs, which a subagent does before the close (`ops/sweep.md`,
`ops/run-checks.md`); briefing a subagent to run the close (`session/brief.md`, type f).

## Before you start
- **Project facts** come from `.labview/project.json` (schema 2, `conventions/dot-labview.md`): `status_file`,
  `briefs_folder`, `mcp_reports_folder`, `proof_folder`, `knowledge_files`, `commit_attribution`. A schema 1 file is
  read as it is: its `rules_file` and `guide_file` stand for `knowledge_files`.
- **A key is absent** (or there is no `project.json`, as in local mode): ask the user once where those files go. If
  the user leaves it open, put them all into one session folder `session-<X>/` (`<X>` = the session id) in a place
  the user can see, outside the product tree when that tree may not be written. Name the folder in the report.
- **The close folder** is the folder of `status_file`, or that session folder. Files that have no place of their own
  go there: the main-session notes, candidates for files the session may not edit, proposed kit scripts.
- **The start HEAD:** the commit the session started from (the parent of its first commit). The side-effect and
  reachability checks run from it.
- **Who closes:** the main session, or a subagent briefed as type (f). A closing subagent sees only files and its
  brief, and does not edit this skill.
- `convention: <concern>.<rule-id>` below means the project's rule; in local mode, or when the concern is off,
  follow what the repo's history does instead.

## Steps
Order: 1 state, 2 main-session events, 3 side effects, 4 status, 5 MCP report, 6 knowledge audit (may add to 3–5),
7 commit, 8 report.

1. **LabVIEW's state, no LabVIEW call:**
   `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>/kit/lv_windows.ps1`. Record the PID (this
   session's, per the `session/start.md` report line, or the user's), unsaved titles, dialogs and the `LVAutoSave`
   count. After a crash or a hang this goes first in the status, with what was not verified.
2. **Main-session events.** Before a subagent closes, the main session writes its own events into
   `<close folder>/main-session-notes.md`: the user's decisions with wording and date, go-aheads and permission
   changes, dialogs it answered, resets, launch messages not saved as briefs, published URLs.
3. **Side effects** (mandatory, the user's rule 2026-10-08: "if a file is removed or something. Make it clear in a
   report"). Collect from the agents' reports, the start and restart report lines, and git since the start HEAD:
   - **items removed:** files (`git log --diff-filter=D --name-only <start>..HEAD`), project, library and class
     items, Dependencies sections dropped (`git diff <start>..HEAD -- '*.lvproj' '*.lvlib' '*.lvclass'`);
   - **files re-saved or upgraded:** every LabVIEW file the session changed, scanned with
     `<skill>/kit/lv_save_version.py`, with from/to version where it changed; a Save version property written;
   - **project files rewritten:** `.lvproj` (BOM, `NI.LV.All.SaveVersion`, Dependencies), `.lvlps`, `.aliases`,
     `.<project>.UserState\` (also untracked: `git status --short`);
   - **LabVIEW started, closed, restarted or killed**, by whom, with PIDs and the go-ahead quoted;
   - **the Nigel chat opened**; **`LVAutoSave` cleared** (count, and the user's ok).
   Empty = "none". This list goes, unshortened, into the status file, the MCP report and the report to the user.
   > MCP-candidate: close-project-guard
4. **Status file** (`status_file`): a new section at the top, `# STATUS: Session <X> <done | stopped>, <date>`. An
   "in progress" block of the same session becomes this section. Older sessions stay below, shortened to a summary;
   their open-items and start-here lists get a one-line "superseded by session <X>".
   - **Built or changed**, with short commit hashes and proof folders.
   - **Verification:** one table `check | target | reading | source`. The readings are numbers (sweep `N/N` state 1
     with its negative control, membership counts, test Pass per test VI, run readings, icons). "stopped at <step>:
     <reason>" is a valid reading. Say which checks were not run this session.
   - **Side effects** (step 3).
   - **Deviations:** every step that ended on a fallback, with its measurement; rule breaks by agents (parallel
     calls, heredocs) and whether they did harm.
   - **The user's decisions** this session, quoted where the wording matters, with the date.
   - **Open items**, numbered; each names its owner (the user, the next session, the skill's maintainer, labview-mcp)
     and its state.
   - **Next session: start here**, numbered. The first steps follow the next task: when it is a decision of the
     user's, they make no LabVIEW call. If the planned work may need a restart of a LabVIEW the session will not
     start itself, say so, so the next session asks for the go-ahead at its start. A blanket go-ahead ends with this
     session.
   - **LabVIEW at the end** (step 1).
5. **MCP report** (`<mcp_reports_folder>session-<X>.md`; model: the latest report there):
   - **Environment:** LabVIEW version and bitness, labview-mcp version, who started LabVIEW, restarts and crashes
     (none = "none").
   - **Use:** table `step | agent (type, fresh or resumed) | LabVIEW calls | wall clock | result`; routes that worked.
   - **Issues:** table `# | issue | kind (tool bug, wrong docs, trap, LabVIEW fact, crash, agent rule break) | where
     (brief, commit, proof file) | workaround | candidate id`. Each has evidence: the exact error text or code and
     the commit.
   - **Proposed MCP candidates:** for a known id in `<skill>/MCP-CANDIDATES.md`, the new evidence; for a new pitfall,
     an entry in its format (id, Gap, Proposed, Evidence, Workaround, Removes). The skill's maintainer adds them;
     nothing goes upstream to labview-mcp without the user's go-ahead.
   - **Side effects** (step 3) and **open at the end**.
6. **Knowledge audit.** Run each row, fix what it finds, run it again.

| Check | How |
|---|---|
| every brief is saved | each brief of the session, launch-message briefs included, in `briefs_folder` and committed: `git status --short <briefs_folder>` against the briefs the status names |
| main-session events are in files | `main-session-notes.md` exists when a subagent closes; its decisions appear in the status |
| cited commits are reachable | each hash in the status and reports: `git merge-base --is-ancestor <h> HEAD`; an unreachable one gets a tag `keep-<h>`. Evidence outside git: a file list and a manifest (path, size, mtime) |
| locked trees are unchanged | each tree the session promised not to change: `git status --short` empty and HEAD equal to the start, or an empty manifest diff for a tree without git. Run after the last agent |
| side effects are complete | every agent's side-effects list and the git checks of step 3 are in the list |
| project facts are recorded | each LabVIEW fact specific to this project goes into its `knowledge_files`, phrased as a fact ("LabVIEW does X when Y"), with evidence (proof file, commit). No `knowledge_files`: list them in the status and ask the user where they go |
| general facts are proposed | a fact about LabVIEW, AF or labview-mcp that holds beyond this project: proposed in the report for `<skill>/knowledge/` (the maintainer adds it) |
| MCP pitfalls are proposed | each tool issue of the MCP report has a candidate entry or new evidence (step 5) |
| files you may not edit | another repo, a locked file, or the skill: write numbered candidates (continuing the file's numbering) into the close folder and open an item for the file's owner |
| decisions are logged | each rule the user chose this session is in `.labview/decisions.md` and in its convention file with a `decided` source |
| scripts used twice are proposed for the kit | scripts the reports name (grep them for `scratchpad`, `.py`, `.ps1`, `.xml`): an offline one is made portable (no project names, paths as arguments, a `--check` self-test), tested on copies, and proposed for `<skill>/kit/` with a README row. One that acts on or samples a live LabVIEW becomes an open item with its test plan |
| helpers came from the kit | no helper VI was regenerated from a scratch copy of a kit `.xml` |
| skill gaps are fixed or owned | each numbered gap from a test: fixed in a skill commit, or an open item with its owner and state |
| stale texts are marked | grep the project's knowledge files and `.labview/` for each superseded route or old name; mark it superseded, do not delete it |
| proof is complete | each proof folder the status names has a `README.md` (question, result, commits), committed |
| nothing only in memory | the agent's memory notes only point to repo files |

7. **Commit.** Stage by explicit paths, never `git add -A`: it sweeps in stray output and other writers' files. The
   message follows `convention: hygiene.commit-messages`, e.g. `docs(<X>): session close - status, MCP report`.
   The user's global git rule forbids AI attribution lines: add a trailer only when `project.json` sets
   `commit_attribution`. A multi-line message goes into a file for `git commit -F <file>`. Then
   `git status --short`: clean, or every leftover named in the status with its reason (a file the user is editing,
   ignored run output, untracked files of another writer, which stay as they are). No git: `dot-labview.md`,
   "No git" (a manifest instead of the commit).
8. **Report to the user:** the final commit hash; 3–5 lines (built, verified, open, next); the side-effects list in
   full; what is proposed for the skill's maintainer (MCP candidates, knowledge, kit scripts).

## Checks / evidence
- The status carries numbers, not "green"; its side-effects section exists, "none" included.
- Every hash it cites is reachable; every locked tree is unchanged by the step 6 checks.
- `git status --short` is clean or each leftover is named.

## Report (when a subagent ran the close; max 12 lines plus the side-effects list)
```
close      session <X>  status <path> (<n> lines)  MCP report <path>
side       <the step 3 list | none>
audit      briefs <n> saved  facts <n> -> <knowledge file | proposed>  candidates <ids>  kit <scripts | none>
           commits reachable <n>/<n> (tags: <list | none>)  locked trees <unchanged | diff: list>
           skill gaps <n> fixed, <n> owned  decisions logged <n>
commit     <hash>  leftovers <none | list with reasons>
LabVIEW    <PID, this session's | the user's>  unsaved <n>  dialogs <n>  LVAutoSave <n>
```

## Traps
- A status that says "green" without numbers is not evidence: copy the readings.
- A reset can leave cited commits reachable only through the reflog; a later `git gc` deletes the evidence while
  the status still says "proof complete". Check reachability, and tag what must stay.
- A subagent's "approved" is not the user's decision: write only decisions the user made.
- The audit edits no LabVIEW file; kit proposals are scripts and AIXML text, tested on copies.
- "No LabVIEW call" also rules out a last `lvai_status`: the window list gives the state.
