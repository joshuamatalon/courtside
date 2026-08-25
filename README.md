# Courtside

Volleyball match tracker for coaching from the sideline. Score, rotations, stats,
lineups, subs and scouting on one phone.
**Runs with no internet. Installs to a phone home screen. Not tied to Claude.**

Ported off the claude.ai artifact on 2026-08-25. Shares its entire design system with
[Pass Chart](../passchart) — same palette, type scale, spacing rhythm and components.

---

## What it does

- **Track** — tap Point US / Point THEM every rally. Score, who is serving, and which
  of the six rotations you are in all track themselves. The court diagram below shows
  exactly where everyone should be standing, with the setter ringed and Zone 1 starred.
  Tap a player, tap what they just did, and it lands in that set's stats.
- **Stats** — kills, attack errors, hitting %, serve-receive pass average, aces, missed
  serves, serve %, digs and blocks. Match totals or the current set.
- **Lineup** — 5-1 / 6-2 / 4-2, the starting six in serving order, who plays what
  position this match, and a browser for all six rotations. Save named lineups for
  the season and load one in a tap.
- **Subs** — count against a per-set limit, tap who is out then who is in. The live
  lineup updates, so the court diagram stays truthful.
- **Scout** — an opponent card per team: key players with tendencies, plus free notes.
- **Roster** — names, numbers, positions, and a JSON backup you can move between phones.

Both point buttons say what the tap will do to your serve — *sideout · rotate*,
*hold serve*, *we lose serve* — so a rotation is visible before it happens rather
than read off afterwards.

---

## Getting it onto a phone

**Do not double-click `index.html`** — a home-screen app requires the files to be
served over http/https.

- **iPhone** — open the URL in Safari → Share → **Add to Home Screen**
- **Android** — open in Chrome → menu → **Install app**

### First run

Ships with a generic roster (`Player 1..15`) and no team name, because the deployed
page is public and baking one team's real names into it would publish them to anyone
with the URL. Setup takes about fifteen seconds:

1. **Roster** → paste the whole list into **Paste names** (one per line, jersey number
   first if you want it: `7 Riley`) → **Fill roster**
2. Tap each player's positions — the court rings whoever is set to **S**
3. **Roster → Team name**

Those names then live only on that phone.

### Running it locally

```bash
python -m http.server 8788 --bind 127.0.0.1
```

Then <http://127.0.0.1:8788/>.

### Pushing an update

`git push`, then **bump the `CACHE` string in `sw.js`** — otherwise phones that already
installed it keep serving the version they first cached.

---

## Offline: what is and isn't true

**Everything works with the phone in airplane mode.** Opening the app, scoring,
rotation tracking, stat logging, subs, lineups, scouting, the leaderboard, backup and
restore. Courtside makes **zero** network calls of any kind once the shell is cached —
there is no API, no font fetch, no analytics.

That is the whole reason for the port. The artifact failed this twice over: it loaded
from claude.ai, so it needed a connection just to open, and it saved to
`window.storage` — a **server-backed** store — so offline saves silently failed and a
logged-out coach lost everything on page close.

---

## Where the data lives

On the device, in two independent local stores:

- **localStorage** — written synchronously on every tap. Cannot be interrupted,
  rate-limited, or lost to bad signal.
- **IndexedDB** — an async mirror with a much bigger ceiling.

On startup both are read and whichever has the higher revision wins, so if the browser
evicts one the other restores the match. (Tested: wiping localStorage entirely and
reloading recovered the score, serve and rotation.)

**Still take backups.** **Roster → Save backup** writes a JSON file; **Restore** reads
it back. That is also how you move a season between phones.

**"New match" is undoable once.** It stashes the finished match, and an
**Undo "New match"** button appears under Backup until you start another. Export if you
want to keep a match for good — there is still no season history (see Known limits).

---

## The volleyball logic, and how it was checked

The handoff flagged the rotation maths and undo-point as the highest-risk untested code.
Both were verified before anything was built on top of them, and both were **correct** —
they are ported verbatim rather than rewritten.

**Rotation.** A player moves one zone clockwise each rotation: 2 → 1 → 6 → 5 → 4 → 3 → 2.
At rotation 1, serving order N stands in zone N. Checked exhaustively: a valid
permutation at every rotation, exactly one clockwise step per rotation, returns to the
start after six, and the server walks 1,2,3,4,5,6 in order.

**Sideout.** You rotate **only** when you win a rally you were not serving. Winning while
already serving keeps the same server and rotation. Checked: five straight points on
serve do not rotate; a sideout rotates exactly once and takes the serve; losing your
serve does not rotate you; an opponent run does not rotate you; six sideouts walk
0,1,2,3,4,5,0.

**Undo.** Score, serve and rotation are restored *together* from the point's own record.
Checked by playing 30 random points and unwinding them one at a time, asserting the full
state matched at every step.

---

## Testing

```bash
python tools/check.py          # syntax + structure, ~1s
```

Parses the inline script with node, then verifies every referenced function and CSS
class exists, that nothing fetches over the network, that no `window.storage` remains,
and the phone rules (touch-action, dvh shell, 16px input floor, pinch-zoom allowed).
It strips comments before matching — several of those rules are explained in comments
that quote the very thing they forbid.

