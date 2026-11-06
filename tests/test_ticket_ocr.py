"""P3-02: ticket photo -> TicketDraft.

T01 and T02 are the row output (OcrResult.lines()) of a real Google Vision run
on two real TOTO Ordinary QP tickets, 22 Oct 2026. Serial and barcode numbers
are replaced with dummies; everything else is exactly what Vision returned,
watermark noise included.
"""
from pathlib import Path

import pytest

from lottery_checker import ocr
from lottery_checker.ticket_ocr import clean_row, is_watermark, read_ocr, read_rows, rows_from_text

T01 = """Mane in CTIA
FJELLSE
P POOLS POOLS
OOLS SINGAPORE
SINGAPORE
SINGAPO TOTO
SINGAPORE So F
F No more cheques from 1 Nov 2026 POOL
Link NRIC to PayNow for payouts
POOLS POO ORDINARY
SINGAP
A. 12 13 14 SINGAPORE
16 26 39 QP
B.04 SINGAPORE
24 28 33 38 39 QP
PO
PRICE : $ 4.00 POOLS
DRAW : LS SIN
THU 10/09/26 4216/26 ORE SINGAPORE
MON 14/09/26 4217/26
09/09/26 01:42 PM 100000001
000000-0-0000000-000 20000002
000-0000000-0000000 POOLS
POOLS
POOLS
S SINGAPORE
SINGAPORE
SINGAPORE
ORE
PUBLS
POOLS
BOOLS""".splitlines()

T02 = """APOT P POOLS
POOLS
POOLS SINGAPORE
OOLS TOTO SINGAPORE F
SINGAPORE No more SINGAPORE cheques from 1 Nov 2026
Link NRIC to PayNow for payouts POOL
ORDINARY COOLS
10 13 26 28 36 42 SGAPO
B. 03 SINGAPORE QP
SINGAPORE 11 17 35 45 46
PRICE : $ 4.00 PO
DRAW : POOLS
THU 24/09/26 4220/26 SIN
MON 28/09/26 4221/26 SINGAPORE
23/09/26 01:51 PM PORE 100000002
000000-0-0000000-000 20000003
$ 000-0000000-0000000
F P POOLS POOLS
POOLS SINGAPORE
RE
OLS
JELLSE""".splitlines()


def boards(read):
    return [tuple(e.numbers) for e in read.draft.entries]


# ---------------------------------------------------------------- real tickets

def test_real_ticket_1_reads_exactly():
    r = read_rows(T01)
    d = r.draft
    assert d.ready and not d.errors and not d.warnings
    assert d.game == "toto" and all(e.kind == "ordinary" for e in d.entries)
    assert boards(r) == [(12, 13, 14, 16, 26, 39), (4, 24, 28, 33, 38, 39)]
    assert d.draw_numbers == [4216, 4217]
    assert [str(w) for _, w in d.draws] == ["2026-09-10", "2026-09-14"]
    assert d.printed_price == 4.0 and d.stake() == 4 and d.quick_pick
    assert r.notes == []


def test_real_ticket_2_board_split_and_letter_missing():
    r = read_rows(T02)
    d = r.draft
    assert d.ready and not d.errors and not d.warnings
    assert boards(r) == [(10, 13, 26, 28, 36, 42), (3, 11, 17, 35, 45, 46)]
    assert d.draw_numbers == [4220, 4221] and d.printed_price == 4.0
    assert "A. 10 13 26 28 36 42" in r.text            # letter filled in
    assert any("letter was missing" in n for n in r.notes)


def test_photo_text_is_the_typed_format():
    """The confirm screen edits this text, so it must be what a person would type."""
    assert read_rows(T01).text == (
        "TOTO\nORDINARY\nA. 12 13 14 16 26 39 QP\nB. 04 24 28 33 38 39 QP\n"
        "DRAW:\nTHU 10/09/26 4216/26\nMON 14/09/26 4217/26\nPRICE: $4.00")


def test_serials_and_purchase_time_are_never_board_numbers():
    r = read_rows(T01)
    assert "1000" not in r.text and "01:42" not in r.text and "0000" not in r.text


