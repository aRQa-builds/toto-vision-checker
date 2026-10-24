# SG Toto and 4D: Rules Reference (v0.3, 21 Oct 2026)

Working reference for the matcher, parser and payout logic. Every line is tagged:

- **[V]** read from the official rules text (version noted)
- **[V, SP page]** read from an official Singapore Pools how-to page (not the rules PDF)
- **[V, SP specimen]** read from an official Singapore Pools specimen ticket image
- **[D]** derived by us, with the check noted
- **[?]** not confirmed, so do not code it until confirmed

Do not hard-code prize amounts from this file without re-checking the live rules, because operators revise them.

## Changes in v0.3 (21 Oct 2026)
- 4D printed ticket layout added, read from the five annotated specimen tickets on Singapore Pools' bet slip page (new section "4D printed ticket layout").
- iBet stake conflict resolved: the specimen iBet ticket charges the marked amount once. Open item 2 closed for stake; real photos are now only needed for OCR training.
- Draw line on tickets: real Toto tickets print one line per draw with the draw number as NNNN/YY (e.g. "THU 24/09/26  4220/26").
- Toto printed ticket layout added from two real tickets and three official specimens (Ordinary, Group TOTO, iTOTO System 12).

## Changes in v0.2 (17 Oct 2026)
- Toto System table: the full 2026 cl. 5.16 table now matches the derived algorithm (was 18 rows only). Open item 1 closed.
- 4D Roll, System and iBet stake rules confirmed from Singapore Pools' bet slip page. Open item 2 closed for stake; a real ticket photo is still wanted for the OCR layout.
- Group TOTO and iTOTO confirmed in the 2026 Toto rules (cl. 2.6). Open item 6 updated.
- Toto set-by-set matching now confirmed in the 2026 text (cl. 5.8 to 5.9, 5.14 to 5.15).

## Sources and versions

| Game | Version used | Link |
|---|---|---|
| Toto (current) | Effective 2 Mar 2026 17:00, from Draw 4161/2026 | https://www.gra.gov.sg/api/media/29a5030f-b1f3-4441-92cf-f48651458562/toto-game-rules_2mar26.pdf |
| Toto (older, cross-check) | From Draw 3751/2022 | https://www.gra.gov.sg/docs/default-source/game-rules/sppl-games/toto-game-rules-(general).pdf |
| 4D (current) | Dated 30 Dec 2024, from Draw 5269/2024 | https://www.singaporepools.com.sg/en/rules/Pages/pdf/4d-game-rules.pdf |
| 4D (older, cross-check) | 24 Sep 2021 | https://www.gra.gov.sg/docs/default-source/game-rules/sppl-games/4d-game-rules-(general).092421v.1.3.pdf |
| 4D bet slip guide (stake rules) | Singapore Pools, read 17 Oct 2026 | https://www.singaporepools.com.sg/en/services/Pages/placing-4d-bets-using-bet-slips.html |
| 4D specimen tickets | Same page, images read 21 Oct 2026 (draw dated Sat 26/04/14) | .../en/services/Pages/images/outlet-lottery-4dticket-{ord,roll,sys,ibet,sold}.jpg |
| 4D microsite (iBet prize split) | Singapore Pools, read 17 Oct 2026 | https://www.singaporepools.com.sg/ms/lotteryhomepage/4d/index.html |
| Index of current rules | GRA | https://www.gra.gov.sg/licenses-approvals/regulatory-approvals-for-other-gambling-operators/games/game-rules/lotteries-game-rules-(singaporepools) |

The GRA copy of the 2024 4D PDF could not be fetched (robots block), so the Singapore Pools copy was used.

## TOTO

### Draw
- [V] Six numbers drawn from 1 to 49, then one Additional Number from the remaining 43 (cl. 2.1 to 2.2).
- [V] A set wins only if it matches at least 3 of the six. The Additional Number is not counted toward the match count (cl. 2.2, 5.2).

### Prize groups (cl. 5.5)

