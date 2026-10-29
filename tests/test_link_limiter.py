from lottery_checker.limits import LinkLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_per_email_hourly_cap_then_recovers():
    c = Clock()
    lim = LinkLimiter(per_email=3, per_ip=100, per_day=100, clock=c)
    assert all(lim.allow("a@x.com", f"ip{i}") for i in range(3))
    assert lim.allow("a@x.com", "ip9") is False
    assert lim.allow("b@x.com", "ip9") is True
    c.t += 3601
    assert lim.allow("a@x.com", "ip9") is True


def test_per_connection_hourly_cap():
    lim = LinkLimiter(per_email=100, per_ip=2, per_day=100, clock=Clock())
    assert lim.allow("a@x.com", "ip1") and lim.allow("b@x.com", "ip1")
    assert lim.allow("c@x.com", "ip1") is False
    assert lim.allow("c@x.com", "ip2") is True


def test_site_wide_daily_cap():
    c = Clock()
    lim = LinkLimiter(per_email=100, per_ip=100, per_day=2, clock=c)
    assert lim.allow("a@x.com", "i1") and lim.allow("b@x.com", "i2")
    assert lim.allow("c@x.com", "i3") is False
    c.t += 86401
    assert lim.allow("c@x.com", "i3") is True


def test_refused_calls_do_not_burn_other_buckets():
    lim = LinkLimiter(per_email=1, per_ip=2, per_day=100, clock=Clock())
    assert lim.allow("a@x.com", "ip1")
    assert lim.allow("a@x.com", "ip1") is False      # email cap, must not use ip1's budget
    assert lim.allow("b@x.com", "ip1") is True


def test_email_is_case_insensitive():
    lim = LinkLimiter(per_email=1, per_ip=100, per_day=100, clock=Clock())
    assert lim.allow("A@x.com", "i1")
    assert lim.allow("a@X.com", "i2") is False


def test_defaults_read_the_environment(monkeypatch):
    monkeypatch.setenv("TOTO_LINK_PER_EMAIL", "1")
    lim = LinkLimiter(clock=Clock())
    assert lim.allow("a@x.com", "i1")
    assert lim.allow("a@x.com", "i2") is False
