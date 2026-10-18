# AGENTS.md

Instructions for agents (and humans) continuing work on this repo. Workspaces are
ephemeral git worktrees; everything needed to continue lives here, not in local state.

## What this is

A Crusader Kings III (CK3) utility mod with two read-only features:

- **Hover tooltip:** every character portrait tooltip (map, character view, outliner,
  character finder) gains a block when that character is an elector for a title the
  player holds. It shows up to 3 titles, who they currently vote for, whether their vote is
  forced, and the player's hook / known blackmailable secret on them. Non-electors'
  tooltips are unchanged.
- **Interaction:** right-click → **Elector Status** lists every matching title (up to 20).

Nothing changes votes, characters, laws, or succession.

Target game version: **CK3 1.20.1.1 (Crozier)** on macOS (`supported_version="1.20.*"`).

## Layout

```
elector_status/                      # the mod itself; this folder is what gets installed
  descriptor.mod                     # mod metadata (install script adds path=)
  common/character_interactions/elector_status_interactions.txt
  common/scripted_effects/elector_status_effects.txt
  common/customizable_localization/elector_status_custom_loc.txt   # tooltip lines
  events/elector_status_events.txt
  localization/english/elector_status_l_english.yml
  localization/replace/english/elector_status_replace_l_english.yml  # the one vanilla key we replace
scripts/install-macos.sh             # copy mod into the stable CK3 mod dir
scripts/validate.py                  # static checks (no game launch)
scripts/load-test-macos.sh           # headless CK3 parse/load test
config/local.env.example             # machine-specific path overrides
docs/TESTING.md                      # in-game test plan
```

## Architecture: hover tooltip

The last paragraph of every portrait tooltip (`cooltip_type` in vanilla
`gui/shared/cooltip.gui`, instantiated from `gui/shared/portraits.gui` and
`gui/hud_outliner.gui`) is the multi-line loc key `CHARACTER_TOOLTIP_INSTRUCTION`
("Click to view / Right-click to interact"), with `Character` in context. The mod replaces
**only that loc key** (via `localization/replace/`). It keeps the vanilla text and prepends
six `[Character.Custom2('ElectorStatusTT…', GetPlayer)]` calls. No GUI file is overridden.

Each custom loc (`common/customizable_localization/elector_status_custom_loc.txt`) runs with
`root` = hovered character and `scope:second` = player. It returns `elector_status_tt_empty`
unless `any_election_title = { holder = scope:second }`.

- `ElectorStatusTTTitle0..2`: `setup_scope` saves the Nth title (`ordered_election_title`,
  `order_by = tier`) and, via `random_election_candidate` + `has_election_vote_of`, the
  candidate the elector currently votes for. The trigger re-checks `count >= N+1` (same
  capping issue as the event). The loc line shows the title, the vote, and
  `(vote forced)` when the GUI function `Title.CanCharacterControlVote(elector)` is false.
  That is the same check vanilla `gui/shared/succession_election_widgets.gui` uses to show
  `SUCCESSION_ELECTION_WINDOW_VOTE_BREAKDOWN_FORCED_VOTE`. There is **no script trigger**
  for forced votes in 1.20.1.1; this GUI function is the only access.
- `ElectorStatusTTHook`: strong/weak × usable/cooldown via `has_strong_usable_hook`,
  `has_strong_hook`, `has_usable_hook`, `has_hook`. Otherwise "you know a blackmailable
  secret" via vanilla's `is_blackmailable_secret_trigger` + `is_known_by` (the same checks as
  the vanilla Blackmail interaction; unknown secrets are never revealed).
- Inside custom-loc output keys, `ROOT.Char` is the custom-loc root and `SCOPE.sTitle('x')`
  resolves `setup_scope` saves (vanilla precedent: `love_letter_text`).

`validate.py` fails if the vanilla text inside the override no longer matches the installed
game (check after every CK3 patch). Another mod that also replaces
`CHARACTER_TOOLTIP_INSTRUCTION` would conflict; the last one loaded wins.

## Architecture: interaction

1. `elector_status_interaction` (category succession, `auto_accept = yes`, players only,
   no diplomatic range limit). `on_accept` fires `elector_status.0001` on `scope:actor`.
   Interaction scopes `scope:actor` / `scope:recipient` carry into the event.
2. `elector_status.0001` `immediate` runs `elector_status_collect_titles_effect`, which in
   `scope:recipient` copies matching titles into numbered saved scopes
   `elector_status_title_0..19` via `ordered_election_title` (`order_by = tier`,
   `limit = { holder = scope:actor }`, `position = N`).
3. The event `desc` concatenates one `triggered_desc` per slot, so the list renders as
   bullet lines; `first_valid` picks the "is an elector" or "is not an elector" intro.
   More than 20 matches shows an overflow line.

Why this shape:

- **Eligibility comes from the engine.** `election_title` is the engine list "Iterate
  through all titles the scoped character can vote on" (scope: character, target:
  landed_title; confirmed in the 1.20.1.1 `triggers.log`/`effects.log`, and used by vanilla
  `common/important_actions/00_inheritance_actions.txt`). Every `common/succession_election`
  type (Feudal, Princely, Gaelic/Tanistry, Saxon, Scandinavian, Tribal, Confederation,
  clerical) and any modded type is covered with no rule re-implementation. Do not
  hand-code elector rules.
