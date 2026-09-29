# CRM Deal Updater

A Claude Skill that keeps a deal or opportunity current from what was
actually said on calls and in email, organized the way your company
sells: your pipeline stages, your fields, and your methodology.

It proposes. The rep decides. Nothing is written to the CRM until the
rep approves it.

## What it does

- **Reads the conversations.** Pulls calls, emails, and notes for the
  account through the [unified-communication](https://github.com/dhand-personal/unified-communications)
  skill, or works from a pasted transcript, email, or notes.
- **Maps them to your methodology.** MEDDPICC by default; also Command
  of the Message, Sandler, BANT, SPICED, and others, or a blend. Setup
  discovers your stages and fields and confirms the map with you once.
- **Proposes field updates with sources.** Every value names the call
  or email it came from. New information is added to what's there, not
  written over it. Replacing anything takes approval on that field.
- **Checks the stage.** Suggests a move forward or back only when your
  stage's exit criteria say so, and checks required fields before
  proposing it. Never proposes Closed Won or Closed Lost.
- **Leaves a trail.** An audit note on the deal records what changed,
  what the rep declined, and which sources were used, so the next run
  picks up where this one left off and doesn't re-propose declined items.
- **Keeps the record clean.** Holds back opinions about people,
  personal details, and anything said off the record.

## CRMs supported

| Setup | What happens |
|---|---|
| HubSpot with its MCP connector | Reads and writes directly, after approval |
| Salesforce with an MCP connector (Headless 360 or the SObject servers) | Reads and writes directly, after approval |
| No connector, or any other CRM (Pipedrive, Dynamics, a spreadsheet) | Snapshot mode: you share an export, screenshot, or the included template, and get back an approved update list to enter by hand |

## Installation

### Claude.ai, Claude Desktop, and Cowork

1. Download this repository as a zip: **Code → Download ZIP** on this page (or
   `git clone` it).
2. In Claude, go to **Settings → Capabilities → Skills → Upload skill**.
3. Select the downloaded zip. `SKILL.md` is at the root of this repo, so no
   repackaging is needed.
4. Enable the skill.

This upload is per-account. If you're on a Team or Enterprise plan, you can share
it with your organization from the same settings screen instead of everyone
uploading individually.

### Claude Code

```bash
git clone https://github.com/dhand-personal/crm-deal-updater.git ~/.claude/skills/crm-deal-updater
```

Or, for just this repo/project:

```bash
git clone https://github.com/dhand-personal/crm-deal-updater.git .claude/skills/crm-deal-updater
```

Restart your session after installing.

### Recommended

Install [unified-communication](https://github.com/dhand-personal/unified-communications)
too, so the skill can pull calls and email on its own. Without it, paste
a transcript, email, or notes into the conversation.

## Using it

Ask in plain words: "update the Acme deal," "log yesterday's call to the
CRM," "is this deal ready to move stages?" The first run walks through a
short setup. After that, each run shows a review table of proposed
changes with sources, asks for approval, and writes only what you
approve.

## What's in this repo

```
SKILL.md                    instructions Claude follows
references/                 CRM specifics, field and stage rules,
                            methodologies, snapshot mode, content rules
assets/snapshot-template.md a fill-in snapshot for reps without a connector
scripts/manage_config.py    saved mapping per CRM (stored locally)
scripts/append_entry.py     entry formatting, duplicate and length checks
```

The skill saves its field and stage map locally at
`~/.crm-deal-updater/config.json`. It never changes your CRM's fields,
stages, or pipelines.

## Testing and known limits

Tested against a live HubSpot account and a live Salesforce org, with
test deals only, plus snapshot mode with a Pipedrive-style export and
screenshots. Not yet tested:

- HubSpot accounts with Sensitive Data turned on (notes may be hidden
  from the connector)
- Salesforce Path steps as a source of stage requirements
- The deal list with more than 15 open deals, and repeated stage names
  across several pipelines

Treat it as a careful assistant, not an autopilot: the review step is
the point.

## License

MIT. See [LICENSE](LICENSE).