| Group | Match | Prize basis |
|---|---|---|
| 1 | 6 | 38% of Prize Pool plus snowball, $1,000,000 minimum |
| 2 | 5 + Additional | 8% of Prize Pool plus snowball |
| 3 | 5 | 5.5% of Prize Pool plus snowball |
| 4 | 4 + Additional | 3% of Prize Pool plus snowball |
| 5 | 4 | Fixed $50 per winning combination |
| 6 | 3 + Additional | Fixed $25 per winning combination |
| 7 | 3 | Fixed $10 per winning combination |

- [V] Prize Pool is 54% of net stake collection, less GST (cl. 5.4).
- [V] Groups 1 to 4 are pool-based and split equally among winning shares. Groups 5 to 7 are fixed (cl. 5.13).
- [V] Snowball: unwon Jackpot and Groups 2 to 4 roll into the next draw. Groups 2 to 4 roll until won (cl. 5.10 to 5.11).
- [V] Cascade: if the Jackpot is unwon at the trigger draw (default 4 consecutive draws), it goes to Group 2, then 3, 4, 5, 6, 7 in order, whichever first has winners. Winners in that group also get their normal prize (cl. 5.12). Singapore Pools may set the trigger lower, not higher.
- [V] Prize amounts may be rounded by Singapore Pools (cl. 5.7). Results, including prize amounts, are as published on the Singapore Pools website and may be rectified (cl. 4.2).
- Implication: a cascade draw uses the same match rules, and only the payout figure differs. The checker must treat the payout as a per-draw published value, not a constant.

### Entry types and stakes (cl. 2.3, 3.4 to 3.5)
- [V] Ordinary: each set of 6 costs $1 per draw. Minimum $1, in $1 multiples, GST included.
- [V] System Roll: 5 chosen numbers combined with each of the other 44, so 44 sets, $44.
- [V] System 7 to 12: every 6-number combination of the chosen numbers.

| System | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|
| Sets | 7 | 28 | 84 | 210 | 462 | 924 |
| Stake | $7 | $28 | $84 | $210 | $462 | $924 |

- [V, 2026] Each set is matched on its own, and each set wins at most one prize, the highest it qualifies for (cl. 5.8 to 5.9). An Ordinary entry earns at most one winning share or fixed prize (cl. 5.14). A System entry can earn several (cl. 5.15).
- [V, 2026] Group TOTO: one entry split into up to 10 equal units, at least S$7 per unit in 10-cent multiples; the prize is split equally across the issued tickets (cl. 2.6a).
- [V, 2026] iTOTO: Singapore Pools offers units of a System Roll or System 7 to 12 entry; the prize is split by the total number of units, sold and unsold, and the buyer gets their units' share (cl. 2.6b).
- Implication: a Group TOTO or iTOTO ticket needs the unit count and total units from the ticket to compute the holder's share. Still out of scope for v1 unless decided otherwise.

### System entry winning shares (official table: 2026 cl. 5.16)
- [D] Algorithm: let N be the number of chosen numbers, w how many of them are among the 6 winning numbers, and a = 1 if the Additional Number is also chosen. Enumerate every 6-combination of the chosen numbers. A combination with i winning numbers and j additional (0 or 1) gets the group from the prize table above. The shares per group are the counts of combinations in each group. For System Roll, take the 5 chosen numbers plus each of the other 44.
- [V + D] Cross-check, 17 Oct 2026: the full cl. 5.16 table (10 scenarios, columns System Roll, Ordinary and System 7 to 12) was transcribed from the 2026 PDF and diffed against the algorithm. 178 group cells compared, 0 mismatches, and the algorithm produces no wins in any scenario the table omits. The algorithm is now the verified source for the System share table.
- Scripts in this project: `toto_system_shares.py` (algorithm) and `verify_cl516.py` (the official table and the diff).
- Worked examples:
  - System 8, all 6 winning plus Additional chosen: Jackpot 1, G2 6, G3 6, G4 15 (28 sets).
  - System 7, 4 winning, no Additional: G5 3, G7 4.
  - System Roll with 5 numbers all winning: G1 1, G2 1, G3 42.
  - System 12, 3 winning plus Additional chosen: G6 28, G7 56.

