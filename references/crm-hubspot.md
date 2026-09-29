# HubSpot mechanics

Everything here assumes HubSpot's official remote MCP server. Behavior
marked "verified" was confirmed read-only against a live account in
September 2026. If a call behaves differently than
described here, trust the live tool (and its `tool_guidance` output) over
this file, and tell the rep what you found.

## Tools used

| Job | Tool |
|---|---|
| Who is the rep, which account | `get_user_details` |
| Field definitions (label, type, options, description) | `get_properties`, `search_properties` |
| Find deals, check how often a field is filled | `search_crm_objects` (objectType `DEAL`) |
| Group deals by pipeline and stage (stage discovery) | `query_crm_data` (call `tool_guidance` for it first) |
| Read one deal | `get_crm_objects` |
| Update a deal, create the audit note | `manage_crm_objects` |
| Find an owner by name | `search_owners` |
| Usage help for any of the above | `tool_guidance` |

Never call `manage_custom_properties` or `manage_custom_pipelines` to
create or change anything. The skill doesn't change CRM structure.

## Listing deals for the rep (SKILL.md Step 2)

1. Get the rep's owner ID from `get_user_details`.
2. Rep's own deals: `search_crm_objects` on `DEAL`, filtered to
   `hubspot_owner_id` = the rep, `hs_is_closed` = false, and the mapped
   pipeline(s). Sort by `closedate` ascending.
3. Other deals the rep can see: the same search without the owner
   filter, excluding the rep's own. HubSpot only returns records the
   rep has access to. Resolve owner names with `search_owners`.
4. Properties to request: `dealname`, `pipeline`, `dealstage`,
   `amount`, `closedate`, `hubspot_owner_id`, `hs_lastmodifieddate`, and
   the associated company name.
5. **Remove duplicates by deal ID (verified).** A deal tied to more than
   one company comes back once per company when the company name is
   joined in. Show each deal once, with one company (or "2 companies").
6. Show each stage as "Stage (Pipeline)" when the account has more than
   one pipeline, because stage labels repeat across pipelines.

## Instance ID

Use the HubSpot account (portal) ID from `get_user_details` as the
config `--instance` value.

## Reading pipelines and stages

What the connector gives you (verified):
- The `pipeline` deal property lists the pipelines (label and stored ID).
- The `dealstage` deal property lists **every stage from every pipeline
  in one flat list**, with no pipeline, order, or probability. Labels
  repeat across pipelines (two "Discovery" stages, for example), each
  with its own stored ID.

So discover the structure from the deals themselves:

```sql
SELECT pipeline, dealstage, COUNT(*), AVG(hs_deal_stage_probability)
FROM DEAL
GROUP BY pipeline, dealstage
```

- A stage with deals in a pipeline belongs to that pipeline.
- Sort each pipeline's stages by average probability to propose an
  order.
- Probability 1.0 is closed-won and 0.0 is closed-lost. Mark them
  `closed: true`; they are never proposed (SKILL.md rule 7).

Limits, so the rep still confirms:
- Stages with no deals don't appear (new or rarely used stages).
- Stages with the same probability can't be ordered this way.
- Rows with a count of 0 can show up for stage/pipeline pairs that
  don't really exist. Ignore them.

Always store and write the stage's ID, and show the label with its
pipeline. Never look a stage up by label alone.

Stage descriptions and closed flags aren't readable either (verified):
the connector has no pipeline or stage read beyond the flat stage list.
Exit criteria an admin typed into a stage description can't be found,
so don't imply setup looked. Ask the rep, and ask which stages are
closed when no stage has deals at 100% or 0%.

## Checking how often a field is filled (setup step 4)

`query_crm_data` can't count text or dropdown fields: `COUNT(field)`
fails because aggregates only work on number, date, and currency
fields (verified). Use `search_crm_objects` on `DEAL` instead, one call
per field, with `hs_is_closed` = false and the field `HAS_PROPERTY`,
`limit` 1, and read `total` (verified). Compare it to the total open
deals from the same search without the field filter. With only a
handful of open deals, say the counts are too few to call any field
unused.

