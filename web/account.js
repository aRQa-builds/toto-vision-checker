/* P4-04 browser account client: sign-in, saved history. Plain script, no
   modules; the page uses window.TotoAccount, tests load it with require(). */
(function (root) {
  function createAccountClient(fetchFn) {
    throw new Error("not implemented");
  }

  function loginTokenFromHash(hash) {
    throw new Error("not implemented");
  }

  const api = { createAccountClient, loginTokenFromHash };
  root.TotoAccount = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
/* ACCOUNT_JS_END */
