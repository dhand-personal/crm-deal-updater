# Salesforce mechanics

Two kinds of Salesforce MCP server work with this skill. Check the live
tool list to see which one is connected; if both are, prefer Headless
360 (it can read more). If a tool behaves differently than described
here, trust the live tool and tell the rep what you found.

| Server | Tools you'll see | Reads | Writes |
|---|---|---|---|
| **Headless 360** (beta) | `discover`, `describe`, `dispatch_readonly`, `dispatch` | Records, stages, field details, **validation rules, Path**, stages per sales process | `dispatch` |
| **SObject servers** (SObject All, or SObject Reads plus Mutations) | `getObjectSchema`, `soqlQuery`, `updateSobjectRecord`, `createSobjectRecord`, `getUserInfo` | Records, stages, field details | `updateSobjectRecord`, `createSobjectRecord` |

Read-only setups (Headless 360 without `dispatch`, or SObject Reads
alone) support setup and drafts. Say up front that the result will be
an update list to enter by hand, not a write.

## Setup is off limits (both servers)

Rule 6 applies with extra force here: Headless 360 can create and
change fields, validation rules, Path, permission sets, and much more
of Salesforce setup. The skill never does. In practice:
- Use `dispatch` only for the record writes in "Writing" below:
  updating an Opportunity, and creating the evidence note and audit
  note Tasks.
- Never call `dispatch` on a Tooling API path (`/tooling/...`), a
  Metadata path, or any setup recipe `discover` returns.
- Never delete anything.
- Reading setup data (validation rules, Path) with `dispatch_readonly`
  is fine.

## Headless 360: how calls work (verified)

`discover` searches setup recipes, which this skill doesn't need.
`dispatch_readonly` and `dispatch` accept standard Salesforce REST
paths directly. Verified against a live Salesforce org, API v67.0:

| Job | Call |
|---|---|
| Who is the rep | `GET /services/data/v67.0/chatter/users/me` (returns user `id`, name, email) |
| Any SOQL query | `GET /services/data/v67.0/query` with `queryParams: {"q": "<SOQL>"}` |
| Setup data (validation rules, Path, field details) | `GET /services/data/v67.0/tooling/query` with `queryParams: {"q": "<SOQL>"}` |
| Stages allowed for one record type | `GET /services/data/v67.0/ui-api/object-info/Opportunity/picklist-values/<RecordTypeId>/StageName` |
| Read one opportunity | `GET /services/data/v67.0/sobjects/Opportunity/<Id>` with `queryParams: {"fields": "<comma list>"}` |
| Update an opportunity | `dispatch` `PATCH /services/data/v67.0/sobjects/Opportunity/<Id>` with a body of only the approved fields |
| Create a Task (evidence or audit note) | `dispatch` `POST /services/data/v67.0/sobjects/Task` |

Use the API version the org supports; if v67.0 fails, try the version
in a `describe` result's path.

On the SObject servers, the same SOQL goes through `soqlQuery`, field
details come from `getObjectSchema`, and writes use
`updateSobjectRecord` / `createSobjectRecord`.

## Instance ID

Use the org ID as the config `--instance` value:
`SELECT Id FROM Organization`.

## Reading stages

```sql
SELECT ApiName, MasterLabel, SortOrder, DefaultProbability,
       ForecastCategoryName, IsClosed, IsWon, IsActive, Description
FROM OpportunityStage
WHERE IsActive = true
ORDER BY SortOrder
```

- Show `MasterLabel` to the rep. Write the picklist value (normally
  `ApiName`).
- `IsClosed = true` stages are marked closed and never proposed.
- `Description` is worth reading. Some admins write exit criteria there.
  Anything found is marked "from the CRM" in setup.

## Record types and sales processes

```sql
SELECT Id, Name, DeveloperName, BusinessProcessId, IsActive
FROM RecordType
WHERE SobjectType = 'Opportunity'
```

Each record type points to a sales process, which uses a subset of the
stages.
- **Headless 360 (verified):** read the stages for each record type from
  the UI API picklist call above. Store them per record type.
- **SObject servers:** not readable. If there's more than one record
  type, ask the rep which stages apply to each.

## Validation rules and Path (Headless 360 only)

These are readable through the Tooling API, so setup can propose stage
requirements from the CRM itself instead of asking for all of them.

**Validation rules (verified):**