def test_reading_order_text_file_uses_the_geometry_rows():
    saved = "TOTO\n12 13 14 16 26 39\n\n# lines\n" + "\n".join(T01) + "\n"
    assert boards(read_rows(rows_from_text(saved)))[0] == (12, 13, 14, 16, 26, 39)


# ---------------------------------------------------------------- watermark

def test_watermark_fragments_dropped():
    for t in ["SINGAPORE", "POOLS", "SINGAPO", "SINGAP", "OOLS", "POO", "POOL", "COOLS", "BOOLS",
              "PUBLS", "SGAPO", "PORE", "ORE", "SIN", "PO", "RE", "OLS", "F", "P", "S"]:
        assert is_watermark(t), t


def test_ticket_words_kept():
    for t in ["TOTO", "ORDINARY", "SYSTEM", "QP", "PRICE", "DRAW", "THU", "MON", "BIG", "SML",
              "A.", "B.04", "4D", "S'OUT", "12", "$4.00", "4216/26", "10/09/26"]:
        assert not is_watermark(t), t


def test_clean_row():
    assert clean_row("B. 03 SINGAPORE QP") == "B. 03 QP"
    assert clean_row("POOLS SINGAPORE") == ""


# ---------------------------------------------------------------- layouts not yet seen on a real photo

def test_system_7_wrapping_rows():
    rows = ["TOTO", "SYSTEM 7", "A. 01 02 03 04", "05 06 07", "DRAW:", "THU 22/10/26 4228/26",
            "PRICE: $7.00"]
    d = read_rows(rows).draft
    assert d.ready and d.entries[0].kind == "system" and len(d.entries[0].numbers) == 7
    assert d.stake() == 7


def test_system_roll_header():
    rows = ["TOTO", "SYSTEM ROLL", "A. 01 02 03 04 05", "DRAW:", "THU 22/10/26 4228/26"]
    d = read_rows(rows).draft
    assert d.ready and d.entries[0].kind == "roll"


def test_missing_header_assumes_ordinary_and_says_so():
    r = read_rows(["TOTO", "A. 01 02 03 04 05 06", "DRAW:", "THU 22/10/26 4228/26"])
    assert r.draft.ready and any("assumed ORDINARY" in n for n in r.notes)


def test_too_few_numbers_reaches_the_confirm_screen_as_an_error():
    r = read_rows(["TOTO", "ORDINARY", "A. 01 02 03 04 05", "DRAW:", "THU 22/10/26 4228/26"])
    assert not r.draft.ready and r.draft.errors


def test_unreadable_dates_fall_back_to_draw_numbers():
    r = read_rows(["TOTO", "ORDINARY", "A. 01 02 03 04 05 06", "DRAW:", "THU 22/1?/26 4228/26"])
    assert r.draft.draw_numbers == [4228] and any("dates" in n for n in r.notes)


def test_4d_passes_through_with_a_caution():
    r = read_rows(["4D", "ORDINARY", "A 1234 BIG $1 SML $1", "SINGAPORE", "DRAW: WED 21/10/26 5551/26"])
    assert r.draft.game == "4d" and r.draft.ready and any("4D" in n for n in r.notes)


# ---------------------------------------------------------------- hardening (P3-02-H)

_DRAW_ROWS = ["DRAW:", "THU 22/10/26 4228/26"]


def test_impossible_system_size_takes_the_type_from_the_count():
    # "SYSTEM 11" with a digit lost: must not split 11 numbers into 11 boards
    r = read_rows(["TOTO", "SYSTEM 1", "A. 01 02 03 04 05 06 07 08 09 10 11"] + _DRAW_ROWS)
    assert r.draft.ready and [(e.kind, len(e.numbers)) for e in r.draft.entries] == [("system", 11)]
    assert any("SYSTEM 1" in n for n in r.notes)
    assert "\nSYSTEM 1\n" not in r.text


def test_system_size_outside_7_to_12_is_not_trusted():
    for head in ("SYSTEM 0", "SYSTEM 3", "SYSTEM 13"):
        r = read_rows(["TOTO", head, "A. 01 02 03 04 05 06 07"] + _DRAW_ROWS)
        assert r.draft.ready and [(e.kind, len(e.numbers)) for e in r.draft.entries] == [("system", 7)], head
        assert any(head in n for n in r.notes), head


