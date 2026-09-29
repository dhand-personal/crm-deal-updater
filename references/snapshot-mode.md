# Snapshot mode

For reps who don't have HubSpot or Salesforce, or who do but haven't
set up the MCP connector. The skill does everything it does in
connected mode, from setup through the review table. The difference is
at the end: instead of writing to the CRM, it hands the rep an approved
update list to enter themselves.

The skill never writes to a CRM in this mode, even if the rep asks it
to "just do it." There's nothing connected to write with. Say so plainly
if it comes up.

## Setup in snapshot mode

SKILL.md setup steps 2 through 4 read from the snapshot instead of the
CRM. Anything the snapshot lacks (stage order, field types, length
limits, picklist options) is asked for, or handled with the defaults
below. Key the config with `--crm other` (or `hubspot` / `salesforce` if
that's the CRM) and an `--instance` name the rep chooses, such as
"acme-pipedrive", and set `"access": "snapshot"`.

Also ask once where notes go in their CRM (its notes feature, or a notes
field or column, such as a "Notes" column in a spreadsheet) and save it
as `notes_location`. The evidence note and audit note go there.

## Each run in snapshot mode, at a glance

- Step 3: current values are whatever the snapshot shows; a field left
  out is unknown, not empty (see "Unknown vs empty"). Compare the saved
  update list with the new snapshot (see "After the list"). Ask for the
  last audit note or last update date if the snapshot doesn't show it.
- Step 10: produce the update list below instead of writing. Approval
  rules are the same.
- Step 11: the audit note text goes at the end of the update list.
- Step 12: save the approved list and the declines to the config (see
  "After the list").

## What a snapshot needs

Minimum for a useful run:

- **CRM name** (HubSpot, Salesforce, Pipedrive, a spreadsheet, whatever
  it is).
- **The deal:** name, account, and current stage.
- **The stages** in order, with closed stages marked. Needed once, at
  setup; after that the saved map covers it.
- **The methodology fields** with their labels and current values,
  including empty ones. An empty field and a field left out of the
  snapshot mean different things (see "Unknown vs empty").

Helpful but optional:

- Field type (text, long text, dropdown, date, number, checkbox) and,
  for dropdowns, the options.
- Character limits, if the CRM shows them.
- Close date, amount, next step.
- The date of the rep's last update to this deal, or the last audit
  note from this skill. Sets the evidence window.

Give the rep `assets/snapshot-template.md` if they aren't sure what to
provide. Don't make them fill it in if they've already given the same
information another way.

## Formats accepted

Take whatever the rep has. In rough order of reliability:

1. **The filled-in template.**
2. **An export** (CSV or Excel) of the deal, with field labels as column
   headers. One row per deal. Ask which row if there are several.
3. **Text copied from the deal page** and pasted into the conversation.
   Match labels to values carefully; copied pages often lose their
   layout.
4. **Screenshots of the deal record.** Read them, then list back the
   fields and values you read and ask the rep to confirm before going
   on. Long text fields in screenshots are often cut off. Treat any
   long text value from a screenshot as possibly incomplete and ask
   before appending to it.
5. **The rep describing it.** Fine for a quick run. Confirm each value
   back.

If a value is unreadable or ambiguous, ask. Never fill a gap in the
snapshot with a guess.

## Unknown vs empty

- **Empty:** the snapshot shows the field with no value. It can get an
  Update.
- **Unknown:** the field isn't in the snapshot at all. Don't propose an
  Update, because the CRM may already hold something the rep would lose
  or duplicate. Ask for the current value, or list the proposed text as
  "add if the field is empty; otherwise append."

## Defaults when details are missing

Snapshot mode has only labels, not internal field names or stored
values. That's fine: the rep enters the changes by label anyway.

| Missing detail | Default |
|---|---|
| Field type | Infer from the label and value (a date, a number, yes/no), then confirm with the rep at setup |
| Short or long text | Treat as short text with a 255-character limit until the rep says otherwise. Keeps appends short and avoids truncation |
| Dropdown options | Only propose a value the rep confirms is an option. Otherwise describe the change and let the rep pick the closest option |
| Stage order | Ask. Don't infer from names |
| Required fields per stage | Ask, same as connected mode |
| Win probability or forecast category per stage | Skip the side-effects line and say it's unknown |

Save what the rep confirms to the config (`"access": "snapshot"`) so
later runs don't ask again.

## Drift in snapshot mode

Each run's snapshot is compared to the saved map. A field label that no
longer appears could be renamed, removed, or simply left out of this
snapshot. Ask which before changing the map.

## The update list (replaces Step 10's write)

Only approved items, in the order the rep should enter them. Fields
first, then the stage, then the audit note. Each item gives the field
label, what to do, and the exact text in a block that's easy to copy.

```
Update list for: Larkspur Freight, Warehouse Automation
CRM: Pipedrive   Prepared: 2026-09-23   Sources through: 2026-09-22

1. Economic Buyer  (field is empty: paste this)
   [2026-09-20 | Email from VP Finance] Dana Ruiz, VP Finance, owns the budget. Asked for an ROI summary before the 10/7 review.

2. Decision Process  (add to the end of the existing text)
   [2026-09-22 | Email from procurement] Procurement needs a signed MSA before issuing the PO; about 5 business days.

3. Forecast Category  (change: Pipeline -> Best Case)
   Source: call 9/18, champion confirmed budget is approved for Q4.

4. Stage  (change: Discovery -> Evaluation)
   Enter after items 1 and 2. Evaluation requires Economic Buyer, which item 1 fills.

5. Notes  (add to the deal's notes: evidence with no field)
   CRM Deal Updater | Evidence | 2026-09-23 14:05 | Paper Process
   Paper Process: [2026-09-22 | Email from procurement] Signed MSA required before a PO; about 5 business days.

6. Notes  (add to the deal's notes: audit note)
   CRM Deal Updater | 2026-09-23 14:05 | 4 changes to enter
   Written: 2026-09-23T14:05:00Z
   Processed through: 2026-09-22T17:30:00Z
   ...
```

(The company and people in this example are invented.)

The "Notes" items go wherever the rep said notes live during setup
(`notes_location` in the config): the CRM's notes feature, or a notes
field or column. Name that place in the item, for example "add to the
Notes column" for a spreadsheet. If it isn't set, ask.

Rules for the list:

- "Add to" items say plainly: add to the end of the existing text,
  don't replace it.
- Replace items show old and new values.
- The stage item says which earlier items it depends on.
- If the rep's CRM supports bulk import and they ask for a file, offer a
  CSV with one column per changed field. Don't assume their import
  format; ask how their CRM expects it.

## After the list

The skill can't confirm the rep entered anything. Save the approved
list to the config (`deals.<slug>`, see `scripts/manage_config.py`),
then close with one line: "Once these are in, the next run will pick up
from 2026-09-22."

On the next run, compare the saved list with the new snapshot:
- Items that appear in the snapshot were entered. Nothing more to do.
- Items that don't appear were probably missed. Carry them into the new
  review, marked "from the last update list, not entered yet," and ask
  whether to keep them. Their
  evidence may be older than the new run's window, so without this step
  they would silently disappear.
- The duplicate check still runs on everything, so an item entered with
  slightly different wording isn't proposed twice.
- Notes rarely show up in a snapshot (a screenshot of the deal fields
  won't show a Notes tab). If the snapshot doesn't show notes, ask
  whether the note items from the last list (evidence note, audit
  note) were added, rather than assuming either way.
- Items the rep declined (`deals.<slug>.declined`) aren't proposed
  again unless newer evidence adds something (SKILL.md Step 3). Add new
  declines to the end of the saved list, one at a time (see
  `scripts/manage_config.py`), so earlier ones aren't lost. Save
  declines even when the rep approved nothing; in that case there's no
  update list to hand over, just a one-line note that the declines were
  saved.

If the config isn't available (a different computer, or a fresh
workspace), ask the rep whether everything from the last list was
entered, or to paste the last audit note.
