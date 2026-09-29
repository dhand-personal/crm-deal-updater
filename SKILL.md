---
name: crm-deal-updater
description: Updates a deal or opportunity from the account's actual sales communications, following the company's own sales process and methodology (MEDDPICC, Command of the Message, Sandler, BANT, SPICED, and others). Discovers stages and fields, maps them to the methodology once with the rep, proposes sourced field updates and forward or backward stage changes, and writes nothing until the rep approves each change. Works through the HubSpot or Salesforce MCP connector, or, with no connector or any other CRM, from a pasted or exported snapshot of the deal, returning an update list to enter by hand. Use whenever someone asks to update a deal or opportunity, log a call or meeting to the CRM, fill in MEDDPICC or other methodology fields, check whether a deal is ready to move stages, or sync customer conversations into their CRM. Pulls communications through the unified-communication skill by default, or works from a pasted transcript, email, or notes.
---

# CRM Deal Updater

Keeps a deal record in step with what has actually been said on calls
and in email, organized the way the company sells: its own pipeline
stages, its own fields, and its own methodology. The skill proposes. The
rep decides. Nothing is written to the CRM without the rep approving it
in this conversation.

It runs in one of two modes:

- **Connected mode:** HubSpot or Salesforce through its MCP connector.
  The skill reads the CRM directly and writes the approved changes.
- **Snapshot mode:** no connector, or a CRM this skill doesn't connect
  to (Pipedrive, Dynamics, Zoho, a spreadsheet, anything). The rep gives
  the skill a snapshot of the deal, and the skill hands back an approved
  update list for the rep to enter. It never writes anything itself in
  this mode.

## Rules that never bend

These hold on every run, in every mode. If a later instruction in this
file seems to conflict with one of them, these win.

1. **No write without approval.** Every field update, stage change, and
   evidence note is shown to the rep first and written only after they
   approve it in this conversation. The audit note is the one exception:
   the rep approves it once, by leaving it on at setup, and it records
   what happened in this run: what was written, declined, or failed,
   plus anything held back or flagged. In snapshot mode,
   nothing is ever written; the rep enters the approved changes
   themselves. There is no "remember my approval" setting. Scheduled or
   unattended runs produce a draft and write nothing.
