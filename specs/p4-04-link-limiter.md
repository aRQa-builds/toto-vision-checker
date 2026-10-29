# P4-04 slice 3: sign-in mail limiter

## 0 - Output format contract
Reply with the complete file `lottery_checker/limits.py`, line 1 to the last line, in one fenced python block. Never `# ... existing code ...`, a placeholder or a partial hunk; every omitted line is deleted from disk. Keep the final line `LIMITER_END = True`. Everything above `class LinkLimiter` stays exactly as it is, including the imports (`time`, `defaultdict`, `deque` are already imported).

## 1 - Scope
Edit only `lottery_checker/limits.py`. Replace only the two `raise NotImplementedError` bodies in `LinkLimiter`. No new files, no new imports.

## 2 - Gate
`py -3 -m pytest tests/test_link_limiter.py -q` must pass (6 tests). The test file is the only success condition.

## 3 - Behaviour
`LinkLimiter(per_email, per_ip, per_day, clock)` caps sign-in emails.
- `__init__`: each cap argument if not None, else from env: `TOTO_LINK_PER_EMAIL` (default 3), `TOTO_LINK_PER_IP` (default 10), `TOTO_LINK_PER_DAY` (default 200), as int. `self.clock = clock or time.time`. Keep three stores: `defaultdict(deque)` of timestamps per email, `defaultdict(deque)` per ip, and one `deque` for the whole site.
- `allow(email, ip)`: key = `email.strip().lower()`. Drop timestamps older than 3600 s from the email and ip deques and older than 86400 s from the site deque. If the email deque has `>= per_email`, or the ip deque `>= per_ip`, or the site deque `>= per_day` entries, return False and record NOTHING (a refused call must not use any bucket). Otherwise append now to all three and return True.
