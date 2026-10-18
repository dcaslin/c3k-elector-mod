# In-game test plan

Static validation and the headless load test only prove that the mod parses. These steps
check that it returns correct results. Use a save where you hold several elective titles
(Tanistry, Saxon Elective, and others if you have them).

## Setup

1. `scripts/install-macos.sh`, then enable **Elector Status** in the launcher playset.
2. Optional: launch with `-debug_mode` so the error counter is visible.
3. Load the save. For each elective title you hold, open its **Succession** view
   (title view → succession / election window) and note a few listed electors. This is
   the ground truth to compare against.

## How to use

Right-click a character → **Elector Status** (succession category, under "More" if the
menu is crowded) → **Send** → an event window lists the titles.

## Cases

| # | Case | How to pick the character | Expected |
|---|---|---|---|
| 1 | Known elector, Tanistry | Elector shown in a Tanistry title's election window | That title is listed |
| 2 | Known elector, Saxon Elective | Elector shown in a Saxon title's election window | That title is listed |
| 3 | Elector in several held titles | Someone in the elector list of 2+ of your titles (France: pick a vassal who also appears elsewhere) | Every such title is listed, highest tier first, no duplicates |
| 4 | Non-elector | A courtier, a child, or an unlanded guest | "…is not an elector for any title you hold." |
| 5 | Elector only for titles you don't hold | An elector of a foreign elective realm (open that title's election window to confirm) | That foreign title is **not** listed; "not an elector" unless they also vote in yours |
| 6 | Yourself (if the menu offers it) | Your own character | Any of your titles whose election you vote in |
| 7 | Read-only | Before/after case 1, check that election window's votes and candidate | Nothing changed; no opinion or notification side effects |
| 8 | Large list (if possible) | Someone voting in more than 20 of your titles | 20 lines plus the "…and more" line |

Spot-check France (50+ electors): pick 3–4 names from its elector list and confirm each
shows France.

## Hover tooltip

Hover any portrait (map, character view, outliner, character finder). For electors, a block
appears above "Click to view / Right-click to interact":

```
Elector for your titles:
    • Kingdom of Ireland: votes Murchad (vote forced)
Hook: weak, usable now
```

| # | Case | Expected |
|---|---|---|
| T1 | Known elector (case 1 above) | Header, the title, and "votes <name>" matching the election window |
| T2 | Non-elector | Tooltip unchanged from vanilla, with no extra lines |
| T3 | Elector in several titles | Up to 3 titles, highest tier first; 4 or more adds "…and more" |
| T4 | Elector you have a usable hook on | "Hook: strong/weak, usable now" |
| T5 | Elector whose secret you know (blackmailable) | "Hook: none, but you know a blackmailable secret" (agrees with the Blackmail interaction being highlighted) |
| T6 | Force an elector's vote (election window → Force Vote), then hover them | That title shows "(vote forced)", and the hook moves to "on cooldown" or disappears |
| T7 | An elector whose vote you have *not* forced | No "(vote forced)" |
| T8 | Hover yourself, a dead character, and a character in the finder list | No errors, and the text looks sensible |

"(vote forced)" uses the same engine check as the election window's forced-vote note. It
means *someone* controls that vote, not necessarily you.

## Afterwards

```sh
grep -n elector_status "$HOME/Documents/Paradox Interactive/Crusader Kings III/logs/error.log"
```

There should be no output. Loc data-function problems only show up once the event has been
displayed, so run this after testing.

If the mod lists something that differs from the election window, record the title, the
character, and the title's succession law. The mod relies entirely on the engine's
`election_title` list. A mismatch means the engine list and the window disagree (for
example, timing of the election recalculation), not a rules bug in this mod.