2. **Show labels, write internal names.** The rep only ever sees the
   CRM's human-readable field labels, stage labels, and picklist labels.
   Internal names and stored values are kept in the saved mapping and
   used only for the write itself. When two fields share a label, add a
   plain qualifier so the rep can tell them apart ("Forecast Category
   (system, read-only)").
3. **Text is never overwritten without the rep's approval on that
   field.** New information is normally added as a dated, sourced entry
   below what is already there. Existing text is replaced only in the
   cases `references/field-rules.md` allows (a placeholder like "Yes",
   a status field like Next Step, or condensing a field that would
   overflow), each as a Review item approved on its own, with the old
   text kept in the audit note.
4. **Anything that can't be appended to is replaced only with
   per-field approval.** Picklists, numbers, dates, checkboxes, and
   similar fields get a **Replace** action that is approved one field at
   a time and is never included in a bulk "approve all."
5. **Every proposed value traces to a source.** A call, an email, a
   pasted note, or something the rep said in this conversation. If there
   is no source, there is no proposal. Never invent a value, a name, a
   date, or a number.
6. **Never change the CRM's structure.** No creating or editing fields,
   pipelines, stages, or picklist options, even if the connector allows
   it. When there's evidence for an element with no field to hold it,
   offer to save it in a Note on the deal instead (see Step 5).
7. **Never propose moving a deal to a closed stage** (won or lost), to a
   different pipeline, or to a different record type. If the evidence
   points toward closed-lost, flag it for the rep and their manager to
   decide.

## What "done" looks like

A run is finished, not just technically complete, when all of these hold:

- The rep saw a review table with every proposed change, its source, and
  its action, and approved or rejected each item.
- Only approved items were written, and every write was confirmed as
  successful or reported as failed with the CRM's reason in plain words.
- Any stage suggestion showed the evidence against that stage's exit
  criteria, and any required fields for the target stage were handled
  or called out.
- The audit note (if the rep kept it on) records what changed, the old
  value for every Replace, what the rep declined, and which sources fed
  the run.
- Evidence for elements with no field was offered as an evidence note,
  not dropped.
- Gaps the methodology calls for but the communications never covered
  were listed, not papered over.

## Before anything else: pick the mode

Check the live tool list in this session. Don't rely on memory, the
config file, or the rep's belief that something is connected.

- **HubSpot connector:** the official HubSpot MCP server (tools such as
  `get_properties`, `search_crm_objects`, `get_crm_objects`,
  `manage_crm_objects`, `get_user_details`).
- **Salesforce connector:** either Salesforce's Headless 360 MCP
  server (tools `discover`, `describe`, `dispatch_readonly`, `dispatch`)
  or its SObject servers (tools such as `getObjectSchema`, `soqlQuery`,
  `updateSobjectRecord`, `createSobjectRecord`, `getUserInfo`). If both
  are connected, prefer Headless 360; it can read more of the sales
  process.

Then:

- **A connector for the rep's CRM is live:** connected mode. If both
  are live, ask which CRM holds this deal. Read the matching reference
  file (`references/crm-hubspot.md` or `references/crm-salesforce.md`)
  before setup or any write.
- **The connector is live but read-only** (for example Salesforce's
  "SObject Reads" server alone, or Headless 360 without `dispatch`):
  connected mode for reading, snapshot mode's update list for the
  output. Say so up front.
- **No connector for the rep's CRM:** snapshot mode. Say in one line
  that the skill can't reach the CRM from here, so it will work from a
  snapshot and give back an update list to enter by hand. If the rep
  uses HubSpot or Salesforce, mention once that connecting its MCP
  connector would let the skill read and write directly, then carry on.
  Don't block on it.

Snapshot mode is covered in full in `references/snapshot-mode.md`,
including what a snapshot must contain, the formats accepted, and the
output format. Read it before a snapshot-mode run. A fill-in template
for the rep is at `assets/snapshot-template.md`.

## First run: discover, then confirm

Setup runs once per CRM instance (a HubSpot account, a Salesforce
org, or, in snapshot mode, a CRM the rep names) and is saved with
`scripts/manage_config.py`. Check for an existing
config first (`manage_config.py --show --crm <hubspot|salesforce|other>
--instance <id>`). If one exists, skip to "Each run."

Setup can't be fully automatic, because stage entry rules are only
partly readable: Salesforce's validation rules and Path are readable
through Headless 360, while HubSpot's required stage fields aren't
readable at all (though HubSpot enforces them). So setup discovers what
the CRM exposes, proposes the rest, and has the rep confirm. The
confirmed map is the source of truth for stage checks.

In snapshot mode, setup reads from the snapshot and also asks where
notes go; see "Setup in snapshot mode" in `references/snapshot-mode.md`.

### Setup steps

1. **Explain in two sentences** what setup does and that it takes a few
   minutes once.
2. **Identify the rep** and the instance ID to key the config by (calls
   in the CRM reference file).
3. **Discover the pipelines and stages** with labels, order, and win
   probability where available. Ask which pipeline(s) the rep works in.
   Ask the rep for anything the connector can't show (order, which
   stages are closed, probabilities of stages with no deals).
4. **Discover the deal fields** (label, type, length, picklist options,
   description). Drop system, formula, and read-only fields. Where the
   CRM doesn't report a text field's size, ask whether it's one line or
   a paragraph. Then count how often each candidate is filled on open
   deals:
   - **Fields no one fills in:** list once as "appear unused" and leave
     them out unless the rep says otherwise. With only a handful of open
     deals, say the counts are too few to judge. Exception: a field
     whose label matches a methodology element is always proposed,
     flagged "not filled yet" (a company that just added its methodology
     fields will have them empty).
   - **Look-alike fields** (a text "Competition" field and a
     "Competitor" dropdown): recommend the one in use, show both counts,
     and let the rep choose. If neither is used, ask which to use.