def test_valid_system_sizes_still_split_boards():
    r = read_rows(["TOTO", "SYSTEM 12", "A. 01 02 03 04 05 06 07 08 09 10 11 12"] + _DRAW_ROWS)
    assert r.draft.ready and [len(e.numbers) for e in r.draft.entries] == [12] and not r.notes


def test_more_than_ten_boards_does_not_crash():
    rows = ["TOTO", "ORDINARY"] + [" ".join(f"{n:02d}" for n in range(1, 7))] * 11 + _DRAW_ROWS
    r = read_rows(rows)
    assert len(r.draft.entries) + len(r.draft.errors) >= 11
    assert any("More than 10 boards" in n for n in r.notes)


def test_4d_footer_rows_are_dropped():
    r = read_rows(["4D", "ORDINARY", "A 1234 BIG $1 SML $1", "DRAW: WED 21/10/26 5551/26", "PRICE: $2.00",
                   "20/10/26 01:42 PM 100000001", "000000-0-0000000-000 20000002", "000-0000000-0000000",
                   "8812 BIG"])
    assert r.draft.ready and not r.draft.errors and len(r.draft.entries) == 1
    assert "PM" not in r.text and "8812" not in r.text and "PRICE: $2.00" in r.text


def test_4d_footer_found_by_serial_when_the_time_is_unreadable():
    r = read_rows(["4D", "ORDINARY", "A 1234 BIG $1 SML $1", "DRAW: WED 21/10/26 5551/26",
                   "0 123456-0-000 $", "5551 0042 7781 2093"])
    assert r.draft.ready and not r.draft.errors and "5551 0042" not in r.text


# ---------------------------------------------------------------- from an OcrResult

def _result(rows, conf=0.95):
    words = [ocr.Word(tok, (10 * j, 30 * i, 10 * j + 8, 30 * i + 20), conf)
             for i, row in enumerate(rows) for j, tok in enumerate(row.split())]
    return ocr.OcrResult("\n".join(rows), words)


def test_read_ocr_uses_word_rows():
    assert boards(read_ocr(_result(T01)))[1] == (4, 24, 28, 33, 38, 39)


def test_read_ocr_blank_photo():
    r = read_ocr(ocr.OcrResult(""))
    assert not r.draft.ready and "Retake" in r.notes[0]


def test_read_ocr_low_confidence_warns():
    assert any("hard to read" in n for n in read_ocr(_result(T01, conf=0.5)).notes)


# ---------------------------------------------------------------- O-for-0 misreads (live test, 22 Oct)

def test_zero_read_as_letter_o_is_put_back():
    """A live test photo came back with 02 as O2, 05 as O5, 10 as 1O and a blurred
    ORDINARY, which lost a number from each board and the draw date."""
    rows = ["TOTO", "ORDlNARY", "A. O2 15 19 20 27 05 QP", "B. 02 15 19 40 41 O5 QP",
            "PRICE: $2.00", "DRAW:", "MON 19/1O/26 4227/26"]
    r = read_rows(rows)
    assert r.draft.ready and r.notes == []
    assert boards(r) == [(2, 5, 15, 19, 20, 27), (2, 5, 15, 19, 40, 41)]   # boards are kept sorted
    assert [str(w) for _, w in r.draft.draws] == ["2026-10-19"]


def test_letter_stuck_to_misread_number():
    assert boards(read_rows(["TOTO", "ORDINARY", "A.O2 15 19 20 27 30", "DRAW:", "MON 19/10/26 4227/26"]))[0][0] == 2


def test_lookalike_fix_leaves_words_alone():
    from lottery_checker.ticket_ocr import fix_token
    for t in ["4D", "O", "PO", "QP", "POOLS", "SINGAPORE", "PRICE", "$2.00"]:
        assert fix_token(t) == t, t
    assert fix_token("0RDINARY") == "ORDINARY" and fix_token("SYSTEN") == "SYSTEM"


