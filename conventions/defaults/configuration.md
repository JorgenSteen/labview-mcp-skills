# Convention: configuration
status: in force
written: (setup fills in the date)

> Default template, and a SUGGESTION: planning always asks the user how configuration will be handled
> (`conventions/setup.md`, section 4) and offers this file as the proposal. The default is the user's current
> practice (production code RT, `production-code`). In an existing project, the mechanism the analysis found wins.

## ini-files
Settings live in INI files, one file per topic (general, communication, control loop, calibration, ...), named
`<project>-config-<topic>.ini`; calibration data uses `<project>-calibration-<topic>.ini`. The default files live in a
`config` folder of the source tree.
source: default

## config-class
One parent configuration class does the file handling. Each topic is a child class of it.
- **The parent:** open, load, save and close the file, create the path or folder, read and write the metadata,
  compare and update the file version, and collect issues (missing or bad entries). A method a child must override
  but does not reports "child not implemented".
- **Each child (one per INI file):** overrides the default file path, the default values, and the read and write of
  its own data (typedefs in the child class), plus any get/set methods its users need.
Why: one place handles files, versions and errors; adding a topic means adding a child, not new file code.
source: default

## metadata
Every INI file starts with a `[metadata]` section: `modified (timestamp)`, `version` and `comment`. On load the class
compares the file's version with the one it expects. It updates an older file or reports it as an issue.
source: default

## defaults-and-missing
If a file is missing, it is created from the child's default values. A missing or unreadable entry is reported as
an issue, never silently replaced. What an issue does at run time (stop, or a message such as "bad config file")
follows the error policy (`errors.default-policy`).
source: default

## who-reads
The actor that owns a part of the system reads its configuration, e.g. the root its general configuration or the
hardware manager the hardware configuration. Values a child actor needs at launch are passed down in its pre-launch
settings (`af-shapes.prelaunch-settings`). The settings may decide which nested actors are launched. An actor that
must pick up changed settings at run time gets a reload message.
source: default