5. **Resolve the methodology.** Stop at the first hit: named by the rep;
   a default this user already confirmed, if saved in memory; the field
   labels (score against `references/methodologies.md`); ask the rep.
   If none names one, **default to MEDDPICC** and say so in one line
   ("No methodology stood out, so I'm using MEDDPICC; you can change it
   anytime"). Blends are normal; record every methodology in play.
6. **Propose the map** in one table the rep can correct:
   - Each methodology element to the field that holds it (by label), or
     "no field" (a gap reported every run). One field can hold two
     elements when the company uses it that way.
   - Each stage's exit criteria, drafted from the methodology and any
     stage descriptions the CRM provides, each marked "from the CRM" or
     "proposed." A stage with no criteria never gets a move-out
     suggestion until the rep adds some.
   - Each stage's required fields: from the CRM where readable
     (Salesforce validation rules and Path through Headless 360, with
     the rule's error message), otherwise asked directly.
   - Methodology-looking fields that don't map: ask whether to include,
     map, or ignore them. Never guess.
   - Standard fields that stage checks and forecasts depend on (Close
     Date, Amount, Next Step, Forecast Category), saved as "Standard."
7. **Ask about the audit note.** On by default. The rep can turn it off,
   but say what that costs: without it, each run can't tell which
   sources were already processed, and declined items come back.
8. **Save** with `manage_config.py --init` and confirm in one or two
   sentences what was saved.

The rep can re-run setup any time ("remap my fields," "our stages
changed"). Individual changes ("Champion is now in a different field")
are handled with `manage_config.py --set` without a full re-run.

## Each run

### Step 1: Load the map and check for drift

Load the config for this CRM instance. Then re-read the field and stage
lists (cheap; in snapshot mode, from the new snapshot) and compare. If a
mapped field was renamed, deleted, or changed type, or a stage was
added, removed, or reordered, tell the rep what changed and fix the map
with them before continuing. Never write
to a field whose definition no longer matches the saved map.

### Step 2: Pick the deal

If the rep named a deal, find it. If more than one record matches, list
them and ask. Never pick by recency.

If no deal was named, show a list of open deals in the mapped
pipeline(s):

- **The rep's own deals first**, soonest close date first.
- **Then other open deals the rep can see** (a teammate's deal they
  support, for example), in the same order, with an Owner column so
  it's clear whose deal it is. Skip this second group if the rep has
  no access to other deals.
- **Columns:** deal name, account, stage label, amount, close date, last
  updated, and owner (second group only). Show each deal once, even if
  it's tied to several companies. With more than one pipeline, show
  stages as "Stage (Pipeline)", since stage names repeat across them.
- **Flag past-due close dates** ("close date passed"); they sort to the
  top.
- **Show clean names:** decode HTML codes ("&amp;" becomes "&").
- **Up to 15 rows.** If there are more, say how many and offer to show
  the rest. The rep can filter by account, stage, or owner at any point.

Ask which deal to update. Updating a deal someone else owns is allowed
if the CRM permits it, but say whose deal it is in the review and in
the audit note.

In snapshot mode, the deal is whatever the snapshot contains. If an
export holds several deals, show them as the same list (using the owner
and last-updated columns if the export has them) and ask which one.

### Step 3: Read what's there now

Fetch the deal's current stage and every mapped field, plus the
required fields for the stages immediately before and after the current
one. Hold these as the current values. Don't show them yet.

In connected mode, some CRMs leave empty fields out of the response.
A mapped field that was requested but not returned is empty. In
snapshot mode, a field missing from the snapshot is unknown, not empty:
never propose an Update to it, and carry over items from the last update
list that weren't entered (see `references/snapshot-mode.md`).

Also look for the most recent audit note from this skill on the deal.
Its "processed through" timestamp sets the default window in Step 4. If
notes can't be read (HubSpot Sensitive Data, for example), say so and
fall back to the default window.

Carry forward anything under "Not written (error)" in the last audit
note: propose it again, marked "approved on <date>, but the write
failed," unless newer evidence changes it. A carried stage move is
re-checked against the exit criteria like any other (Step 7) and
dropped if they aren't met.

Collect the items the rep declined on earlier runs: the lines under the
"Declined:" heading in this skill's earlier audit notes on the deal (in
snapshot mode, `deals.<slug>.declined` in the config). A declined item is
not proposed again, and stays out of every other field too (note any
overlap in the review). It comes back only if a source newer than the
decline adds something new about it, marked "declined on <date>; new
evidence since." A declined stage move comes back only when new
evidence changes an exit criterion's status; otherwise it gets one line
("Perception Analysis still looks met; you passed on it 9/24"). Details
in `references/stage-rules.md`.

### Step 4: Gather the evidence

Default path: invoke the `unified-communication` skill for this
account. Confirm it's installed first. If it isn't, say so, point the
rep to https://github.com/dhand-personal/unified-communications, and
use the standalone path for this run.

Time window, in order of preference:
- Everything after the last audit note's "processed through" timestamp.
- The deal's create date to today, for a first run on this deal.
- Whatever the rep asks for.
Say which window is in use.

What counts as evidence: communications that already happened and have
content (a call transcript or summary, an email, notes). Leave out
future calendar entries, logistics-only meetings, and duplicate records
of the same meeting. A scheduled meeting can support "next meeting
agreed," as a date only.

Standalone path: a pasted or attached transcript, email thread, or set
of notes is treated as one more record in unified-communication's
normalized shape. Ask for the date and participants if they aren't in
the text.

Then ask the rep once: "Anything to add that isn't in the calls or
email? Off-call conversations, internal politics, what you think
changed." Their answer is a source like any other, labeled "rep notes."

If there is very little to work with (one short call, no email), say so
before extracting and ask whether to continue.

### Step 5: Extract evidence for each mapped element

For each methodology element that has a mapped field, pull what the
records actually say. Rules:

- **Customer voice outranks everything.** A customer statement on a call
  or in a customer-sent email is the strongest evidence. Quote short
  phrases where they carry the point.
- **Internal-only threads and rep notes are context, not customer
  voice.** Label them that way in the review.
- **A record from the rep's own address that reads as someone else's
  words** (a forwarded or pasted customer email, signed by another
  name): ask the rep whether to treat it as the customer's voice, and
  label the source that way ("Email from Jim, sent from your address").
  In a scheduled run, treat it as rep notes and list the question in the
  draft.
- **Keep "not yet discussed" and "confirmed absent" separate.** "They
  told us there's no hard deadline" is information and can be recorded.
  Silence on the deadline is a gap.
- **Note conflicts, don't resolve them silently.** If a new source
  contradicts the current CRM value or another source, it becomes a
  **Review** item.
- **Write like a sharp rep would in a CRM:** concrete, short, specific
  numbers and names, no filler.
- **One fact, one field.** Put each new fact in the single text field it
  fits best. If it also fits another text field, say so in the review
  ("also fits Economic Buyer") instead of proposing it twice. That way a
  rep who declines it in one place never has it land somewhere else, and
  an approval never has to be undone. Dropdowns, dates, and status
  fields like Next Step show current state, so they can reflect a fact
  that's also written in a text field.

Elements with **no evidence** go in the gap list for Step 9.

Elements with **evidence but no mapped field** (the CRM has no field
for them, or the rep chose not to map one) go in an **evidence note**:
a Note on the deal, offered in the review, that holds this evidence so
it isn't lost. Rules:
- One note per run, grouped by methodology element, each item dated and
  sourced like a field entry. Title it `CRM Deal Updater | Evidence |
  <date> <time> | <elements covered>` (for example `CRM Deal Updater |
  Evidence | 2026-09-24 19:45 | Competition, Metrics`).
- The content screen and the self-check apply to it. Don't repeat
  evidence already in an earlier evidence note (lookup in each CRM
  reference file).
- Offer it only for evidence worth keeping. It's one review item,
  approved on its own. If the rep says no, the
  evidence stays in the review as coaching notes and nothing is written.

### Step 6: Decide the action for each field

Follow `references/field-rules.md` for the field's type. In short:

| Action | When | Approval |
|---|---|---|
| **Update** | Field is empty and there is sourced evidence | Can be approved in bulk |
| **Add to** | Text field already has content; new evidence adds something | Can be approved in bulk |
| **Keep** | Existing value already covers it | Nothing is written |
| **Replace** | Non-text field (picklist, number, date, checkbox, etc.) with a value the evidence says is wrong or out of date | One at a time, never in bulk |
| **Review** | New evidence conflicts with the current value, the append would exceed the field's length limit, the current value is a placeholder ("Yes", ".", "TBD", "To be added"), or the field holds only the current status (Next Step) | One at a time; rep chooses what to write |

Appends match the field's existing dated format if it has one;
otherwise they use the default format in `field-rules.md`
(`[YYYY-MM-DD | source] text`). Every append is checked against the
existing text so a re-run doesn't add the same fact twice. An entry that
repeats a known fact but adds a new detail is trimmed to just the new
detail (see `field-rules.md`). A placeholder value is replaced (with
approval) rather than appended to.

### Step 7: Assess the stage

Follow `references/stage-rules.md`. In short:

- Compare the evidence against the saved exit criteria for the current
  stage and the stages on either side.
- **Forward:** suggest a move only when the current stage's exit
  criteria are met by sourced evidence. Show each criterion with its
  evidence.
- **Backward:** only when a named exit criterion the deal already
  passed, as written in the saved map, clearly no longer holds. Events
  like a champion leaving are evidence to check against the criteria,
  never an automatic reason to move back. Uncertain criteria don't
  count.
- **Required fields for the target stage:** offer to fill empty ones
  from the evidence. With no evidence, say the move will fail until
  they're filled (both CRMs block it) and don't propose it.
- **Side effects:** show what else changes, such as win probability.
- **Closed stages are never proposed** (rule 7); closed-lost signals are
  flagged.
- **No stage change** is a common outcome. Say "stage looks right" and
  why.

### Step 8: Screen the content

Before showing anything, check every proposed value against
`references/crm-content-rules.md`. CRM records are widely visible inside
a company and can be subject to legal discovery. Remove or rewrite
opinions about individuals, personal details, health or family
information, unverified claims about competitors, and anything said off
the record. Tell the rep what was held back and why, in one line each.

### Step 9: Show the review

One message, in this order:

1. **Sources used:** calls (title and date), email threads (count and
   date range), rep notes (yes or no), and any source that was skipped
   or unavailable.
2. **Field table**, grouped by methodology element:

   | Field | Current value | Proposed | Source | Action |
   |---|---|---|---|---|

   For **Add to**, show the exact text that will be appended. For
   **Replace**, show old and new side by side. For **Review**, show both
   versions and explain the conflict in one sentence.
3. **Stage:** current stage, suggestion (or "no change"), the exit
   criteria with evidence for each, required fields for the target
   stage, and side effects.
4. **Evidence with no field:** the proposed evidence note, shown in
   full, with the offer to save it as a Note on the deal. Skip this
   section if there's nothing.
5. **Gaps:** methodology elements with no evidence yet. Keep it to a
   short list. This is useful coaching for the rep's next call.
6. **Held back** by the content screen, if anything.

Before sending the review, check it:
- Every proposed value names a source, and says only what that source
  said. Conclusions go in the stage section or Gaps, never in a field.
- Nothing the content screen held back or the rep declined on an
  earlier run appears in the table, including inside another field's
  text, and no new fact is proposed in two text fields.
- Replace and Review items (placeholders and status fields included)
  are marked one-at-a-time, never bulk-approvable.
- Labels are shown, not internal names or stored values.

Then ask the rep to approve, edit, or reject; they can edit any proposed
text. Update and Add to items can be approved together ("approve all").
That never covers the one-at-a-time items (Replace, Review, the stage
change, the evidence note): ask for each separately, as one form with a
yes/no per item if a question tool is available.

### Step 10: Confirm and write

In snapshot mode, this step produces the update list in
`references/snapshot-mode.md` instead of writing, with the same
approval rules. Then skip to Step 12.

If the rep approved every item as proposed, with no edits, that is the
go-ahead:
write without asking again. Otherwise (the rep edited text, or approved
only some items), show a final list of only what will be written, with
each Replace and Review item on its own line plus the stage change,
evidence note, and audit note if they apply. Ask "Write these to [CRM]
now?" and wait for a clear yes.

**Re-read before writing.** Right before writing, re-read the stage and
every field being written; an append sends the whole field back, so a
later edit by someone else could be lost. If anything changed since
Step 3, write nothing, show what changed, and rebuild those items for
approval from the fresh read.

Write order: fields first, then the stage change, then the evidence
note, then the audit note. Send each write only after the one before it
succeeds, never at the same time. If a field write fails and the stage
change depends on that field (a required field for the target stage),
hold the stage change and tell the rep why. After writing, read the
record back and confirm each item landed before reporting success.

If a write fails, don't retry blindly: explain the CRM's error in plain
words and offer the fix. Some CRMs reject a whole update when one field
in it fails (HubSpot, verified), so every field sent with it is also not
written; say so, and offer to resend the good fields on their own once
the rep agrees. Report partial success exactly, and don't roll back
successful writes unless the rep asks.

If the rep cancels the run at any point, write nothing, including the
audit note. Cancelling is different from declining items: a cancelled
run records nothing, so its items can come back next time.

### Step 11: Audit note

If on, create the note on the deal (mechanics per CRM reference file;
HubSpot notes are written as simple HTML so each line shows on its own).
In snapshot mode, the note text goes at the end of the update list.

Skip the audit note only when there was nothing new to propose. If the
rep declined everything, still write it: the "Declined" section is what
keeps those items from coming back, and "Processed through" moves
forward so the same sources aren't read again. Approved items that
failed to write go under "Not written (error)," never under "Declined,"
so the next run proposes them again.

Title it `CRM Deal Updater | <date> <time> | <summary>`, where the
summary says what happened in a few words (for example `2 fields
updated, stage Qualification to Solution Validation, 1 declined`, or
`nothing written, 3 declined`). CRM timelines often show only the first
line until the note is expanded. Keep it under 120 characters.

Read the date and time from the system clock right before writing (for
example `date -u`) for both note titles and the "Written" timestamp;
never estimate or reuse an earlier time. "Processed through" can never be
later than "Written"; if a source's timestamp is in the future, flag it
in the review and leave it out of the window. Write "Processed through" as a
full timestamp with time zone (for example `2026-09-24T19:40:00Z`),
never a date alone, so a second run the same day can tell which emails
were already handled.

```
CRM Deal Updater | <date> <time> | <summary>
Written: <exact timestamp, e.g. 2026-09-24T19:45:00Z>
Processed through: <full timestamp of newest source record used, e.g. 2026-09-24T19:40:00Z>
Methodology: <methodology or blend>

Fields updated:
  - <Field label>: added to
  - <Field label>: replaced "<old value>" with "<new value>"
Stage: <old stage label> -> <new stage label>, or unchanged
Evidence note: saved (<elements>), declined, or none
Held back: <count and kind, e.g. 1 personal remark; never the content itself>, or none
Flags: <closed-lost signal, close date passed, stage move waiting on a required field>, or none
Not written (error):
  - <Field label>: "<approved text or value>" (<CRM error in plain words>)
Declined:
  - <Field label>: "<proposed text or value, shortened if long>"
  - Stage: <suggested stage label>
  - Evidence note: <element>
Sources:
  - Call: <title>, <date>
  - Email: <subject>, <date of latest message>
  - Rep notes: yes or no
Gaps noted: <short list>
```

The "processed through" line is what makes the next run incremental.
When looking up the last audit note on a later run, skip evidence notes:
both titles start with "CRM Deal Updater |", and only the audit note has
a "Processed through" line (lookup details in each CRM reference file).

### Step 12: Wrap up

In snapshot mode, first save the approved update list and the declines
to the config (see "After the list" in `references/snapshot-mode.md`).

One or two sentences: what was written and anything that needs the
rep's attention (a failed write, a stage move waiting on a required
field, a closed-lost flag).

## Scheduled runs and calls from other skills

Nothing is written in either case. Read
`references/other-run-types.md` first:
- **No rep in the conversation** (a scheduled or unattended run): run
  Steps 1 through 9, ask nothing, and save the review as a draft.
- **Another skill asks for deal information:** run Steps 1 through 8
  read-only and return the results, each labeled customer-sourced or
  internal only.

## Error handling

- **Snapshot is thin or unreadable:** list exactly what's missing and
  ask for it. Don't guess at values.
- **Deal not found:** ask whether someone else owns it, or for a link.
- **Field the rep can't edit:** mark it "can't update" in the review with
  the reason.
- **No new evidence:** "Nothing new since the last update on <date>" is
  a complete answer.
- **Almost everything is a gap:** say so and ask whether to write the few
  items found or wait until after the next call.
- **Few or no methodology fields:** say so once, and offer the evidence
  note as the place to keep evidence.
- **A source reported as not connected:** list it in the sources. Not
  connected is not the same as empty.

## Reference files

Read the one that matches the task before acting on it.

- `references/crm-hubspot.md` / `references/crm-salesforce.md`:
  connector calls, stage and field discovery, writes, notes, known gaps,
  and common errors for each CRM.
- `references/field-rules.md`: actions per field type, entry format,
  duplicate and length checks.
- `references/stage-rules.md`: forward, backward, and declined moves;
  required fields; side effects.
- `references/methodologies.md`: methodology signals, elements, and
  typical field labels, for setup.
- `references/crm-content-rules.md`: what never goes into a CRM record.
- `references/snapshot-mode.md`: working without a connector or with any
  other CRM.
- `references/other-run-types.md`: scheduled runs and calls from other
  skills.
- `assets/snapshot-template.md`: a fill-in snapshot template for the rep.
- `scripts/manage_config.py`: the saved mapping at
  `~/.crm-deal-updater/config.json`, keyed by CRM and instance.
- `scripts/append_entry.py`: builds an append entry and checks it for
  duplicates and length.
