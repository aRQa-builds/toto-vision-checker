/* P4-04 browser account client: sign-in, saved history. Plain script, no
   modules; the page uses window.TotoAccount, tests load it with require(). */
(function (root) {
  function createAccountClient(fetchFn) {
    async function call(method, url, payload) {
      const opts = { method, headers: {}, credentials: "same-origin" };
      if (method !== "GET") opts.headers["X-Toto"] = "1";
      if (payload !== undefined) {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(payload);
      }
      let r;
      try {
        r = await fetchFn(url, opts);
      } catch (e) {
        throw makeError(["Can't reach the checker right now. Try again in a minute."], 0);
      }
      let data = null;
      try {
        data = await r.json();
      } catch (e) {
        data = null;
      }
      if (!r.ok) {
        const p = data && data.detail && data.detail.problems;
        const problems = Array.isArray(p) && p.length ? p : ["Something went wrong. Try again."];
        throw makeError(problems, r.status);
      }
      return data;
    }

    function makeError(problems, status) {
      const err = new Error(problems[0]);
      err.problems = problems;
      err.status = status;
      return err;
    }

    return {
      me: () => call("GET", "/api/me"),
      requestLink: (email) => call("POST", "/api/auth/request", { email }),
      verify: (token) => call("POST", "/api/auth/verify", { token }),
      logout: () => call("POST", "/api/auth/logout"),
      history: async () => (await call("GET", "/api/history")).entries,
      save: async (entry) => (await call("POST", "/api/history", entry)).id,
      remove: (id) => call("DELETE", "/api/history/" + id),
      deleteAccount: () => call("DELETE", "/api/account"),
    };
  }

  function loginTokenFromHash(hash) {
    if (typeof hash !== "string") return null;
    const m = hash.match(/^#login=([A-Za-z0-9_-]{20,200})$/);
    return m ? m[1] : null;
  }

  const api = { createAccountClient, loginTokenFromHash };
  root.TotoAccount = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
/* ACCOUNT_JS_END */
