/* Service worker (P4-06). Makes the checker installable and gives a clear
   offline message. It never caches /api/: results and checks always come
   fresh from the server, so a stale result can never be shown.
   Bump VERSION when the page changes so phones pick up the new copy.

   Share target (22 Oct 2026): on Android, Share on a screenshot can send it
   straight to the installed app. The browser POSTs the pictures to /share-target;
   this worker keeps them in a cache named toto-shared (on the phone only, never
   sent anywhere) and redirects to /?shared=N. The page reads them back, deletes
   them at once and reads them like screenshots chosen from the gallery. */
const VERSION = "toto-check-v20";
const SHARED = "toto-shared";            // screenshots shared into the app, held only until the page picks them up
const SHELL = ["/", "/offline.html", "/manifest.webmanifest",
               "/icons/icon-192.png", "/icons/icon-512.png", "/icons/maskable-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION && k !== SHARED).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method === "POST" && url.origin === location.origin && url.pathname === "/share-target"){
    e.respondWith((async () => {
      let n = 0;
      try {
        const form = await e.request.formData();
        const files = form.getAll("screenshots").filter(f => f && f.type && f.type.startsWith("image/")).slice(0, 200);
        const cache = await caches.open(SHARED);
        for (const k of await cache.keys()) await cache.delete(k);      // only the latest share
        await Promise.all(files.map((f, i) => cache.put("/shared/" + i,
          new Response(f, {headers: {"Content-Type": f.type}}))));
        n = files.length;
      } catch (err) { n = 0; }
      return Response.redirect("/?shared=" + n, 303);
    })());
    return;
  }
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return;          // never cached
  if (url.pathname === "/owner") return;                 // owner view: never cached, never stored as "/"
  if (e.request.mode === "navigate") {
    // page: network first so updates show at once; cached copy, then offline page, if no network
    e.respondWith(fetch(e.request)
      .then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put("/", copy)); return r; })
      .catch(() => caches.match("/").then(r => r || caches.match("/offline.html"))));
    return;
  }
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
