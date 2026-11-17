# P6-15 FRAME: Group TOTO and iTOTO unit tickets in v1

Owner decision 2026-11-17: in v1. Today a unit ticket is recognised and refused
(`TicketDraft.supported` is False when `units` is set; `docs/web-api.md` and README say so).
This file is the FRAME and PLAN. No code yet. Criteria below are frozen once the owner answers Q1-Q3.

## 1 - What the rules say (docs/toto-4d-rules-reference.md, 2026 cl. 2.6; all `[V, 2026]`)
- **Group TOTO (2.6a):** one entry split into up to 10 equal units, at least S$7 per unit, in 10-cent multiples. The prize is split equally across the issued tickets. Ticket prints `UNIT NUMBER: k/n`; PRICE is per unit (specimen: 6 boards x 4 draws = $24 over 3 units = $8.00).
- **iTOTO (2.6b):** units of a System Roll or System 7-12 entry. The prize is split by the total number of units, sold and unsold; the buyer gets their units' share. Ticket prints `NUMBER OF UNITS PURCHASED: u of N` (specimen: System 12 = $924 / 28 = $33.00 per unit).
- **Sources on hand:** three official specimens only. No real Group TOTO or iTOTO photo exists, and none can be scraped (terms ban it). Tests use the specimen text as golden input, the same way System 8-11 were handled.

## 2 - What is already built
- `ticket_entry.py`: `_UNITS` regex reads both unit lines into `TicketDraft.units` as `(k, n)` for Group TOTO and `(u, N)` for iTOTO; a unit header with no count gives `(0, 0)` and a warning.
- `ticket.py`: `check_ticket` prices the whole entry; `TicketResult.total_won` is the whole-entry win, `None` while any group's amount is unpublished (never S$0).
- `reveal.py`: PRICE check compares `stake()` (whole entry, all draws) to the printed PRICE.
- Gaps: no share maths, no per-unit stake, `ready` refuses unit tickets, the two header forms are not told apart in the model (Group vs iTOTO), no reveal wording.

## 3 - Unknowns: RESOLVED by existing convention (owner 2026-11-17: follow the existing code; only unique things need a decision)
| # | Resolution | Basis |
| :-- | :--- | :--- |
| Q1 | **No rounding in the maths.** The share is a plain float division. Display goes through the existing `reveal.money()` (whole dollars bare, otherwise 2 decimals). | The code never rounds a prize today; `money()` is the one display rule. The official result stays final (reveal rule 4). |
| Q2 | **Yes, every prize is split**, fixed Groups 5-7 included. One path, no special case. | Cl. 2.6a splits "the prize"; the checker has one prize path (`TotoResult.amount`). |
| Q3 | **PRICE for a unit ticket = whole stake / n (Group) or whole stake x u / N (iTOTO), unrounded; the existing mismatch warning fires only above S$0.10.** A warning, never a block. | Existing PRICE check is already warn-only; 10 cents is the Group TOTO unit step. |

No decision is left for the owner. Anything new that turns up mid-build and has no existing precedent is raised then.

## 4 - Acceptance criteria (frozen 2026-11-17)
1. A Group TOTO ticket `k/n` and an iTOTO ticket `u of N` no longer produce "not supported"; `ready` is True when bets, draws and a non-zero unit count are present and there are no errors.
2. Group TOTO holder share of a won entry = entry win / n. iTOTO holder share = entry win x u / N.
3. A pending group (amount unpublished) stays pending for the share, never S$0 (reveal rule 1 holds).
4. Stake shown for a unit ticket is the per-unit price, and the PRICE cross-check compares like with like: whole stake / n for Group, whole stake x u / N for iTOTO.
5. The reveal says the amount is the holder's share, names the units ("1 of 28 units"), and keeps the claim-by and official-result lines.
6. A unit header with no unit line still warns and stays not ready (current behaviour, `(0, 0)`).
7. Ordinary and System tickets, and all 4D paths, are byte-for-byte unchanged in result.
8. The full suite stays green; every new behaviour has a named red test first.

## 5 - Slices (build sequence)
| Slice | Change | Target | Gate | Route |
| :-- | :--- | :--- | :--- | :--- |
| A | Pure share function: `unit_share(win, kind, units, rounding)` returns the holder's amount from the whole-entry win; `None` stays `None`. Stub plus red tests; rounding from Q1. | new `lottery_checker/units.py` (stub with sentinel) | `py -3 -m pytest tests/test_units.py -q` | Hand |
| B | Per-unit stake and PRICE comparison: `TicketDraft.stake()` and the mismatch warning use units. | `lottery_checker/ticket_entry.py` (30 KB file; in budget) | `py -3 -m pytest tests/test_ticket_entry.py -q` | Hand |
| C | Remove the refusal: `supported`/`problems()` accept a unit ticket with a real count; `check()` applies slice A to each line and the total. | `ticket_entry.py`, `ticket.py` (two files, so two attempts, ticket.py first) | `py -3 -m pytest tests/test_ticket_entry.py tests/test_ticket.py -q` | Hand, expect L1 on `check()` |
| D | Reveal wording for a share (criterion 5). | `lottery_checker/reveal.py` | `py -3 -m pytest tests/test_reveal.py -q` | Hand |
| E | OCR: Group/iTOTO headers and the unit line from specimen-shaped text through `ticket_ocr.py`. | `lottery_checker/ticket_ocr.py` | `py -3 -m pytest tests/test_ticket_ocr.py -q` | Hand; synthetic only |
| F | Web UI copy and `docs/web-api.md`, README. `web/index.html` is 85 KB, over the 80 KB cap. | `web/index.html` | browser smoke | `too-large`, Fixer |

Order: A, B, C, D, E, F. A has no dependency; C needs A and B.
**Delegable: 5 of 6.** Reason for zero: F `too-large`.
Catalogs at PLAN: Baker (core backend), Doris (assertions), Grace is not triggered (no stored data change). Slices run uncatalogued if no entry matches.

## 6 - Process notes for the build
- Before delegating each slice, apply a reference fix locally and run the whole gate file, then revert (P2-07-I lesson).
- Specimen golden text lives in the red tests. Never add the specimen images to git.
- Stored accounts history keeps bets and outcome only; a unit ticket saves the same fields plus nothing new (no unit serials). Confirm before slice C touches history.

## 7 - Stop point
Slice A cannot be written until Q1 is answered, because the test asserts a rounded number. If the owner cannot get the clause text, build slice A with the "about" default in section 3 and flag it as an assumption in the spec, the way iBet two-permutation payout is flagged in the BRAIN.
