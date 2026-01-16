# Changelog

---

## [2.0.0] - 2026-01-16
**Author: Glxy97**

### New Features

#### System Tray Integration
- App can be minimized to system tray
- Tray icon with context menu (Show/Refresh/Settings/Exit)
- Configurable in Settings: "Minimize to System Tray"

#### Desktop Notifications
- Notifications when reaching usage thresholds
- Default thresholds: 80%, 95%, 99%, 100%
- Thresholds configurable in Settings
- Cooldown prevents notification spam (5 min)
- Separate notifications for 5-Hour and Weekly limits

#### Compact Mode
- Toggle button (▬) in header
- Reduces window height from 240px to ~90px
- Shows only progress bars and percentages
- Setting is persisted

#### Drag Snap
- Three modes: Off / Screen Edge / Taskbar
- **Screen Edge**: Window snaps to screen borders
- **Taskbar**: Window positions relative to Windows taskbar
- Collapsible when docked to edge

#### Token Refresh
- Automatic detection of expired sessions (401)
- Optional: Automatic re-login without prompt
- Desktop notification on session expiry

#### Retry Logic
- 3 attempts on API errors
- Exponential backoff (2s, 4s, 8s delay)
- Distinguishes: Network-Error, Auth-Error, Rate-Limit

#### API Status Indicator
- Colored dot in header (●)
- Green: Connected
- Yellow: Retry in progress
- Red: Error
- Tooltip shows details

### New Dependencies
- `pystray` - System tray functionality
- `Pillow` - Icon generation for tray
- `plyer` - Cross-platform desktop notifications

### Extended Settings
- Minimize to System Tray (Checkbox)
- Auto-refresh expired sessions (Checkbox)
- Window Snap Mode (Off/Edge/Taskbar)
- Notification Thresholds (configurable)
- Settings window enlarged (400x650)

### Technical Improvements
- Better error handling in `fetch_usage_data()`
- UI elements as instance variables for dynamic layout
- Config schema extended with new defaults

---

### Neue Features (Deutsch)

#### System Tray Integration
- App kann in den System Tray minimiert werden
- Tray-Icon mit Kontextmenü (Show/Refresh/Settings/Exit)
- Konfigurierbar in Settings: "Minimize to System Tray"

#### Desktop Notifications
- Benachrichtigungen bei Erreichen von Usage-Schwellenwerten
- Standard-Thresholds: 80%, 95%, 99%, 100%
- Schwellenwerte in Settings anpassbar
- Cooldown verhindert Notification-Spam (5 Min)
- Separate Notifications für 5-Hour und Weekly Limits

#### Compact Mode
- Toggle-Button (▬) im Header
- Reduziert Fensterhöhe von 240px auf ~90px
- Zeigt nur Progress-Bars und Prozentwerte
- Einstellung wird gespeichert

#### Drag Snap
- Drei Modi: Off / Screen Edge / Taskbar
- **Screen Edge**: Fenster rastet an Bildschirmrändern ein
- **Taskbar**: Fenster positioniert sich relativ zur Windows-Taskbar
- Ein/Ausklappbar wenn am Rand angedockt

#### Token Refresh
- Automatische Erkennung abgelaufener Sessions (401)
- Optional: Automatisches Re-Login ohne Nachfrage
- Desktop-Notification bei Session-Ablauf

#### Retry Logic
- 3 Versuche bei API-Fehlern
- Exponential Backoff (2s, 4s, 8s Verzögerung)
- Unterscheidung: Network-Error, Auth-Error, Rate-Limit

#### API Status Indikator
- Farbiger Punkt im Header (●)
- Grün: Verbunden
- Gelb: Retry läuft
- Rot: Fehler
- Tooltip zeigt Details

---

## [1.0.0] - Initial Release
**Author: LouisVanh**

### Features
- 5-Hour and Weekly Limit Tracking
- Click-Through Mode
- Cloudflare Bypass via undetected-chromedriver
- Opacity and refresh interval adjustable
- Session persistence in %APPDATA%
