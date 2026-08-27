"""
PocketPlot Universe - v25 native + PWA builder.

Generates the files needed to:
  1. Enhance the PWA (manifest.json + sw.js upgrade)
  2. Configure native iOS/Android shells via Capacitor.js

Usage:
  cd /root/pocketplot
  python3 build_native.py
"""
import os
import shutil
from pathlib import Path

# v25 PWA manifest
MANIFEST_V25 = """{
  "name": "PocketPlot Universe",
  "short_name": "PocketPlot",
  "description": "Create. Roleplay. Explore. Premium storytelling for adults.",
  "id": "/",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "display_override": ["window-controls-overlay", "standalone", "browser"],
  "orientation": "any",
  "theme_color": "#0a0f1c",
  "background_color": "#0a0f1c",
  "categories": ["books", "entertainment", "lifestyle"],
  "lang": "en",
  "dir": "ltr",
  "icons": [
    {"src": "/logo-icon-32.png", "sizes": "32x32", "type": "image/png", "purpose": "any"},
    {"src": "/logo-icon-180.png", "sizes": "180x180", "type": "image/png", "purpose": "any maskable"},
    {"src": "/logo-icon.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
    {"src": "/logo-halo-icon.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ],
  "screenshots": [
    {"src": "/logo-halo-600.png", "sizes": "1200x630", "type": "image/png", "form_factor": "wide"}
  ],
  "shortcuts": [
    {"name": "My worlds", "short_name": "Worlds", "url": "/worlds",
     "icons": [{"src": "/logo-icon-32.png", "sizes": "32x32"}]},
    {"name": "New world", "short_name": "New", "url": "/worlds/new",
     "icons": [{"src": "/logo-icon-32.png", "sizes": "32x32"}]},
    {"name": "Seed generator", "short_name": "Seed", "url": "/seed",
     "icons": [{"src": "/logo-icon-32.png", "sizes": "32x32"}]}
  ],
  "share_target": {
    "action": "/share-target",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {"title": "title", "text": "text", "url": "url"}
  },
  "launch_handler": {"client_mode": "focus-existing"}
}
"""

# v25 service worker
SW_V25 = """// PocketPlot Universe service worker (v25)
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

  if (url.pathname.match(/\\\\.(css|js|woff2?|ttf|svg|png|jpg|webp)$/)) {
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
"""

# v25 Capacitor config
CAPACITOR_CONFIG = """{
  "appId": "app.pocketplot.universe",
  "appName": "PocketPlot Universe",
  "webDir": ".",
  "bundledWebRuntime": false,
  "server": {
    "androidScheme": "https",
    "iosScheme": "https",
    "cleartext": false
  },
  "plugins": {
    "SplashScreen": {
      "launchShowDuration": 1500,
      "backgroundColor": "#0a0f1c"
    },
    "StatusBar": {
      "style": "DARK",
      "backgroundColor": "#0a0f1c"
    },
    "DeepLinks": {
      "universalLinks": {
        "android": ["pocketplot.app"],
        "ios": ["applinks:pocketplot.app"]
      }
    }
  },
  "ios": {
    "contentInset": "automatic",
    "backgroundColor": "#0a0f1c"
  },
  "android": {
    "allowMixedContent": false,
    "captureInput": true
  }
}
"""

# Native build README
NATIVE_README = """# Native shell build instructions

PocketPlot Universe ships as a PWA by default. To wrap it in a native iOS/Android shell, use Capacitor.js.

## Prerequisites

```bash
# Install Capacitor + iOS + Android
npm install -g @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android
```

## Add iOS shell

```bash
cd /root/pocketplot
npx cap add ios
# Configure team in Xcode:
#   1. Open ios/App/App.xcworkspace
#   2. Select "App" target -> Signing & Capabilities
#   3. Set your Apple Developer Team ID
#   4. Set bundle identifier: app.pocketplot.universe
npx cap copy ios
npx cap open ios
```

## Add Android shell

```bash
cd /root/pocketplot
npx cap add android
# Configure signing:
#   1. Open android/app/build.gradle
#   2. Set signingConfigs.release with your keystore
npx cap copy android
npx cap open android
```

## Push notifications

Service worker handles push delivery. Server-side push requires VAPID keys (lands in v26).

## Deep links

Universal links configured for `pocketplot.app`. Configure associated domains in App Store Connect + Play Console.

## File structure

```
pocketplot/
├── app.py                  (Flask backend, single file)
├── manifest.json           (PWA manifest, served at /manifest.json)
├── sw.js                   (Service worker, served at /sw.js)
├── capacitor.config.json   (Capacitor config for native shells)
├── ...
└── www/                    (Optional: web build output if you add a bundler)
```

When you run `npx cap copy`, Capacitor copies everything from the project root into the native projects.
"""


def main():
    project = Path('/root/pocketplot')
    # Write v25 manifest.json (overwrites old)
    (project / 'manifest.json').write_text(MANIFEST_V25)
    print('Wrote manifest.json (v25)')
    # Write v25 sw.js (overwrites old)
    (project / 'sw.js').write_text(SW_V25)
    print('Wrote sw.js (v25)')
    # Write capacitor.config.json
    (project / 'capacitor.config.json').write_text(CAPACITOR_CONFIG)
    print('Wrote capacitor.config.json')
    # Write native build README
    (project / 'NATIVE_BUILD.md').write_text(NATIVE_README)
    print('Wrote NATIVE_BUILD.md')
    print('\nDone. PWA + native shell config files updated.')


if __name__ == '__main__':
    main()
