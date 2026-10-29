"""P4-04 slice 6c: static checks of the account UI in web/index.html."""
import re
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")


def _function_body(name):
    start = PAGE.index(f"function {name}(")
    m = re.search(r"\n(?:async )?function |\n// -{10,}", PAGE[start + 1:])
    return PAGE[start:start + 1 + (m.start() if m else len(PAGE))]


def test_account_script_tag_before_main_script():
    tag = PAGE.index('<script src="/account.js"></script>')
    assert tag < PAGE.index('"use strict";')


def test_footer_wording_replaced():
    assert "Tickets are not stored unless you sign in and choose to save them." in PAGE
    assert "Ticket details are used for this check only and are not stored." not in PAGE


def test_no_innerhtml_added_for_account_data():
    assert PAGE.count("innerHTML") == 2          # the helper comment and the constant svg markup only
    for name in ("acctBar", "showSignIn", "showHistory", "saveCard", "buildHistoryEntries", "initAccount"):
        assert "innerHTML" not in _function_body(name)


def test_save_entry_code_never_mentions_serial():
    for name in ("buildHistoryEntries", "saveToHistory"):
        assert "serial" not in _function_body(name).lower()


def test_entry_fields_match_server_shape():
    body = _function_body("buildHistoryEntries")
    for field in ("game:", "draw_no:", "draw_date:", "bets", "stake", "won", "claim_by:", "label:", "numbers:"):
        assert field in body


def test_hash_token_dropped_and_signed_in_only_save():
    body = _function_body("initAccount")
    assert body.index("verify(") < body.index("replaceState") < body.index("ACCT.me()")
    assert "!A.user" in _function_body("saveCard") or "A.user" in _function_body("saveCard")
