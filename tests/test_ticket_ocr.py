"""P3-02: ticket photo -> TicketDraft.

T01 and T02 are the row output (OcrResult.lines()) of a real Google Vision run
on two real TOTO Ordinary QP tickets, 22 Oct 2026. Serial and barcode numbers
are replaced with dummies; everything else is exactly what Vision returned,
watermark noise included.
"""
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
