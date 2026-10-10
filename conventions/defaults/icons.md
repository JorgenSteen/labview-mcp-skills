# Convention: icons
status: in force
written: (setup fills in the date)

> Default template. `conventions/setup.md` copies it into `<repo>/.labview/conventions/icons.md` and settles each
> rule. The per-project values (abbreviations, colours, glyphs) go in `.labview/conventions/icon-spec.json`; its
> format and the procedure are in `ops/icons.md`.

## existing-icons
Existing icons are never redrawn. A new or regenerated VI in an existing class gets the class or library template
re-applied, or a sibling's icon copied. Icons are generated from the spec for existing code only when the user asks,
for the classes they name.
source: default

## when
Icons are made for the VIs a task adds or regenerates, at the end of the step that made them. A tree is never
re-run as a whole.
source: default

## banner
Every VI icon of new code has a banner on top: the class abbreviation (unique within the project as far as
possible), in the class's own colour (unique per class), in black LabVIEW Small Fonts text.
source: default

## class-glyph
Every class and actor has ONE glyph of its own, on the right of the icon body. The banner plus the class glyph form
the class template, the starting point of every VI of the class.
source: default

## labview-template
Icons use LabVIEW's own icon system. The banner and the class glyph are drawn ONCE, as the class's (or library's) icon,
and LabVIEW applies that icon to every member as its template layer (`NI_Library`). Each VI holds only its own glyph
layer on top. A class template change is then one set of the class icon plus LabVIEW's apply to its members, not a
redraw of every VI. Drawing a full composite into each VI (which loses the template link) is a fallback only, with the
user's ok.
source: default

## vi-glyph
Every VI adds at least one glyph, or text where that makes sense, telling what it does. For example, "write to file"
is a paper and a pencil. The VI glyph may overlap the class glyph.
source: default

## library-icon
A library icon has at least a banner, with the library's abbreviation and colour. A glyph is optional.
source: default

## reference
The look of new icons follows the user's RT core actor icons in production code, not the GUI or
middleware icons. For an existing area, the reference is that area's own icons.
source: default
