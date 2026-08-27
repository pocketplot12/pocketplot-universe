# Native shell build instructions

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