# ---------------------------------------------------------------- live test ticket, real Vision rows (22 Oct 11:11)
# A drawn test ticket uploaded to toto.zenqi.cc with a heavy SINGAPORE watermark.
# Vision lost two numbers under the watermark (fixed on the phone by cleaning the
# photo first); the rest must still come through.
LIVE = """GAPORE SINGA
SINGAPORE TOTO OPORE
NRIC to Pay Now for NGAPORE payouts SINGAPO
SINGAPO PORE SINGAPORE S
ORDING SINGAPORE
SING
A. 15 19 20 27 05 QP
SINGA B. 02 15 19 RE 40 41 SINGAPORE
RE SINGAPORE
PRICE APORE $ 2.00
DRAW : SINGAPORE SINGAPORE SINGAPORE
APORE MON 19 / 10 / 26E 4227/26
ORE SINGAPORE SINGAPORE SINGAPORE
/ 26 02:11
INGAPOR0 123456-0-000 $""".splitlines()


def test_live_rows_header_date_and_price_survive_the_watermark():
    r = read_rows(LIVE)
    assert "ORDINARY" in r.text and "MON 19/10/26 4227/26" in r.text and "PRICE: $2.00" in r.text
    assert [str(w) for _, w in r.draft.draws] == ["2026-10-19"]
    # the two numbers Vision never returned are reported per board, for the user to fix
    assert [e.message for e in r.draft.errors] == ["expected 6 numbers for this bet type, found 5"] * 2


def test_glued_watermark_letters_and_spaced_dates():
    from lottery_checker.ticket_ocr import clean_row, fix_token
    assert fix_token("26E") == "26" and fix_token("SING02") == "02" and fix_token("SINGAPOR05") == "05"
    assert fix_token("R888") == "R888" and fix_token("4D") == "4D" and fix_token("PO") == "PO"
    assert fix_token("ORDING") == "ORDINARY" and fix_token("SYSTE") == "SYSTEM"
    assert clean_row("APORE MON 19 / 10 / 26E 4227/26") == "MON 19/10/26 4227/26"


# ---------------------------------------------------------------- P3-02-R2: seven real photos, 5 Nov 2026
# Row output of Google Vision on real tickets (a02 = 07, a03 = 08, a04 = 09, a05 = 10, a06 = 11 in tests/fixtures/tickets; a01 = 06). Serial, terminal and
# barcode numbers are dummies; everything else is exactly what Vision returned.

A02 = """SINGAPO TOTO
F No more cheques from 1 Nov 2026 POOL
Link NRIC to PayNow for payouts
POO ORDINARY SINGAP
A. 12 13 14 16 26 39 QP
B. 3.04 INGAPORE 24 28 33 38 39 QP PO
PRICE : $ 4.00 SIN
DRAW : LS APORE
THU 10/09/26 4216/26 RẺ
MON 14/09/26 4217726
09/09/26 01:42 PM 100000000
111111-1-1111111-111 11111111
111-1111111-1111111 POOLS""".splitlines()

A03 = """4D COLS
POOLS 2026INGAPORE
OLS No more cheques from 1 Nov
Link SINGAPORE NRIC Cato PayNow for payouts S
GAPORE ORDINARY
R310 BIG $ 1 SML $ 0 POOLS
PRICE : $ 10.00
DRAW : SAT 31/10/26 5555/26
SINGAP 24/10/26 06:49 PM F 000000000
111111-1-1111111-111 11111111
111-1111111-1111111 POO""".splitlines()

A04 = """ORE F STO
TOTOLS
more OL cheques from 1 Nov 2026INGAPORE
OLS No
Link NRIC to Pay Now for payouts F
SINGAPORE SYSTEM 7
GAPORE
A. 08 11 18 21 31 41 POOLS
POOL
46 POOLS SINGAPOR
PRICE : $ 14.00 SINGAPORE
DRAW : SINGAPORE FF
SINGMON 26/10/26 4229/26
THU 29/10/26 4230126 0000000000 POO
24/10/26 06:49 PM PO
111111-1-1111111-111 11111111
111-1111111-1111111 SINGA""".splitlines()