### Multi-draw
- [V] Non-subscription bets can be placed from 15 days to 30 minutes before a draw (cl. 3.6). Consecutive-draw entry is at Singapore Pools' discretion (cl. 2.7).
- [V] TOTO Subscription: the same numbers for 10 consecutive draws (cl. 2.8 to 2.11, 3.9). If funds are short, no bet is placed but that draw still counts as used (cl. 3.8).
- Implication: a multi-draw ticket is one ticket checked against several draws. The parser must capture the draw number or date range, and the checker must loop over each draw.

### Printed ticket layout (Toto)
Sources: two real Ordinary QuickPick tickets photographed 21 Oct 2026 (draws 4216/4217 and 4220/4221), plus three official specimens on Singapore Pools' Toto bet slip page (outlet-lottery-tototicket.jpg, -grouptoto.jpg, -itoto.jpg).
- [V, real ticket] Top: "TOTO". Real 2026 tickets then print two notice lines ("No more cheques from 1 Nov 2026", "Link NRIC to PayNow for payouts") before the bet type. The parser must skip notice lines rather than expect the header on line 2.
- [V, real + specimen] Bet type header: "ORDINARY", "GROUP TOTO - ORDINARY", "ITOTO - SYSTEM 12". System entries presumably print "SYSTEM n" (not yet seen on a plain System ticket).
- [V, real + specimen] Boards lettered A, B, ... Numbers are zero-padded two digits ("03"). "QP" after a board marks Quick Pick. A System 12 board wraps its 12 numbers over two lines.
- [V, real] Draw block: "DRAW:" then one line per draw, "THU 24/09/26  4220/26" (weekday, DD/MM/YY, draw number NNNN/YY). Confirmed against third-party results: 24 Sep 2026 = draw 4220, 28 Sep = 4221, 10 Sep = 4216, 14 Sep = 4217. Specimens may list draws in two columns (Group TOTO shows four draws in a 2x2 grid).
- [V, real] "PRICE:" is the total for all boards across all draws: 2 boards x 2 draws = $4.00.
- [V, specimen] Group TOTO: "UNIT NUMBER: 3/3" under the price; the price is per unit (6 boards x 4 draws = $24 over 3 units = $8.00).
- [V, specimen] iTOTO: "NUMBER OF UNITS PURCHASED: 1 of 28"; System 12 = $924 / 28 units = $33.00.
- [V, real] Then purchase timestamp ("23/09/26 01:51 PM"), two serial lines, two codes on the right, barcode. Do not parse these for matching.
- [?] System 7 to 11 and System Roll tickets: no official specimen and no published photo found (21 Oct 2026). Collect real ones.

### Variants
- [?] Hong Bao and other special draws: not covered in the general Toto rules. Likely governed by a promotion or draw-specific notice. Find that source before supporting them.
- [V] TOTO Match is a separate game with its own rules (effective 3 Jun 2025). Out of scope.
- [V, Sweep rules cl. 6.5 + SP public statement] Claim period: 180 days from the draw date (settled 18 Oct 2026, see `claim.py`). Not stated in the Toto or 4D rules text. Show as a hint only; Singapore Pools has extended it by announcement before.

## 4D

### Draw (2021 rules 6.1 to 6.2)
- [V] Big: 1 first, 1 second, 1 third, 10 starter, 10 consolation (23 numbers). Small: first, second, third only. Small has no starter or consolation.
- [V] When Singapore Pools adopts Sweep numbers: first, second and third come from the Sweep 1st, 2nd and 3rd. Starter comes from the Jackpot numbers, and consolation from the Lucky numbers.
- [?] The Singapore Sweep rules (effective 22 Apr 2026) have not been read.

### Prizes per $1 stake (identical in the 2021 and 2024 versions)

**Ordinary, 4D Roll and System entries**