## Required properties per stage (conditional stage properties)

HubSpot lets admins require certain properties before a deal can enter a
stage (a "logic rule" or conditional stage property on the stage).

- **Not readable (verified):** neither `get_properties` nor the stage
  list shows these rules. Setup has to ask the rep which fields each
  stage requires.
- **Enforced on writes (verified, 2026-09-28):** moving a deal into a
  stage with a required field empty is rejected, and nothing is
  written. The error reads: "Property validation failed: <internal
  name> is required based on the values of other properties." (Older
  HubSpot Community reports say API updates skip these rules; that
  wasn't the case through this connector.)

Before proposing a stage move, check every required field for the
target stage from the saved map (see `stage-rules.md`), so the move
isn't proposed only to fail. If a write is rejected anyway, see
"Common failures."

## Field types and how they map to actions

`get_properties` returns each field's name, label, type, options, and
description. It does **not** return the field type detail that separates
single-line from multi-line text, and it doesn't flag read-only or
calculated fields (verified).

| HubSpot `type` | Treat as | Action rules |
|---|---|---|
| `string` | text, line length unknown | Ask the rep in setup whether it's a one-line or a paragraph field. Until answered, treat as short text: keep appends to one short line |
| `enumeration` with Yes/No options | checkbox | Replace |
| `enumeration`, other | picklist (or multi-select if the rep says so) | Replace; multi-select adds a value |
| `number` | number | Replace |
| `date`, `datetime` | date | Replace |
| Owner fields (`hubspot_owner_id` and similar) | lookup | Replace; resolve names with `search_owners` |

Skip HubSpot-maintained fields (most `hs_` fields, such as
`hs_deal_stage_probability` or `hs_lastmodifieddate`), even if they look
relevant. Exceptions a rep may map: `hs_next_step` (Next step) and
`hs_manual_forecast_category` (Forecast category). If a write to any
field fails as read-only, mark it "can't update" and remove it from the
map with the rep's OK.

Length: HubSpot stores text values up to 65,536 characters, but a
one-line field shows poorly past a sentence or two. Treat one-line
fields like the 255-character short text in `field-rules.md`.

Multi-select values are stored as one string separated by semicolons.
Write the stored values, not the labels.

## Reading a deal's current values

Request every mapped field by name. **Empty fields are left out of the
response rather than returned blank (verified).** In connected mode, a
field that was requested but not returned is empty, not unknown. (This
is the opposite of snapshot mode.) A field that no longer exists is also
left out without an error (verified), so it reads as empty; only the
field list check in SKILL.md Step 1 catches a deleted field.

## Writing a deal

Use `manage_crm_objects` to update the deal by ID with only the
approved properties. Send stored values for picklists, not labels. The
connector enforces the rep's own permissions, so a field the rep can't
edit will fail; report it as "can't update" with the reason.

Write order (from SKILL.md): fields, then `dealstage`, then the
evidence note, then the audit note, each after the one before succeeds.
A required stage field filled in the first write lets the stage change
through (verified).

When `dealstage` changes, HubSpot may update the deal's probability and
related values automatically. Say so in the review's side-effects line
rather than writing those values directly.

Adding a note to a deal changes the deal's Last Modified Date even when
no field changed (verified). The re-read before writing (SKILL.md Step
10) compares field values, never that date.

## Note formatting (evidence note and audit note)

HubSpot's note view ignores plain line breaks (verified): a note written
as plain text with line breaks shows as one run-on paragraph, though the
breaks reappear in edit mode. Write note bodies as simple HTML, one
`<p>` per line, for example:

