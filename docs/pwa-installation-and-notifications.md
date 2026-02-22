# PWA Installation & Push Notifications Guide

A practical reference for installing the ShutterSense PWA and troubleshooting push notifications across platforms and browsers.

> **See also:** [Notifications Guide](notifications.md) for VAPID key setup, notification types, and preferences configuration.

---

## Table of Contents

- [PWA Installation](#pwa-installation)
  - [Installation by Platform](#installation-by-platform)
  - [Default Browser Myth (macOS)](#default-browser-myth-macos)
  - [iOS / iPadOS Constraints](#ios--ipados-constraints)
  - [Summary Matrix](#installation-summary-matrix)
- [Push Notifications](#push-notifications)
  - [How macOS Notification Attribution Works](#how-macos-notification-attribution-works)
  - [Edge on macOS: The Attribution Flag](#edge-on-macos-the-attribution-flag)
  - [Chrome on macOS](#chrome-on-macos)
  - [Safari on macOS](#safari-on-macos)
  - [iOS / iPadOS Push](#ios--ipados-push)
  - [Android Push](#android-push)
  - [Cross-Platform Support Matrix](#cross-platform-support-matrix)
- [Troubleshooting](#troubleshooting)
  - [macOS (Chrome)](#macos-chrome)
  - [macOS (Edge)](#macos-edge)
  - [iOS / iPadOS](#ios--ipados-1)
  - [General Checklist](#general-checklist)
- [Future Improvements](#future-improvements)

---

## PWA Installation

### Installation by Platform

#### macOS (Desktop)

| Browser | Install Method | Notes |
|---------|---------------|-------|
| **Chrome** | Click install icon in address bar, or Menu > "Install ShutterSense" | Creates app shim in `~/Applications/Chrome Apps/` |
| **Edge** | Click install icon in address bar, or Menu > Apps > "Install this site as an app" | Creates standalone app in Applications |
| **Safari 17+** (Sonoma) | File > Add to Dock | Not a full PWA install — copies cookies at install time, then uses separate storage |
| **Firefox** | Not supported | macOS PWA support not available (Windows-only experimentally since Firefox 143, Sept 2025) |

#### Windows

| Browser | Install Method | Notes |
|---------|---------------|-------|
| **Chrome** | Address bar install icon | Standard PWA install |
| **Edge** | Address bar install icon | Deep Windows integration: Start Menu, taskbar pinning, auto-start |
| **Firefox 143+** | Experimental | Enable via `about:preferences#experimental` or `browser.taskbarTabs.enabled` in `about:config` |

#### Android

| Browser | Install Method | Notes |
|---------|---------------|-------|
| **Chrome** | Menu > "Install app" or "Add to Home Screen" | Also shows install banner automatically |
| **Edge** | Menu > "Add to phone" | Standard install |
| **Firefox** | Menu > "Install" | Supported |
| **Samsung Internet** | Menu > "Add page to" > "Home screen" | Supported |

#### iOS / iPadOS

| Browser | Install Method | Notes |
|---------|---------------|-------|
| **Safari** | Share > "Add to Home Screen" | Primary method; required for push notifications |
| **Chrome** (iOS 16.4+) | Share > "Add to Home Screen" | Share button added in address bar since iOS 17 |
| **Edge** (iOS 16.4+) | Share > "Add to Home Screen" | Same mechanism as Chrome |
| **Firefox** (iOS 16.4+) | Share > "Add to Home Screen" | Same mechanism |

### Default Browser Myth (macOS)

A common misconception is that PWAs can only be installed from the **default browser**. This is **not true** on any platform.

**What actually happens:**

- Each Chromium-based browser (Chrome, Edge, Brave) can independently install PWAs regardless of which browser is set as default.
- Safari (macOS Sonoma+) can add sites to the Dock regardless of default browser status.
- PWA installations are **per-browser** — installing in Chrome doesn't affect Edge and vice versa.

**What "default browser" does affect:**

- **URL handling from external apps.** If you click a link in Mail, Slack, or another application, it opens in the default browser — not in the PWA. This is an OS-level behavior, not a PWA limitation.
- **Link capture.** Some browsers can intercept URLs that match a PWA's scope and open the PWA instead. This works more reliably when the browser is the default.

**Why it may seem like only the default browser can install:**

If you visit the app in a non-default browser and the install prompt doesn't appear, the most common cause is **stale cached data**. This has been confirmed on ShutterSense deployments:

1. **Stale cache from early deployments.** If the browser visited the app before the PWA manifest or service worker was properly configured (e.g., during initial production deployment), it may have cached responses that prevent installability. **Fix:** Clear all site data for the app (Settings > Privacy > Site Settings > [site] > Clear data), then reload. This is the most common cause and was confirmed to resolve the issue on macOS with both Chrome and Edge.
2. **Cached manifest issues.** The browser may have a cached version of the manifest that is missing required fields or icons. Clearing site data forces a fresh fetch.
3. **Browser install UI differences.** Different browsers surface the install option differently — look for the install icon in the address bar or in the app menu rather than expecting an automatic prompt.

> **Deployment lesson:** Service worker and manifest misconfigurations during initial deployment have **long-lasting consequences**. Browsers aggressively cache these resources, so a broken first impression can persist indefinitely until the user manually clears site data. Ensure the PWA manifest and service worker are correctly configured *before* the first production deployment, or be prepared to instruct users to clear site data.

### iOS / iPadOS Constraints

iOS has the most restrictive PWA support of any platform:

1. **All browsers on iOS use WebKit under the hood** (Apple's App Store policy). Chrome, Edge, and Firefox on iOS are essentially Safari with different UIs. PWA capabilities are limited to what Safari's WebKit engine supports.
2. **Push notifications require Home Screen installation.** You cannot receive push notifications from a website open in a browser tab on iOS — only from installed PWAs.
3. **No silent push.** Every push message must display a visible notification.
4. **No rich media.** Notification content is limited to text and the app icon — no inline images.

### Installation Summary Matrix

| Platform | Chrome | Edge | Safari | Firefox |
|----------|--------|------|--------|---------|
| **macOS** | Full PWA | Full PWA | Add to Dock (limited) | Not supported |
| **Windows** | Full PWA | Full PWA (best integration) | N/A | Experimental (143+) |
| **Android** | Full PWA | Full PWA | N/A | Full PWA |
| **iOS/iPadOS** | Via Share (WebKit) | Via Share (WebKit) | Via Share (native) | Via Share (WebKit) |

---

## Push Notifications

### How macOS Notification Attribution Works

macOS routes every notification through `UNUserNotificationCenter`, which attributes notifications to a **specific application bundle**. Users see and manage these per-app in System Settings > Notifications.

**The problem for Chromium-based PWAs:**

Chromium browsers use a separate **notification helper process** to deliver notifications:
- Chrome: `Google Chrome Helper (Alerts).app`
- Edge: `Microsoft Edge Helper (Alerts).app`

This helper exists because macOS only allows one notification style (banner or alert) per app bundle. The browser's main process uses one style, so a separate helper handles the other.

**The consequence:** All notifications from all PWAs installed via the same browser appear under the same helper app in macOS Notification Center. Users cannot selectively control notifications per PWA in System Settings — they can only enable/disable the entire browser's notifications.

This also means:
- Notification badges appear on the **browser's** Dock icon, not the PWA's.
- The notification banner may show "Google Chrome" or "Microsoft Edge" instead of "ShutterSense".

### Edge on macOS: The Attribution Flag

**This is the most common issue for ShutterSense push notifications on macOS with Edge.**

Edge has an experimental flag that fixes notification attribution for PWAs:

```text
edge://flags/#enable-mac-pwas-notification-attribution
```

| Flag Value | Behavior |
|-----------|----------|
| **Default** | Notifications appear under "Microsoft Edge" — **PWA notifications will not display** or will be attributed to Edge |
| **Enabled** | Notifications are properly attributed to the installed PWA and will display correctly |

**To enable:**

1. Open Edge and navigate to `edge://flags`
2. Search for `enable-mac-pwas-notification-attribution`
3. Set it to **Enabled**
4. Restart Edge when prompted

**Important notes:**
- As of early 2026, this flag defaults to "Default" (disabled), meaning notifications will silently fail for PWAs on macOS unless explicitly enabled.
- Edge 105+ introduced improvements to show PWA names and icons in notification content, but the system-level attribution (which is what macOS uses to route and display notifications) requires this flag.
- This flag may be promoted to enabled-by-default in a future Edge release. Monitor Edge release notes for changes.

**Related Chromium issues:**
- [Chromium #40874345](https://issues.chromium.org/issues/40874345) — "PWA notification should use app (not Chrome) icon" on macOS
- [Chromium #40246993](https://issues.chromium.org/issues/40246993) — macOS Alerts Notification Helper naming
- [Chromium #370536109](https://issues.chromium.org/issues/370536109) — `notificationclick` not handled on macOS 15 (Sequoia)

### Chrome on macOS

Chrome handles PWA notification attribution differently from Edge:

1. **System-level notification permissions** must be granted. On managed macOS devices (corporate MDM), Chrome notifications may be disabled by policy.
   - Check: System Settings > Notifications > Google Chrome Helper (Alerts) — must be enabled.
   - If missing from the list, Chrome may need to trigger a notification first for macOS to register it.

2. Chrome generally attributes PWA notifications more reliably than Edge on macOS, but they still appear under "Google Chrome Helper (Alerts)" in System Settings.

3. There is a similar flag in Chrome (`chrome://flags`) for notification improvements, though Chrome has shipped more of these features to stable than Edge has.

### Safari on macOS

Safari (macOS Sonoma+ / Safari 17+) takes a fundamentally different approach:

- Web apps added via **File > Add to Dock** get their own **independent app bundle**.
- Notifications appear under the web app's own name in System Settings > Notifications.
- This completely avoids the attribution problem that Chromium-based browsers have.

**Limitations:**
- Safari's "Add to Dock" is not a full PWA install — it copies cookies at install time but uses separate storage afterward.
- The Badging API (`navigator.setAppBadge()`) works for Dock web apps but not in regular Safari tabs.
- Safari 18.4+ (iOS/iPadOS) and Safari 18.5+ (macOS 15.5+) support **Declarative Web Push** — notifications can be delivered without an active service worker (Safari-only feature as of early 2026).

### iOS / iPadOS Push

Push notifications on iOS require:

1. The PWA must be **installed on the Home Screen** (via Share > Add to Home Screen).
2. Notification permission must be requested in response to a **user gesture** (e.g., button tap).
3. iOS 16.4 or later is required.

**Key limitations:**
- No silent push — every push event must display a visible notification.
- No notification action buttons (limited support).
- No inline images in notifications.
- Service workers may be evicted by Safari's Intelligent Tracking Prevention (ITP) if the user hasn't visited the PWA recently, breaking push subscriptions.

### Android Push

Android has the most complete push notification support:

- Works in both browser tabs and installed PWAs.
- Supports silent push, rich media, notification actions, and badge counts.
- No special flags or workarounds needed.

### Cross-Platform Support Matrix

| Feature | Chrome (macOS) | Edge (macOS) | Safari (macOS) | Chrome (Android) | Safari (iOS) |
|---------|---------------|-------------|----------------|-----------------|-------------|
| Push API | Yes | Yes (needs flag) | Yes (16+) | Yes | Yes (16.4+, PWA only) |
| Notification attribution | Browser helper | Browser helper (flag fixes) | Own app identity | App identity | Own app identity |
| Badge API | Yes | Yes | Dock apps only | Yes | Yes (PWA only) |
| Silent push | Yes | Yes | No | Yes | No |
| Notification actions | Yes | Yes | Limited | Yes | Limited |
| Rich media (images) | Yes | Yes | No | Yes | No |
| `notificationclick` | Yes (macOS 15 bug) | Yes (macOS 15 bug) | Yes | Yes | Yes |
| Service worker persistence | Reliable | Reliable | May be evicted (ITP) | Reliable | May be evicted (ITP) |

---

## Troubleshooting

### macOS (Chrome)

**Notifications not appearing at all:**

1. Check System Settings > Notifications — look for "Google Chrome Helper (Alerts)".
   - If it's missing, Chrome hasn't registered its notification helper yet. Send a test notification from the app to trigger registration.
   - If it's listed but disabled, enable it.
2. On **managed/corporate macOS devices**, a system policy may block Chrome notifications entirely. Check with your IT department or inspect profiles in System Settings > Privacy & Security > Profiles.
3. Check Chrome's site-level notification permission: Settings > Privacy and Security > Site Settings > Notifications — ensure the ShutterSense domain is in the "Allowed" list.
4. Check macOS Focus mode is not suppressing notifications.

**Notifications appear as "Google Chrome" instead of "ShutterSense":**

This is the attribution issue described above. On Chrome, there is no easy workaround — notifications will be grouped under Chrome's helper app. Consider using Safari's "Add to Dock" if proper attribution is important.

### macOS (Edge)

**Notifications not appearing at all:**

1. **First: enable the attribution flag.** Navigate to `edge://flags/#enable-mac-pwas-notification-attribution` and set it to **Enabled**. Restart Edge. This is the most common fix.
2. Check System Settings > Notifications — look for "Microsoft Edge Helper (Alerts)" and ensure it's enabled.
3. Check Edge's notification permissions: Settings > Cookies and site permissions > Notifications — ensure the ShutterSense domain is allowed.
4. Verify the PWA is properly installed (not just a browser tab).

**Notifications work in Edge browser but not in the installed PWA:**

This is almost certainly the attribution flag issue. When the flag is disabled/default, macOS cannot route notifications to the PWA because the notification isn't attributed to the PWA's app bundle.

### iOS / iPadOS

**"Enable notifications" button doesn't appear:**

1. The PWA must be opened from the Home Screen icon — not from a browser tab.
2. iOS 16.4 or later is required.
3. The notification permission prompt only appears on user gesture (tap/click) — it cannot trigger automatically on page load.

**Notifications stop arriving after a while:**

Safari's ITP may have evicted the service worker. Open the PWA from the Home Screen to re-register. The app's service worker lifecycle code includes automatic re-registration on activation.

**Notifications never arrive:**

1. Check iOS Settings > Notifications > ShutterSense — ensure notifications are enabled.
2. Check iOS Settings > Focus — ensure Focus mode isn't suppressing notifications.
3. Check that the push subscription is still active: Notifications page > Devices section.

### General Checklist

| Check | How to Verify |
|-------|--------------|
| HTTPS | App must be served over HTTPS (required by Web Push standard) |
| VAPID keys | Server has `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, and `VAPID_SUBJECT` set |
| Browser permission | Browser shows ShutterSense as "Allowed" in notification settings |
| OS permission | System Settings > Notifications shows the browser/PWA as enabled |
| Subscription active | Notifications page shows at least one active device |
| Service worker | DevTools > Application > Service Workers shows active SW |
| Focus/DND | OS-level Do Not Disturb or Focus mode is off |
| macOS Edge flag | `edge://flags/#enable-mac-pwas-notification-attribution` is **Enabled** |

---

## Future Improvements

### 1. In-App Notification Permission Diagnostics

Add a diagnostic panel in the notification settings page that checks and reports:

- Whether the browser supports the Push API
- Whether notification permission is granted, denied, or default
- Whether a service worker is registered and active
- Whether the VAPID public key is available from the server
- Whether the push subscription endpoint is reachable
- **Platform-specific warnings** (e.g., "You're using Edge on macOS — check that the notification attribution flag is enabled")

This would replace manual troubleshooting with automated detection and guidance.

### 2. Safari "Add to Dock" Detection and Guidance

Safari's "Add to Dock" web apps get better notification attribution than Chromium PWAs on macOS. The app could detect when it's running in Safari on macOS and suggest "Add to Dock" as the preferred installation method, with instructions.

Detection is possible via:
```javascript
// Safari standalone detection
const isSafariStandalone = window.navigator.standalone === true;
// Or via display-mode media query
const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
```

### 3. Declarative Web Push Support (Safari 18.4+)

> **PRD available:** See [026-declarative-web-push.md](prd/026-declarative-web-push.md) for the full implementation plan.

Safari 18.4+ (macOS 15.4 / iOS 18.4) and Safari 26 (iOS 26) support **Declarative Web Push** — a standard where push payloads contain notification content directly, without requiring a Service Worker to process them. This is the most impactful improvement for iOS push reliability, as it eliminates silent notification loss caused by ITP evicting Service Workers.

**References:**
- [WebKit Blog — Meet Declarative Web Push](https://webkit.org/blog/16535/meet-declarative-web-push/)
- [WWDC25 Session 235 — Learn more about Declarative Web Push](https://developer.apple.com/videos/play/wwdc2025/235/)

### 4. Push Subscription Health Monitoring

Implement server-side monitoring of push subscription health:

- Track delivery success/failure rates per subscription endpoint
- Automatically remove subscriptions that return HTTP 410 (Gone) — already implemented in `push_subscription_service.py`
- Alert users when their subscription appears unhealthy (e.g., consecutive delivery failures)
- Periodic "keep-alive" test pushes (opt-in) to detect silently broken subscriptions

### 5. Multi-Browser Installation Guidance

Since users may have multiple browsers installed, the app could detect the current browser and provide tailored installation instructions, including:

- Browser-specific steps for PWA installation
- Known issues for that browser/platform combination
- Whether any flags need to be enabled (e.g., Edge attribution flag)
- Link to this documentation for advanced troubleshooting

### 6. Firefox PWA Support Monitoring

Firefox added experimental PWA support on Windows in Firefox 143 (September 2025). macOS and Linux support is tracked in [Mozilla Bug #1407202](https://bugzilla.mozilla.org/show_bug.cgi?id=1407202). When Firefox ships macOS PWA support, the app should be tested and this documentation updated.

---

## References

- [MDN — Making PWAs Installable](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable)
- [MDN — Installing and Uninstalling Web Apps](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Installing)
- [web.dev — PWA Installation](https://web.dev/learn/pwa/installation)
- [WebKit Blog — Web Push for Web Apps on iOS and iPadOS](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)
- [WebKit Blog — Meet Declarative Web Push](https://webkit.org/blog/16535/meet-declarative-web-push/)
- [Apple Developer — Sending Web Push Notifications](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers)
- [Chrome Developer Blog — Moving to Native macOS Notifications](https://developer.chrome.com/blog/native-mac-os-notifications)
- [Chromium Issue #40874345 — PWA notification should use app icon](https://issues.chromium.org/issues/40874345)
- [Chromium Issue #370536109 — notificationclick on macOS 15](https://issues.chromium.org/issues/370536109)
- [Mozilla Bug #1407202 — Desktop PWA Meta Bug](https://bugzilla.mozilla.org/show_bug.cgi?id=1407202)