A05 = """4D S
No more cheques from 1 Nov 2026
Link NRIC to PayNow for payouts
ORDINARY
A - 0310 S BIG $ 1 SML $ 0
OLS B. 1310 BIG $ 1 SINGAPORE SML $ 0 SINGAPORE
GAPORE C. 2310 APORE BIG S'OUT SML $ 0 F
3310 BIG $ 1 SML $ 0 POOLS
4310 BIG $ 1 POSML $ 0
0 SINGAPOR
00 5310 BIG $ 1 SIN SML $ 0
SINGAP GR 6310 SINGAPORE BIG $ 1 SML $ 0 F
H. 7310 BIG $ 1 SML $ 0 POO
8310 PO BIG $ 1 SML $ 0 SINGA
P 0 9 . 9310 BIG $ 1 SMLCSOORE
SINPRICE POBE : $ 9.00 S
DRAW : SUN 25/10/26 5553/26 PO
24/10/26 06:49 PM P 000000000
111111-1-1111111-111 11111111
111-1111111-1111111 SINGAPORE""".splitlines()

A06 = """POOLS 503
SINGAPORE 4D
UL No more cheques from 1 Nov 2026
Link NRIC to PayNow for payouts
POOLS iBet
A - 6214 INGA BIG $ 1 SML $ 0 UL
24 PERMUTATIONS
5413 BIG $ 1 SML $ 0 POO
24 PERMUTATIONS
PO PRICE : $ 4.00 SINGAPORE
DRAW : SINGAPORE
WED 28/10/26 5554/26 EL
SAT 31/10/26 5555/26
24/10/26 06:49 PM 000000000
111111-1-1111111-111 11111111
111-1111111-1111111""".splitlines()


def test_slash_read_as_a_digit_in_a_draw_number_is_put_back():
    assert clean_row("MON 14/09/26 4217726") == "MON 14/09/26 4217/26"
    assert clean_row("THU 29/10/26 4230126 0000000000") == "THU 29/10/26 4230/26 0000000000"
    assert clean_row("THU 10/09/26 4216/26") == "THU 10/09/26 4216/26"
    assert clean_row("SINGMON 26/10/26 4229/26") == "MON 26/10/26 4229/26"
    assert clean_row("MON 14/09/26 4217/26") == "MON 14/09/26 4217/26"
    assert clean_row("SINGMON 26/10/26 4229/26") == "MON 26/10/26 4229/26"
    assert clean_row("MON 14/09/26 4217/26") == "MON 14/09/26 4217/26"
    assert clean_row("23/09/26 01:51 PM 177302004") == "23/09/26 01:51 PM 177302004"


def test_a02_second_board_and_second_draw_survive():
    d = read_rows(A02).draft
    assert d.ready and not d.errors
    assert [e.numbers for e in d.entries] == [(12, 13, 14, 16, 26, 39), (4, 24, 28, 33, 38, 39)]
    assert d.draw_numbers == [4216, 4217]


def test_a04_toto_title_lost_is_found_from_the_system_header():
    r = read_rows(A04)
    assert r.draft.game == "toto" and r.draft.ready and not r.draft.errors
    assert r.draft.entries[0].kind == "system"
    assert r.draft.entries[0].numbers == (8, 11, 18, 21, 31, 41, 46)
    assert r.draft.draw_numbers == [4229, 4230]
    assert not any("Couldn't tell" in n for n in r.notes)


def test_a03_4d_roll_header_noise_is_not_an_error():
    d = read_rows(A03).draft
    assert d.game == "4d" and d.ready and not d.errors
    assert [(e.kind, e.number, e.big, e.small) for e in d.entries] == [("roll", "R310", 1, 0)]
    assert d.draw_numbers == [5555] and d.printed_price == 10.0


def test_a06_4d_ibet_header_noise_is_not_an_error():
    d = read_rows(A06).draft
    assert d.game == "4d" and d.ready and not d.errors
    assert [(e.kind, e.number) for e in d.entries] == [("ibet", "6214"), ("ibet", "5413")]
    assert d.draw_numbers == [5554, 5555] and d.printed_price == 4.0