| | Big | Small |
|---|---|---|
| First | $2,000 | $3,000 |
| Second | $1,000 | $2,000 |
| Third | $490 | $800 |
| Starter | $250 | n/a |
| Consolation | $60 | n/a |

**iBet entries** (amount depends on the digit pattern of the winning number)

| Big | 4 different digits | 2 same | 2 pairs | 3 same |
|---|---|---|---|---|
| First | $83 | $166 | $335 | $500 |
| Second | $41 | $83 | $168 | $250 |
| Third | $20 | $40 | $85 | $127 |
| Starter | $10 | $20 | $41 | $62 |
| Consolation | $3 | $6 | $10 | $15 |

| Small | 4 different digits | 2 same | 2 pairs | 3 same |
|---|---|---|---|---|
| First | $125 | $250 | $500 | $750 |
| Second | $83 | $167 | $333 | $500 |
| Third | $33 | $66 | $133 | $200 |

- The iBet values are close to the ordinary prize divided by the permutation count, but not exactly (for example Big 2 pairs). Use the published table and never compute it.
- [V, SP page] iBet prize money is divided proportionately by the number of permutations (4D microsite). This is why the iBet table is roughly the ordinary prize over the permutation count.

### Entry types
- [V] Ordinary: one 4-digit number, exact order (0000 to 9999).
- [V] 4D Roll: 3 chosen digits plus a wildcard position (RXYZ, XRYZ, XYRZ or XYZR, R = 0 to 9), which covers 10 numbers. Example: 58X2 covers 5802 to 5892.
- [V, SP page] 4D Roll can only be bought for the one current draw, not multi-draw.
- [V] System and iBet: all permutations of a number, excluding the ten single-permutation numbers (0000, 1111, ..., 9999). Wins regardless of order.
- [D] Permutation counts: 24 (all digits different), 12 (one pair), 6 (two pairs), 4 (three the same). Standard permutation math, not stated in the rules. The 2021 rules give only the 1234 = 24 example.

### Stakes (confirmed 17 Oct 2026; iBet confirmed from the specimen ticket 21 Oct 2026)
- [V] Minimum stake $1, in $1 multiples, GST included (2024 rule 3.1). Singapore Pools may set other limits on its website or app (rule 3.6).
- [V, SP page] Ordinary: bet cost is the Big and/or Small amounts marked.
- [V, SP page + specimen] 4D Roll: bet cost is the amounts marked x 10. Specimen: R888 Big $10 Small $10, PRICE $200.00.
- [V, SP page + specimen] System: bet cost is the amounts marked x the number of permutations. Specimen: 1234 Big $10 Small $10, 24 permutations, PRICE $480.00.
- [V, SP page + specimen] iBet: bet cost is the amounts marked, once, covering all permutations. Specimen: 1234 Big $10 Small $10, 24 permutations, PRICE $20.00. This settles the old conflict with the 4D microsite's "each permutation costs a minimum of $1" wording; the specimen is dated 2014 but agrees with the current bet slip page.
- [V, 2021] Multi-day: stake scales by the number of draw days (example: 1234 System, $2, Sat and Sun = 24 x $2 x 2 = $96).

