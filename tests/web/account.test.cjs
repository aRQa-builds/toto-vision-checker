// P4-04 slice 6a: browser account client. Run: node --test tests/web/account.test.cjs
const test = require("node:test");
const assert = require("node:assert/strict");
const { createAccountClient, loginTokenFromHash } = require("../../web/account.js");

function fake(status, body) {
  const calls = [];
  const fn = async (url, opts) => {
    calls.push({ url, opts });
    return { ok: status >= 200 && status < 300, status, json: async () => body };
  };
  fn.calls = calls;
  return fn;
}

test("me is a plain GET and returns the JSON", async () => {
  const f = fake(200, { signed_in: true, email: "a@b.co" });
  const out = await createAccountClient(f).me();
  assert.deepEqual(out, { signed_in: true, email: "a@b.co" });
  assert.equal(f.calls[0].url, "/api/me");
  assert.equal(f.calls[0].opts.method, "GET");
  assert.equal(f.calls[0].opts.credentials, "same-origin");
});

test("state-changing calls send the X-Toto header and a JSON body", async () => {
  const f = fake(200, { ok: true });
  const c = createAccountClient(f);
  await c.requestLink("a@b.co");
  await c.verify("tok");
  await c.logout();
  const [req, ver, out] = f.calls;
  assert.equal(req.url, "/api/auth/request");
  assert.equal(req.opts.method, "POST");
  assert.equal(req.opts.headers["X-Toto"], "1");
  assert.equal(req.opts.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(req.opts.body), { email: "a@b.co" });
  assert.equal(ver.url, "/api/auth/verify");
  assert.deepEqual(JSON.parse(ver.opts.body), { token: "tok" });
  assert.equal(out.url, "/api/auth/logout");
  assert.equal(out.opts.headers["X-Toto"], "1");
});

test("history returns the entries array", async () => {
  const f = fake(200, { entries: [{ id: 1 }, { id: 2 }] });
  const out = await createAccountClient(f).history();
  assert.deepEqual(out, [{ id: 1 }, { id: 2 }]);
  assert.equal(f.calls[0].url, "/api/history");
  assert.equal(f.calls[0].opts.method, "GET");
});

test("save posts the entry and returns the new id", async () => {
  const f = fake(200, { ok: true, id: 7 });
  const id = await createAccountClient(f).save({ game: "toto" });
  assert.equal(id, 7);
  assert.equal(f.calls[0].url, "/api/history");
  assert.equal(f.calls[0].opts.method, "POST");
  assert.equal(f.calls[0].opts.headers["X-Toto"], "1");
  assert.deepEqual(JSON.parse(f.calls[0].opts.body), { game: "toto" });
});

test("remove and deleteAccount use DELETE with the header", async () => {
  const f = fake(200, { ok: true });
  const c = createAccountClient(f);
  await c.remove(12);
  await c.deleteAccount();
  assert.equal(f.calls[0].url, "/api/history/12");
  assert.equal(f.calls[0].opts.method, "DELETE");
  assert.equal(f.calls[0].opts.headers["X-Toto"], "1");
  assert.equal(f.calls[1].url, "/api/account");
  assert.equal(f.calls[1].opts.method, "DELETE");
  assert.equal(f.calls[1].opts.headers["X-Toto"], "1");
});

test("a server error throws with the problems list and status", async () => {
  const f = fake(429, { detail: { problems: ["Too many sign-in emails. Try again later."] } });
  await assert.rejects(createAccountClient(f).requestLink("a@b.co"), (e) => {
    assert.deepEqual(e.problems, ["Too many sign-in emails. Try again later."]);
    assert.equal(e.status, 429);
    assert.equal(e.message, "Too many sign-in emails. Try again later.");
    return true;
  });
});

test("an error without a problems list gets a generic message", async () => {
  const f = fake(500, null);
  await assert.rejects(createAccountClient(f).me(), (e) => {
    assert.deepEqual(e.problems, ["Something went wrong. Try again."]);
    assert.equal(e.status, 500);
    return true;
  });
});

test("a network failure throws a friendly problem", async () => {
  const f = async () => { throw new TypeError("failed to fetch"); };
  await assert.rejects(createAccountClient(f).me(), (e) => {
    assert.deepEqual(e.problems, ["Can't reach the checker right now. Try again in a minute."]);
    return true;
  });
});

test("loginTokenFromHash reads #login=<token> only", () => {
  const tok = "A".repeat(43);
  assert.equal(loginTokenFromHash("#login=" + tok), tok);
  assert.equal(loginTokenFromHash("#login=abc"), null);
  assert.equal(loginTokenFromHash("#other=" + tok), null);
  assert.equal(loginTokenFromHash(""), null);
  assert.equal(loginTokenFromHash(null), null);
  assert.equal(loginTokenFromHash("#login=" + tok + "&x=1"), null);
});
