# Convention: hygiene
status: in force
written: (setup fills in the date)

> Default template. `conventions/setup.md` copies it into `<repo>/.labview/conventions/hygiene.md` and settles each
> rule. The save version, commits before structural steps and the side-effects report are safety rules (`SKILL.md`),
> not conventions, and are not in this file.

## cleanup-diagram
Clean Up Diagram runs only on VIs the bot generated or regenerated, never on existing hand-laid VIs.
- **New VI:** the best result is a layout in the style of the VIs around it (their rails, direction, habits).
- **If that cannot be done:** Clean Up Diagram is better than the raw generated layout.
- **A request to clean up all VIs of existing code:** list those VIs and ask first.
source: default

## test-convention
A class that packs, multiplexes or bundles data has a round-trip test: data in → pack → unpack → compare with the
input, because data can be mangled on the way. The test VI's outputs are a Boolean named `Pass` and `error out`.
Other indicators are informational and stay off the read-back. The test is listed in `.labview/checks.json`.
Driver and hardware tests (e.g. a power supply) are a second type, not yet defined.
source: default

## test-library
Tests live in a separate library (dev-time code, not shipped).
source: default

## test-after-edit
After every edit to a class that has a round-trip test, that test is run (`ops/run-checks.md`).
source: default

## descriptions
Every new class and VI gets a description saying what it does (and, for an actor, its error-handling plan or the
`errors.no-plan-statement`). Short: 2-4 sentences, about 400 characters at most. ASCII only ("->", not an arrow
character: a class description is stored ANSI and an arrow became "?" with no error). No decision or finding
numbers, no rule IDs, no spec section references, no walk through the diagram: what it does and why, for a reader
of the code.
source: default

## conditional-disable
Conditional Disable symbols are defined on the project targets and used only where there is a good reason (target
PC vs sbRIO, development environment vs run-time). Every Conditional Disable structure carries a bookmark comment
(`#NOTE: <why>`, or the project's own `#` tag), so all of them can be found in LabVIEW's Bookmark Manager.
source: default

## commit-messages
Commit messages follow Conventional Commits: `<type>(<scope>): <summary>`, with a short body saying what and why.
Commit by explicit paths. Add a trailer line only if `project.json` sets `commit_attribution`.
source: default
