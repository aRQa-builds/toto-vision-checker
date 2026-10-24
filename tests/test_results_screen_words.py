"""The desktop 4D results page is a two-column table that Vision reads column by column
(23 Oct 2026: 1st/2nd/3rd all read as the first Starter, 5 of 10 Starters and
Consolations). Reading by word position fixes it."""
from lottery_checker.ocr import Word
from lottery_checker.results_screen import read_screen

STARTER = ["0273", "0436", "2089", "2837", "5006", "6491", "7394", "8072", "8468", "9574"]
CONSOL = ["0030", "0854", "2005", "4062", "4623", "4890", "6736", "6804", "8934", "9363"]


def _w(text, x, y, wd=60):
    return Word(text, (x, y - 10, x + wd, y + 10))


def desktop_page():
    """Words laid out like the official desktop page, plus Vision's column-order text."""
    ws = [_w("Next", 160, 450), _w("Draw", 210, 450), _w("Sat,", 270, 450), _w("24", 320, 450),
          _w("Oct", 350, 450), _w("2026", 390, 450),
          _w("Wed,", 240, 543), _w("21", 300, 543), _w("Oct", 330, 543), _w("2026", 370, 543),
          _w("Draw", 800, 543), _w("No.", 860, 543), _w("5551", 900, 543)]
    for y, label, num in ((590, "1st", "8455"), (635, "2nd", "1103"), (680, "3rd", "3344")):
        ws += [_w(label, 275, y), _w("Prize", 320, y), _w(num, 840, y)]
    ws += [_w("Starter", 530, 750), _w("Prizes", 590, 750)]
    for i in range(5):
        ws += [_w(STARTER[2 * i], 290, 795 + 45 * i), _w(STARTER[2 * i + 1], 840, 795 + 45 * i)]
    ws += [_w("Consolation", 510, 1043), _w("Prizes", 600, 1043)]
    for i in range(5):
        ws += [_w(CONSOL[2 * i], 290, 1090 + 45 * i), _w(CONSOL[2 * i + 1], 840, 1090 + 45 * i)]
    ws += [_w("Prizes", 35, 1353), _w("not", 90, 1353), _w("by", 200, 1353), _w("Mon,", 240, 1353),
           _w("19", 300, 1353), _w("Apr", 330, 1353), _w("2027", 370, 1353)]
    text = ("Next Draw Sat, 24 Oct 2026, 6.30pm Draw Date Wed, 21 Oct 2026 Wed, 21 Oct 2026 Draw No. 5551 "
            "1st Prize 2nd Prize 3rd Prize 8455 1103 3344 Starter Prizes "
            + " ".join(STARTER[0::2]) + " " + " ".join(STARTER[1::2]) + " Consolation Prizes "
            + " ".join(CONSOL[0::2]) + " " + " ".join(CONSOL[1::2])
            + " Prizes not claimed by Mon, 19 Apr 2027 will be channelled 4D Calculate Prize")
    return text, ws


def test_desktop_page_reads_by_position():
    text, ws = desktop_page()
    r = read_screen(text, ws)
    assert (r.first, r.second, r.third) == ("8455", "1103", "3344")
    assert r.starter == STARTER and r.consolation == CONSOL
    assert r.draw_no == 5551 and r.complete


def test_row_order_not_column_order():
    text, ws = desktop_page()
    assert read_screen(text, ws).starter[:3] == ["0273", "0436", "2089"]


def test_without_words_text_path_unchanged():
    text, _ = desktop_page()
    r = read_screen(text)                                # old behaviour, no positions
    assert r.game == "4d" and r.draw_no == 5551


def test_two_people_reading_the_desktop_page_make_a_shared_4d_result(tmp_path):
    """4D had no crowd database: no screenshot ever read complete. Now two do."""
    from datetime import date
    from lottery_checker import shared
    text, ws = desktop_page()
    read = read_screen(text, ws)
    today = date(2026, 10, 23)
    assert shared.submit(read, "alice", tmp_path, today=today, device="Windows · Brave")
    assert shared.status("4d", 5551, tmp_path) == "waiting"
    assert shared.load_shared_ref("4d", 5551, tmp_path) is None
    assert shared.submit(read, "bob", tmp_path, today=today, device="Android · Chrome")
    assert shared.status("4d", 5551, tmp_path) == "agreed"
    ref = shared.load_shared_ref("4d", 5551, tmp_path)
    assert ref.draw.first == "8455" and ref.draw.consolation[-1] == "9363"