```bash
python -m http.server 8788 --bind 127.0.0.1
# then open http://127.0.0.1:8788/tools/selftest.html
```

**114 assertions** driving the real app in a frame: rotation geometry, sideout scoring,
undo-point unwinding, stat maths, saved-lineup apply/save-over, subs updating the live
court, no sideways scroll at 320/360/390/430 px, a locked nav bar, tap targets, the
iOS zoom rules, every screen rendering, persistence across a reload, IndexedDB rescue,
the backup round trip, and the live scoring loop itself.

It backs your data up before it runs and restores it afterwards **through the app's own
save path** — restoring localStorage alone is not enough, because the IndexedDB mirror
would win on revision and hand back the test data.

**The suite was itself tested.** Rotation was deliberately sabotaged to confirm the
suite fails — it did, on two assertions, and it exposed a third that passed anyway
because "ends at rotation 0" is also true when rotation never moves. That one now
asserts the sequence `0,1,2,3,4,5,0`.

---

## The intent pass — does it actually work mid-rally?

Everything above says the app is *correct*. That is not the same as saying a coach can
use it, and it failed that test badly the first time.

`render()` tears down and rebuilds the screen. It threw the scroll position away, so
**every tap fired the coach back to the top of a page 2.77 viewports tall.** Measured:
`scrollTop 900 → 0` on a stat, a point, and a player chip alike. The real loop was:
scroll down, log one kill, get sent to the top, scroll down again. Correct code, right
colours, unusable.

Three fixes, all measured:

- **The controls used every rally are pinned.** Point US / Point THEM, the running score,
  the rotation, and Undo point live in a bar between the scroller and the nav — a real
  layout row, never `position:fixed`, for the same iOS toolbar reason as the nav itself.
- **Scroll survives a rebuild.** It is carried across and restored *after* the pinned bar
  is built. Restoring before that silently clamps it: while the slot is empty `main` is
  120px taller and its maximum scroll is smaller, so asking for 576 landed on 494.
- **Track lost ~700px of duplication.** The point row is no longer drawn twice, and
  "Positions this match" — a 15-row panel of dropdowns — lives on the Lineup tab only
  instead of being repeated at the bottom of the live screen.

Result: **0px of scroll drift across 13 consecutive taps**, and the point buttons are
reachable without scrolling from any position.

### What fits on screen at once

Measured with a 15-player roster, parked at the best scroll position:

| viewport | player chips | stat keys | point buttons |
|---|---|---|---|
| 844 (iPhone 14) | 15 / 15 | 12 / 12 | 2 / 2 |
| 750 | 15 / 15 | 10 / 12 | 2 / 2 |
| 667 (iPhone SE) | 15 / 15 | 10 / 12 | 2 / 2 |

On a small phone the two that fall below the fold are **Dig and Block** — the least
time-critical, and typically logged after the rally rather than during it. Kills,
errors, aces and the pass ratings are always visible.

### A full match, played

Three sets to 25 with subs and a lineup change, 126 rallies: every rally scored exactly
one point, rotations stayed legal in all three sets, match totals equalled the sum of
the sets, and the whole thing came to **17 KB**. The 200-entry event log caps *undo
depth*, never the stats themselves — those live separately and are never trimmed.

## Three bugs found by looking

Neither threw an error and neither looked broken in a quick glance.

**The stats table hid every player's name.** Seven numeric columns filled the row, and
`.tname` had `min-width:0`, so it collapsed to **zero width** — perfectly correct figures
next to nobody. Fixed with a real minimum width, fewer columns per table, and a scroll
box; the suite now asserts no name column is ever narrower than 40px.

**Every tap scrolled the page back to the top.** See the intent pass above.

**Highlighted figures rendered as buttons.** The cell modifier was `.tcell.key`, and
`.key` is also the stat-button class — so those cells picked up a border, a background
and a 56px height. A class-name collision, the same species as one found in Pass Chart.
Renamed, with assertions on row height and cell border.

---

## Files

```
index.html               the entire app - no build step, no dependencies
manifest.webmanifest     makes it installable
sw.js                    offline cache (bump CACHE to push an update)
icons/                   the six-zone court mark, Zone 1 lit
tools/check.py           static checks
tools/selftest.html      the 100-assertion browser suite
tools/make_icons.py      regenerates the icons
```

No npm, no framework, no build. Edit `index.html` in any text editor and reload.

---

## Known limits

- **No season history.** "New match" clears the match (undoable once). There are no
  per-match archives or season-long totals. The coach was asked and has not answered.
- **Each phone is its own island.** Nothing syncs between coaches. Two coaches logging
  produce two separate stat sheets; moving data means Save backup → send file → Restore.
- **Substitution legality is not enforced** — only a raw count against a limit. No
  re-entry pairing, no libero rules.
- **Not opened on a physical phone.** Everything was verified in desktop Chrome at
  emulated widths of 320–430px. Layout and sizing are measured, but type renders
  differently on iOS (SF Pro vs Segoe) and the install flow itself is untested there.
- **The overlap with Pass Chart is real.** Courtside's "Serve-receive pass 0–3" group
  logs exactly what Pass Chart exists to log, for the same team. Pass Chart tracks it
  across a whole season with a per-player trend; Courtside forgets it on "New match".
  Worth deciding which one owns passing rather than tapping the same grades twice.