- **Localization can't iterate lists**, hence numbered slots. Each slot is guarded by
  `any_election_title = { count >= N+1 holder = scope:actor }` because `ordered_`
  *caps* an out-of-range `position` to the last element (it would duplicate titles).
  Same guard + position pattern as vanilla `common/activities/activity_types/coronation.txt`.
- **No persistent state.** Saved scopes and scope values die with the event. No flags,
  variables, on_actions, or periodic scans. No vanilla file is overridden; all files use
  unique `elector_status_` names (validate.py checks for path collisions). The only vanilla
  override is the single replaced loc key described above.
- The confirmation window (Send → event) is accepted for v1: `needs_confirmation` would
  skip it but is documented as deprecated.

Changing the slot count means editing all three: the `N = .. COUNT = ..` calls and the
overflow `count >=` in the effects file, the `triggered_desc` blocks in the event, and the
`line_N` / overflow keys in loc. `validate.py` fails if they drift.

## Conventions

- All script `.txt` and loc `.yml` files must be **UTF-8 with BOM** (CK3 logs
  "should be in utf8-bom encoding" otherwise). Loc files: `*_l_english.yml`, first line
  `l_english:`, entries indented one space.
- Tabs for indentation in script, matching vanilla.
- Prefix every key, event namespace, and scope name with `elector_status`.
- Before using any trigger/effect/iterator, confirm it in the generated script docs (below)
  and preferably find a vanilla usage. Don't describe untested script as working.

## Paths and configuration

Defaults (override with env vars or `config/local.env`, copied from the example):

| Variable | Default |
|---|---|
| `CK3_USER_DIR` | `~/Documents/Paradox Interactive/Crusader Kings III` |
| `CK3_GAME_DIR` | `~/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game` |

Never point CK3 at this workspace. The installed copy lives at
`$CK3_USER_DIR/mod/elector_status/` with descriptor `$CK3_USER_DIR/mod/elector_status.mod`.

## Install

```sh
scripts/install-macos.sh            # validates, then rsyncs into the CK3 mod dir
scripts/install-macos.sh --dry-run  # show paths only
```

Then enable **Elector Status** in a playset in the Paradox launcher. Re-run the script
after every change; the installed copy is a mirror (`rsync --delete`, scoped to its folder).

## Verification (three levels; say which one you did)

1. **Static** — `python3 scripts/validate.py` (about 1s): BOMs, brace balance, loc file format,
   referenced loc keys exist, slot-count consistency, no vanilla path collisions, and every
   `any_/every_/random_/ordered_` list name appears in the CK3 binary. `--no-game` skips
   the install-dependent checks. Catches typos only; it knows nothing about scopes.
2. **Headless load test** — `scripts/load-test-macos.sh` (about 40s; Steam running, CK3 closed,
   mod installed). Launches CK3 with only this mod, runs `script_docs`, exits, and fails on
   any `error.log` line mentioning `elector_status`. CK3 reports unknown triggers/effects
   and unknown loc keys in dynamic descs at load. It restores `dlc_load.json` and logs
   on exit. Proves the mod parses; does not prove behaviour.
3. **In-game** — follow `docs/TESTING.md`. Only this level verifies results. Agents
   can't drive the game; ask the user to run it and report back.

## Development mode, script docs, error.log

- **Debug mode:** Steam → CK3 → Properties → Launch Options: `-debug_mode`
  (add `-suppress_error_log` to stop error.log auto-opening). Gives the `~` console and
  an error counter. Other flags: `game/_commandline_options.info` in the CK3 install.
- **Generate API docs** (no GUI interaction needed):
  ```sh
  cd "$HOME/Library/Application Support/Steam/steamapps/common/Crusader Kings III/binaries/ck3.app/Contents/MacOS"
  ./ck3 -debug_mode -suppress_error_log -run_console_action=script_docs
  ```
  Writes `triggers.log`, `effects.log`, `event_targets.log` to `$CK3_USER_DIR/logs/`.
  In-game console equivalents: `script_docs`, `dump_data_types` (loc/GUI data functions).
  The load test runs `script_docs` too. Never commit these outputs (`.gitignore` covers it).
- **error.log:** `$CK3_USER_DIR/logs/error.log`, rewritten every launch.
  `grep elector_status "$HOME/Documents/Paradox Interactive/Crusader Kings III/logs/error.log"`.
  Loc data-function errors (for example a bad `[scope.Function]`) only appear after the event
  or tooltip has actually been displayed, so check again after in-game testing. The headless
  load test cannot catch them.
- **Character finder:** its filter categories are hard-coded in the engine (not in any
  script file), so a true "electors only" filter isn't moddable. Portrait hovers in the finder
  already show the tooltip block. A per-row marker would require overriding the vanilla GUI
  type `widget_character_list_item_finder` (`gui/shared/lists.gui`); this hasn't been done.

## Do not commit

Vanilla game files or excerpts beyond short API references, saves (`*.ck3`), logs,
generated script docs/data types, or `config/local.env`.