def test_a05_ten_line_4d_ticket_reads_every_live_bet():
    d = read_rows(A05).draft
    # 2310 is fully sold out (BIG S'OUT SML $0), so it is not a bet
    assert [e.number for e in d.entries] == ["0310", "1310", "3310", "4310", "5310", "6310",
                                             "7310", "8310", "9310"]
    assert d.draw_numbers == [5553] and d.printed_price == 9.0
    assert d.ready and not d.errors


def test_toto_without_a_title_or_system_header_still_says_it_could_not_tell():
    r = read_rows(["A. 01 02 03 04 05 06", "DRAW:", "THU 22/10/26 4228/26"])
    assert any("Couldn't tell" in n for n in r.notes)


# P3-02-S: System 8-11 from synthetic rows. No real System 8-11 ticket exists, so these are
# built on the real A04 (System 7) row shape: watermark glue, a wrapped tail row, a lost title.
# Dummy numbers and serials. Guards: the parser already reads these; they must stay green.
def _sys_rows(n, boards, price, header=None):
    rows = ["ORE F STO", "TOTOLS", "more OL cheques from 1 Nov 2026INGAPORE", "OLS No",
            "Link NRIC to Pay Now for payouts F", f"SINGAPORE {header or f'SYSTEM {n}'}", "GAPORE"]
    for letter, nums in boards:
        rows += [f"{letter}. " + " ".join(nums[:6]) + " POOLS", "POOL",
                 " ".join(nums[6:]) + " POOLS SINGAPOR"]
    rows += [f"PRICE : $ {price}.00 SINGAPORE", "DRAW : SINGAPORE FF",
             "THU 29/10/26 4230126 0000000000 POO", "24/10/26 06:49 PM PO",
             "111111-1-1111111-111 11111111"]
    return rows


_SYS_NUMS = {
    8: ("03 09 14 22 30 37 41 45".split(), 28),
    9: ("02 07 13 19 25 33 38 44 49".split(), 84),
    10: ("01 06 12 18 24 29 35 40 43 48".split(), 210),
    11: ("04 05 11 17 23 28 34 39 42 46 47".split(), 462),
}


@pytest.mark.parametrize("n", [8, 9, 10, 11])
def test_system_8_to_11_wrapped_board_reads_as_one_board(n):
    nums, price = _SYS_NUMS[n]
    r = read_rows(_sys_rows(n, [("A", nums)], price))
    d = r.draft
    assert d.game == "toto" and d.ready and not d.errors
    assert [(e.kind, e.numbers) for e in d.entries] == [("system", tuple(int(x) for x in nums))]
    assert d.draw_numbers == [4230] and d.printed_price == float(price)


def test_system_8_two_boards_each_keep_their_wrapped_tail():
    a, _ = _SYS_NUMS[8]
    b = "02 08 13 20 26 31 36 44".split()
    d = read_rows(_sys_rows(8, [("A", a), ("B", b)], 56)).draft
    assert d.ready and not d.errors
    assert [e.numbers for e in d.entries] == [tuple(int(x) for x in a), tuple(int(x) for x in b)]


def test_system_header_number_misread_takes_the_type_from_the_count():
    nums, price = _SYS_NUMS[9]
    r = read_rows(_sys_rows(9, [("A", nums)], price, header="SYSTEM 19"))
    assert r.draft.ready and not r.draft.errors
    assert [(e.kind, len(e.numbers)) for e in r.draft.entries] == [("system", 9)]
    assert any("doesn't exist" in n for n in r.notes)


def test_system_header_number_lost_fails_loudly_and_never_guesses():
    nums, price = _SYS_NUMS[9]
    d = read_rows(_sys_rows(9, [("A", nums)], price, header="SYSTEM")).draft
    assert not d.ready and d.errors


# P3-02-R: TOTO System Roll from synthetic rows. No real System Roll ticket exists, so these use
# the same row shape as the real System 7 photo (09), with a SYSTEM ROLL header, 5 numbers per
# board and a $44 price (5 chosen numbers x the other 44). Dummy numbers and serials. Guards.
_ROLL_A = "05 12 19 27 38".split()
_ROLL_B = "03 14 22 31 46".split()