```sql
SELECT Id, ValidationName, Active, ErrorMessage, ErrorDisplayField
FROM ValidationRule
WHERE EntityDefinition.QualifiedApiName = 'Opportunity' AND Active = true
```

To read a rule's formula, query one rule at a time and include
`Metadata` (it can't be selected across many rows):

```sql
SELECT Id, ValidationName, Metadata FROM ValidationRule WHERE Id = '<Id>'
```

`Metadata.errorConditionFormula` holds the formula. A rule that checks
`StageName` and a field being blank, for example
`AND(ISPICKVAL(StageName, 'Id. Decision Makers'), ISBLANK(Economic_Buyer__c))`,
means that field is required to enter that stage. Propose it as a
required field marked "from the CRM," and show the rep the rule's error
message. Rules too complex to read confidently are listed for the rep
to interpret; don't guess.

**Path:**

```sql
SELECT Id, DeveloperName, SobjectType, SobjectProcessField, IsActive
FROM PathAssistant
```

This query works (verified). If the org has an active Opportunity Path,
read its steps' key fields and guidance for success and use them the
same way: key fields become candidate required fields, and guidance
becomes candidate exit criteria, all marked "from the CRM." (Reading the
step details is not yet verified on an org with a Path set up.)

**SObject servers:** neither is readable. Required fields per stage come
from the rep during setup, and validation rules still show up as errors
when writing.

## Checking how often a field is filled (setup step 4)

Salesforce can't filter or aggregate on Long Text Area or Rich Text
Area fields (verified: "field 'Description' can not be filtered in a
query call"). Pull the candidate fields for a sample of 50 recent open
opportunities and count non-empty values yourself. Keep the sample at
50: every record comes back in full, and 200 records produced a very
large response in testing without changing the answer.

```sql
SELECT Id, Champion__c, Economic_Buyer__c, Decision_Process__c
FROM Opportunity
WHERE IsClosed = false
ORDER BY LastModifiedDate DESC
LIMIT 50
```

Short text, picklist, number, and date fields can be counted directly
(verified): `SELECT COUNT(Id), COUNT(NextStep) FROM Opportunity WHERE
IsClosed = false`. Say in setup when counts come from a sample.

## Field details

**Headless 360 (verified):** one Tooling query returns every field's
API name, label, type, and length:

```sql
SELECT QualifiedApiName, Label, DataType, Length, IsNillable
FROM FieldDefinition
WHERE EntityDefinition.QualifiedApiName = 'Opportunity'
```

`DataType` comes back as readable text, for example `Long Text
Area(32000)`, `Text(255)`, `Picklist`, `Checkbox`, `Currency(16, 2)`,
`Date`, `Lookup(User)`.

**SObject servers:** `getObjectSchema` on `Opportunity`.

## Field types and how they map to actions

| Salesforce type | Treat as | Action rules |
|---|---|---|
| Text (up to 255) / `string` | short text, single line | Append if it fits, otherwise Review. Can't hold line breaks (verified): join entries with a space and check with `append_entry.py check --single-line` |
| Text Area (255) / `textarea` | short text | Append if it fits, otherwise Review |
| Long Text Area / `textarea` | long text, length from the field | Append |
| Rich Text Area | rich text | Append as a new `<p>` |
| Picklist | picklist | Replace |
| Picklist (Multi-Select) | multi-select | Add a value; removing one is a Replace |
| Checkbox | checkbox | Replace |
| Number, Currency, Percent | number | Replace |
| Date, Date/Time | date | Replace |
| Lookup | lookup | Replace; resolve the record with SOQL and show the name |

Skip formula, roll-up, auto-number, and system fields (Created By,
Last Modified, Stage Sort Order, and similar).

Standard fields to know:
- `NextStep`: Text, 255 characters, a status field (Review replacement).
- `Description`: Long Text Area (32,000). Append freely.
- `StageName`: the stage. Only changed through the stage flow.
- Two fields are labeled "Forecast Category" (verified):
  `ForecastCategoryName` is the editable one to map; `ForecastCategory`
  is a system field. Show the second as "Forecast Category (system)" if
  it comes up.
- `Probability` and `ForecastCategoryName`: default from the stage when
  `StageName` changes. Show that as a side effect. Don't write them
  directly unless the rep asks.
- `CloseDate`, `Amount`: Replace only, per-field approval.

## Reading a deal's current values

Salesforce returns empty fields as `null` (verified), so a mapped field
that comes back `null` is empty. (HubSpot leaves empty fields out
instead.)

## Listing deals for the rep (SKILL.md Step 2)

Rep's own open opportunities first, then others the rep can see:

```sql
SELECT Id, Name, Account.Name, StageName, Amount, CloseDate,
       LastModifiedDate, Owner.Name, OwnerId
FROM Opportunity
WHERE IsClosed = false AND OwnerId = '<rep user Id>'
ORDER BY CloseDate ASC
LIMIT 15
```

For the second group, change the filter to `OwnerId != '<rep user Id>'`.
Sharing rules limit results to records the rep can access. Show stage
labels, not stored values.

## Writing an opportunity

Send only the approved fields in one update (Headless 360: `PATCH` via
`dispatch`; SObject servers: `updateSobjectRecord`). Field-level
security and sharing apply to the rep automatically. A newly created
custom field is invisible to everyone, even admins, until field-level
security is granted; a field the rep can't see shows as "can't update."

Write order: fields, then `StageName`, then the evidence note, then the
audit note. If fields and the stage change need to land together to
pass a validation rule, send them in the same update and say so in the
confirm step.

## Evidence note

Same mechanics as the audit note below: a completed Task on the
opportunity, with `Subject` = the evidence note title from SKILL.md Step 5
(`CRM Deal Updater | Evidence | <date> <time> | <elements>`)
and the evidence grouped by methodology element in `Description`. Find
earlier ones with the same SOQL as the audit note, using
`Subject LIKE 'CRM Deal Updater | Evidence%'`.

## Audit note

A completed **Task** on the opportunity, which shows in the activity
timeline in both Lightning and Classic.

```json
{
  "Subject": "CRM Deal Updater | 2026-09-23 14:05 | 2 fields updated, stage unchanged",
  "Description": "<audit note text from SKILL.md Step 11>",
  "WhatId": "<opportunity Id>",
  "Status": "Completed",
  "ActivityDate": "<today>",
  "Priority": "Normal"
}
```

Task `Description` holds up to 32,000 characters. Confirm "Completed" is
a Task Status value (Headless 360:
`GET /services/data/v67.0/ui-api/object-info/Task/picklist-values/012000000000000AAA/Status`);
if not, use the org's closed status.

To find the last audit note on a later run:

```sql
SELECT Id, Subject, Description, CreatedDate
FROM Task
WHERE WhatId = '<opportunity Id>'
  AND Subject LIKE 'CRM Deal Updater%'
  AND (NOT Subject LIKE 'CRM Deal Updater | Evidence%')
ORDER BY CreatedDate DESC
LIMIT 1
```

The exclusion matters (verified): evidence notes share the title prefix,
and without it the newest match can be an evidence note with no
"Processed through" line.

For declined items (SKILL.md Step 3), run the same query without
`LIMIT 1` and read the "Declined" section of each audit note.

Some teams prefer Notes (`ContentNote` linked through
`ContentDocumentLink`) over Tasks. That takes two records instead of
one. Offer it only if the rep asks.

## Common failures

Read the error and translate it. Don't retry the same call unchanged.

| Error | Plain meaning | Offer |
|---|---|---|
| `FIELD_CUSTOM_VALIDATION_EXCEPTION` | A validation rule blocked it. The message says what's needed (verified, for example "Economic Buyer must be filled in before moving to Id. Decision Makers.") | Fill the named field from evidence, or hold the stage change |
| `REQUIRED_FIELD_MISSING` | A required field is empty | Same |
| `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` | That picklist value isn't allowed (possibly for this record type) | Re-read values, re-confirm with the rep |
| `STRING_TOO_LONG` | The text exceeds the field's length | Propose a condensed version as a Review item |
| `INSUFFICIENT_ACCESS_OR_READONLY` | The rep can't edit this field or record | Mark "can't update" and continue |
| `INVALID_FIELD` | A field doesn't exist or can't be used that way (for example filtering a long text field) | Re-check the map; on a query, drop the filter and count results directly |
| `UNABLE_TO_LOCK_ROW` | Someone else is editing | Wait briefly, try once more, then report |

When a validation error comes back, add the rule's requirement to the
saved stage map (with the rep's OK) so the next run checks it before
writing.
