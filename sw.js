// PocketPlot Universe service worker (v25)
const CACHE_VERSION = 'v25';
const CACHE_NAMES = {
  html: 'pocketplot-html-v25',
  assets: 'pocketplot-assets-v25',
  worlds: 'pocketplot-worlds-v25',
  brand: 'pocketplot-brand-v25',
};

const BRAND_FILES = [
  '/logo.svg', '/logo-icon-32.png', '/logo-icon-180.png', '/logo-icon.png',
  '/logo-halo-icon-32.png', '/logo-halo-icon-180.png', '/logo-halo-icon.png',
  '/logo-halo-240.png', '/logo-halo-600.png', '/logo-halo-og.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAMES.brand).then((cache) => cache.addAll(BRAND_FILES))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => !Object.values(CACHE_NAMES).includes(k)).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  if (BRAND_FILES.includes(url.pathname)) {
    event.respondWith(
      caches.open(CACHE_NAMES.brand).then((cache) =>
        cache.match(req).then((cached) => cached || fetch(req).then((resp) => {
          cache.put(req, resp.clone()); return resp;
        }))
      )
    );
    return;
  }

  if (url.pathname.match(/\\.(css|js|woff2?|ttf|svg|png|jpg|webp)$/)) {
    event.respondWith(
      caches.open(CACHE_NAMES.assets).then((cache) =>
        cache.match(req).then((cached) => cached || fetch(req).then((resp) => {
          if (resp.ok) cache.put(req, resp.clone());
          return resp;
        }).catch(() => cached))
      )
    );
    return;
  }

  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE_NAMES.html).then((cache) => cache.put(req, copy));
        return resp;
      }).catch(() => caches.match(req))
    );
    return;
  }
});

self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'PocketPlot Universe', {
      body: data.body || 'New activity in your worlds.',
      icon: '/logo-icon-180.png',
      badge: '/logo-icon-32.png',
      data: data.url || '/',
      tag: data.tag || 'pocketplot-default',
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data || '/';
  event.waitUntil(clients.openWindow(url));
});