def _roll_rows(boards, price, header="SYSTEM ROLL"):
    rows = ["ORE F STO", "TOTOLS", "more OL cheques from 1 Nov 2026INGAPORE", "OLS No",
            "Link NRIC to Pay Now for payouts F", f"SINGAPORE {header}", "GAPORE"]
    for letter, nums in boards:
        rows += [f"{letter}. " + " ".join(nums) + " POOLS", "POOL"]
    rows += [f"PRICE : $ {price}.00 SINGAPORE", "DRAW : SINGAPORE FF",
             "THU 29/10/26 4230126 0000000000 POO", "24/10/26 06:49 PM PO",
             "111111-1-1111111-111 11111111"]
    return rows


def test_system_roll_board_reads_as_one_five_number_board():
    d = read_rows(_roll_rows([("A", _ROLL_A)], 44)).draft
    assert d.game == "toto" and d.ready and not d.errors
    assert [len(e.numbers) for e in d.entries] == [5]
    assert d.entries[0].numbers == tuple(int(x) for x in _ROLL_A)
    assert "roll" in d.entries[0].kind.lower()
    assert d.draw_numbers == [4230] and d.printed_price == 44.0


def test_system_roll_two_boards_do_not_merge():
    d = read_rows(_roll_rows([("A", _ROLL_A), ("B", _ROLL_B)], 88)).draft
    assert d.ready and not d.errors
    assert [e.numbers for e in d.entries] == [tuple(int(x) for x in _ROLL_A),
                                              tuple(int(x) for x in _ROLL_B)]


def test_system_roll_header_glued_or_spaced_reads_the_same():
    for header in ("SYSTEMROLL", "SYSTEM  ROLL"):
        d = read_rows(_roll_rows([("A", _ROLL_A)], 44, header=header)).draft
        assert d.ready and not d.errors and len(d.entries[0].numbers) == 5


# P3-02-L: 4D board-letter and stray-digit Vision variants seen live on photos 10 and 11
# (2026-11-06). The ticket text below is what the page's text box held after read_rows.
from lottery_checker.ticket_entry import parse_ticket as _parse_ticket

_L10 = """4D
ORDINARY
- 0310 BIG $ 1 SML $ 0
B. 1310 BIG $ 1 SML $ 0
- 2310 BIG S'OUT SML $ 0
D. 3310 BIG $ 1 SML $ 0
E. 4310 BIG $ 1 SML $ 0
4 - 5310 BIG $ 1 SML $ 0
G.6310 BIG $ 1 SML $ 0
H. 1.7310 BIG $ 1 SML $ 0
I. 8310 BIG $ 1 SML $ 0
J. 9310 BIG $ 1 SML $ 0
PRICE: $9.00
DRAW : SUN 25/10/26 5553/26"""

_L11 = """4D
iBet
- 6214 BIG $ 1 SML $ 0
24 PERMUTATIONS
B.5413 BIG $ 1 SML $ 0
24 PERMUTATIONS
PRICE: $4.00
DRAW :
WED 28/10/26 5554/26
SAT 31/10/26 5555/26"""


def test_l10_letter_glued_to_number_and_stray_digit_read_every_live_bet():
    d = _parse_ticket(_L10)
    assert not d.errors
    assert [e.number for e in d.entries] == ["0310", "1310", "3310", "4310", "5310", "6310",
                                             "7310", "8310", "9310"]
    assert d.draw_numbers == [5553] and d.printed_price == 9.0


def test_l11_ibet_letter_glued_to_number_reads_both_boards():
    d = _parse_ticket(_L11)
    assert not d.errors
    assert [(e.kind, e.number) for e in d.entries] == [("ibet", "6214"), ("ibet", "5413")]
    assert d.draw_numbers == [5554, 5555] and d.printed_price == 4.0


def test_l_draw_word_is_not_read_as_a_board_letter():
    # "DRAW" must stay a header: a letter glued to R must not become board D + roll number.
    d = _parse_ticket("4D\nORDINARY\nA. 0310 BIG $ 1 SML $ 0\nDRAW : SUN 25/10/26 5553/26\nPRICE: $1.00")
    assert not d.errors and [e.number for e in d.entries] == ["0310"]


