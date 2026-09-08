/* Courtside service worker.
   Job: make the app open with zero network. It caches the shell on install,
   serves the shell from cache first, and never caches API traffic. */

/* Bump this string to push an update to installed phones. Changing sw.js at
   all is what makes the browser re-check it; the activate handler then drops
   every older cache. */
const CACHE = "courtside-v8";
const SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/maskable-512.png",
  "./icons/apple-touch-icon.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      /* addAll is all-or-nothing; add individually so one missing icon
         cannot leave the app with no offline cache at all. */
      .then((c) => Promise.all(SHELL.map((u) => c.add(u).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  /* Courtside makes no API calls at all - it never talks to any server once
     the shell is cached. Anything cross-origin is therefore not ours. */
  if (url.origin !== location.origin) return;

  /* Navigations: answer from cache immediately so the app opens with no
     signal, but refresh the copy in the background. Without the refresh an
     installed phone would keep serving the first version it ever cached and
     could never be updated. */
  if (req.mode === "navigate") {
    /* Match the app's OWN address exactly, not "any path ending in a slash".
       That looser test meant navigating to any subdirectory - /tools/, say -
       took the app branch, fetched that directory's page, and wrote it into
       the cache under ./index.html. The app shell was then permanently
       replaced by a directory listing, which on an installed phone bricks it
       until someone clears site data. Observed, not theorised. */
    const root = new URL("./", self.registration.scope).pathname;
    const p = url.pathname;
    const isApp = p === root || p === root + "index.html";
    if (!isApp) {
      e.respondWith(fetch(req).catch(() => caches.match(req)));
      return;
    }
    e.respondWith(
      caches.match("./index.html").then((hit) => {
        const fresh = fetch(req).then((res) => {
          /* only ever cache the shell under the shell's key, and only when
             the response really is the shell */
          if (res && res.ok && res.type === "basic" && isApp) {
            caches.open(CACHE).then((c) => c.put("./index.html", res.clone()));
          }
          return res;
        }).catch(() => null);
        return hit || fresh.then((r) => r || caches.match("./"));
      })
    );
    return;
  }

  e.respondWith(
    caches.match(req).then((hit) => {
      if (hit) {
        /* refresh in the background so the next open is current */
        fetch(req).then((res) => {
          if (res && res.ok) caches.open(CACHE).then((c) => c.put(req, res.clone()));
        }).catch(() => {});
        return hit;
      }
      return fetch(req).then((res) => {
        if (res && res.ok && res.type === "basic") {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => caches.match("./index.html"));
    })
  );
});