### 4D printed ticket layout (official specimens, read 21 Oct 2026)
- [V, SP specimen] Top: "4D". Next line: bet type header, one of ORDINARY, SYSTEM, IBET.
- [V, SP specimen] A 4D Roll prints under ORDINARY. Only the "R" in the number (e.g. R888) marks it as a Roll, so the parser must detect Roll from the number, not the header.
- [V, SP specimen] Boards are lettered A, B, C... A ticket can carry up to 10 boards (A to J), all of one bet type. Each board line: letter, 4-digit number, "BIG $n", "SML $n".
- [V, SP specimen] System and iBet boards add a line "<n> PERMUTATIONS".
- [V, SP specimen] "QP" after a board marks a Quick Pick.
- [V, SP page + specimen] "S'OUT" in place of an amount: that side was sold out and not accepted, so its stake is $0. If the only number on a ticket is sold out, no ticket is issued.
- [V, SP page + specimen] "*" after an amount (e.g. "BIG $2*"): accepted stake is lower than requested. The printed amount is what was accepted and is what pays.
- [V, SP specimen] "PRICE:$n.nn" on every ticket: total charged. Sold-out specimen: 10 boards, BIG S'OUT on one, BIG $2* on another, PRICE $182.00 = only accepted stakes. Use it to cross-check the parsed stake.
- [V, SP specimen] Draw line: "DRAW: SAT 26/04/14" (weekday, DD/MM/YY). A field on the right reads "0003/14", which Singapore Pools labels as part of "draw date and number".
- [?] The "0003/14" field looks like a draw number in NNNN/YY form, but 0003 cannot be a real April 2014 draw number, so the specimen value is probably a placeholder. Confirm on a real ticket before coding the parser against it.
- [V, SP specimen] Other printed lines: purchase timestamp (e.g. "23/04/14 02:18pm"), a serial of the form "209-38781441-093108", and two further codes ("00888802-01", "02-1349"), then a barcode. Their meaning is not stated; do not parse them for matching.

### Multiple wins
- [V] A winner receives all applicable prizes if the number wins more than one (2024 rule 4.6).
- [D] For System and Roll entries each covered number is its own stake, so every covered number that wins is paid separately, and a number drawn in two prize positions is paid for both (rule 4.6).
- [?] iBet with two different winning permutations in the same draw (for example 1234 first and 4321 starter): the rules do not say it directly. Following rule 4.6 and the per-permutation split, pay each matching prize from the iBet table. Confirm before launch.

### Multi-draw
- [V] Bets can be placed up to 15 days before a draw (2024 rule 3.3).
- [V, SP page] Bet slips offer Wed, Sat, Sun or "6 DRAWS" (six consecutive draws including the current one). Not for 4D Roll.
- [V, 2021] Consecutive-draw entry is allowed if permitted by the Company, and the rules apply to each draw.

### Claim period
- [V, Sweep rules cl. 6.5 + SP public statement] 180 days from the draw date, as for Toto (see above).

## Test plan hooks (for the matcher and parser)
1. Toto Ordinary: one case per group G1 to G7 and a no-win case, including the Additional-Number edge (the Additional Number must not count toward the match count).
2. Toto System: the full official cl. 5.16 table as the golden set (in `verify_cl516.py`), including System Roll and the Ordinary column.
3. 4D: Big and Small hits in each category, the same number winning twice, Roll wildcard expansion with stake x 10, and System permutation counts and stakes for each digit pattern.
4. 4D iBet: all four digit patterns, taking amounts from the table, stake charged once.
5. Multi-draw: one ticket against several draws, including a mixed win and loss result.
6. 4D ticket parser: the five specimens as golden cases (header, Roll detected from "R", 10 boards, QP, S'OUT = $0, "*" amount, PRICE equals the computed stake).

## Open verification list
1. ~~Diff the 2026 Toto cl. 5.16 System table.~~ Closed 17 Oct 2026: full match.
2. ~~Confirm the iBet "Total bet amount" on a real iBet ticket.~~ Closed 21 Oct 2026 from the official specimen: charged once. Real 4D photos are still wanted for OCR training only.
3. Find the source for Hong Bao and special Toto draws.
4. Read the Singapore Sweep rules (22 Apr 2026) if 4D adopts Sweep numbers.
5. ~~Find the claim period.~~ Closed 18 Oct 2026: 180 days from the draw date.
6. Group TOTO and iTOTO are in the 2026 rules (cl. 2.6). Decide whether v1 supports them.
7. Confirm iBet payout when two different permutations win in the same draw.
8. Draw-number field: confirmed NNNN/YY on real Toto tickets (21 Oct 2026), one line per draw. Still confirm on a real 4D ticket.
9. Collect real Toto System 7 to 11 and System Roll tickets (no specimen exists online).