def test_l_board_letter_needs_a_dot_or_a_space():
    from lottery_checker.ticket_entry import _BOARD_LETTER as B
    assert not B.match("DRAW : SUN 25/10/26") and not B.match("A0310 BIG $ 1")
    assert B.match("G.6310 BIG") and B.match("B)5413") and B.match("A. 0310") and B.match("C R310")


# P3-02-W: rows as Vision returns them for the image the PAGE sends (shrunk to 2000 px and
# watermark-filtered by web/index.html), photo 07. Raw-file rows (A02 above) read fine; the
# page's image puts the printed word DRAW between the day name and the date.
_W07 = ["PO ORDINARY", "A. 12 13 14 16 26 39 QP", "B. 04 24 28 33 38 39 QP", "PRICE : $ 4.00",
        'THU DRAW : 10/09/26 4216126 - $ 10 67 PORE "', "RE", "MON 14/09/26 4217/26",
        "09/09/26 01:42 PM 177302006", "TOTO"]


def test_w07_draw_word_between_day_and_date_is_dropped():
    assert clean_row('THU DRAW : 10/09/26 4216126 - $ 10 67 PORE "').startswith("THU 10/09/26 4216/26")
    assert clean_row("THU DRAW 10/09/26 4216/26") == "THU 10/09/26 4216/26"
    assert clean_row("DRAW : THU 10/09/26 4216/26") == "DRAW : THU 10/09/26 4216/26"


def test_w07_page_image_rows_keep_both_draws():
    r = read_rows(_W07)
    assert r.draft.draw_numbers == [4216, 4217] and r.draft.printed_price == 4.0
    assert r.draft.ready and not r.draft.errors and not r.draft.warnings


# P3-02-P: Vision rows for the image the PAGE sends (web/index.html shrink + cleanTicket), one
# fixture per real photo, saved 2026-11-06 (serial rows dropped; they sit after the footer).
# Raw-file rows (above) missed two live bugs because the page's image reads differently.
_PAGE_DIR = Path(__file__).parent / "fixtures" / "ocr"
_T = lambda *n: tuple(n)                                   # noqa: E731
_PAGE_CASES = {
    "01": ("toto", [4227], 2.0, [_T(2, 5, 15, 19, 20, 27), _T(2, 5, 15, 19, 40, 41)]),
    "02": ("toto", [4227], 7.0, [_T(2, 15, 19, 20, 27, 30, 41)]),
    "03": ("toto", [4227, 4228], 4.0, [_T(3, 8, 11, 19, 27, 30), _T(5, 12, 22, 31, 38, 44)]),
    "04": ("toto", [4224, 4225, 4226, 4227], 4.0, [_T(2, 15, 19, 20, 33, 45)]),
    "05": ("4d", [5551], 5.0, [("ordinary", "8455"), ("ordinary", "9363"), ("ordinary", "1234")]),
    "06": ("toto", [4220, 4221], 4.0, [_T(10, 13, 26, 28, 36, 42), _T(3, 11, 17, 35, 45, 46)]),
    "07": ("toto", [4216, 4217], 4.0, [_T(12, 13, 14, 16, 26, 39), _T(4, 24, 28, 33, 38, 39)]),
    "08": ("4d", [5555], 10.0, [("roll", "R310")]),
    "09": ("toto", [4229, 4230], 14.0, [_T(8, 11, 18, 21, 31, 41, 46)]),
    "10": ("4d", [5553], 9.0, [("ordinary", n) for n in
                               ("0310", "1310", "3310", "4310", "5310", "6310", "7310", "8310", "9310")]),
    "11": ("4d", [5554, 5555], 4.0, [("ibet", "6214"), ("ibet", "5413")]),
}


@pytest.mark.parametrize("key", sorted(_PAGE_CASES))
def test_p_page_processed_photo_rows_read_the_whole_ticket(key):
    game, draws, price, bets = _PAGE_CASES[key]
    rows = (_PAGE_DIR / f"{key}_page.rows.txt").read_text(encoding="utf-8").splitlines()
    d = read_rows(rows).draft
    assert d.game == game and d.ready and not d.errors
    assert d.draw_numbers == draws and d.printed_price == price
    got = [e.numbers if game == "toto" else (e.kind, e.number) for e in d.entries]
    assert got == bets