```html
<p>CRM Deal Updater | 2026-09-28 14:14 | 1 field updated, stage unchanged, 2 declined</p>
<p>Written: 2026-09-28T14:14:47Z</p>
<p>Processed through: 2026-09-26T18:00:00Z</p>
<p>Methodology: MEDDPICC</p>
<p>Fields updated:</p>
<p>&nbsp;&nbsp;- Economic buyer: filled</p>
```

The first `<p>` is the note's title (SKILL.md Step 11). HubSpot's
timeline shows only the first paragraph until the note is expanded
(verified), so the title's summary is what a rep sees at a glance.

Keep it to `<p>` (and `<br>` if needed); no other tags. Escape `<`, `>`,
and `&` in the text itself (`&lt;`, `&gt;`, `&amp;`); HubSpot encodes
them anyway.

**Reading notes back:** bodies come back as HTML, with characters like
`>` encoded (`->` returns as `-&gt;`, verified). Before looking for
"Processed through" or the Declined section, turn each `<p>` or `<br>`
into a line break, remove any other tags, and decode entities
(`&gt;` to `>`, `&amp;` to `&`, `&nbsp;` to a space).

## Evidence note

Same mechanics as the audit note below: a NOTE created with
`manage_crm_objects`, associated to the deal, with `hs_note_body`
starting with its title (`CRM Deal Updater | Evidence | <date> <time> |
<elements>`) and the evidence
grouped by methodology element, formatted as above. To avoid repeating
evidence on a later run, search the deal's notes for bodies containing
`CRM Deal Updater | Evidence`.

## Audit note

Create a NOTE engagement with `manage_crm_objects`:
- `hs_note_body`: the audit note text from SKILL.md Step 11, as HTML
  (see "Note formatting")
- `hs_timestamp`: now, read from the clock
- associated to the deal

To find the last audit note on a later run, search notes associated with
the deal for bodies containing `CRM Deal Updater` (a `CONTAINS_TOKEN`
filter on `hs_note_body` with an association filter on the deal
works, verified), **then drop any whose body contains `CRM Deal Updater
| Evidence`**. Evidence notes match the same text but have no
"Processed through" line. Take the newest remaining note, sorted by
`hs_createdate`. Clean up the body as described in "Note formatting"
before reading it, and match on the text, not the start of the string.

For declined items (SKILL.md Step 3), read the "Declined" section of
every remaining audit note on the deal, not just the newest.

Search catches up a few seconds after a write (verified: a note created
moments earlier was missing from search, then appeared about 30 seconds
later). If a run starts within a minute of the last one on the same
deal, wait briefly and search again before trusting the lookup.

If the account has Sensitive Data turned on, HubSpot's MCP server blocks
activity data, including notes. The write may still work but the read
back won't. Tell the rep and fall back to the default window.
**Not tested:** neither test account had Sensitive Data turned on. This
behavior comes from HubSpot's connector documentation (the
`BLOCKED_FOR_PORTALS_WITH_SENSITIVE_DATA` status in `get_user_details`),
not from a run. If `get_user_details` reports that status for notes,
treat notes as unreadable for this account.

## Common failures

- **"Property validation failed: <name> is required based on the values
  of other properties":** a stage rule requires that field, and it's
  empty. Nothing was written. Tell the rep in plain words ("Negotiation
  requires Economic buyer, which is empty"), using the field's label, not
  its internal name. Offer to fill it from the evidence, or hold the
  stage change. Then, with the rep's OK, add the field to that stage's
  required fields in the saved map so the next run checks it first.
  Don't retry the same write, and don't work around the rule.
- **"Property \"<name>\" does not exist" / property not found:** the map
  is stale. HubSpot rejects the **whole update** (verified), so no field
  in it was saved. Tell the rep which fields weren't saved, go back to
  SKILL.md Step 1 to fix the map, and offer to resend the other fields
  on their own.
- **Invalid option for a picklist:** the stored value changed. Re-read
  the property and re-confirm with the rep.
- **Permission error:** mark "can't update," give the reason, continue
  with the rest.
