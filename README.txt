=====================================================================
  SlidesHost
  Control your presentations from your phone, over WiFi.
=====================================================================
Localhost possibilities explored.

contact: slideshostapp@gmail.com
 
SlidesHost is a Windows app that turns your phone into a presentation
remote. Scan a QR code, approve the phone on your PC, and your phone's
browser becomes a controller for PowerPoint, PDF readers, Word and more.
Nothing to install on the phone.

*** VIBE-CODED WITH AI ***
Slideshost is a completely vibe-coded app, developed with Claude AI (Anthropic) and Copilot AI.
It was built by describing what I wanted and iterating with AI
assistants. Expect rough edges, review the code before trusting it, and
please open an issue if something breaks. Thank you <3
 
---------------------------------------------------------------------
  !! WINDOWS SMARTSCREEN WARNING (unsigned .exe) !!
---------------------------------------------------------------------
If you run a built SlidesHost .exe, Windows may show a SmartScreen
message: "Windows protected your PC". This happens because the .exe is
not code-signed, not because anything is wrong with it.
 
    Click "More info", then click "Run anyway".
 
If you prefer not to run an unsigned .exe, run the app from source
instead (see "Run from source" below). All the code is in this repo.
 
 
---------------------------------------------------------------------
  FEATURES
---------------------------------------------------------------------
Connecting
  - Scan the QR code on the PC with your phone camera (same WiFi).
  - The QR holds a one-time token that expires after 5 minutes.
  - The PC asks you to Allow or Deny each new phone.
  - Only phones that have scanned the QR appear in the list.
  - Phones are NOT saved: the device list is cleared when the app
    closes, so you scan the QR code again each time.
  - The phone's model is used as its default name. Rename a phone from
    the PC app or by tapping its name on the phone page.
 
Phone controller
  - Swipe left = previous slide, swipe right = next slide.
  - Start presentation and Stop presenting buttons.
  - Preview: a live view of the primary display on your phone, with
      * Laser pointer (touch to point)
      * Draw on the slide, with Undo, Redo and Clear all
      * Pinch zoom (zooms what the audience sees) and Reset zoom
  - Blur slide: hides the slide behind a blurred copy of the screen.
  - Stage curtain: red stage curtains close over the screen and open
    again.
  - Mic drop: plays a mic-drop sound on the PC speakers (4 second
    cooldown).
 
Windows app
  - Modern, minimal window (it is set to not open in fullscreen).
  - Phone list on the left, QR code on the right.
  - Buttons: Use as controller, Rename, Forget.
 
Works with
  - PowerPoint / LibreOffice Impress (arrow keys, F5 to start)
  - Word, PDF readers and browsers (Page Up / Page Down)
  - Adobe Reader (Ctrl+L to start), Chrome / Edge / Firefox (F11)
  Slide changes are sent as keystrokes to the last app you used, so
  keep your presentation app open.
 
 
---------------------------------------------------------------------
  REQUIREMENTS
---------------------------------------------------------------------
  - Windows 10 or 11
  - PC and phone on the same WiFi network
  - A phone with a modern browser (Chrome, Safari, Edge, Brave...)
 
 
---------------------------------------------------------------------
  RUN FROM SOURCE
---------------------------------------------------------------------
1. Download or clone this repository and open the folder.
2. Double-click run.bat
   or, in a terminal (PowerShell) inside the folder, run:
 
   python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt; .venv\Scripts\python app.py
 
3. When Windows Firewall asks, allow access on "Private networks".
4. Scan the QR code with your phone, then click Allow on the PC.
 
Next time, just run:  .venv\Scripts\python app.py
 
 
---------------------------------------------------------------------
  BUILD AN .EXE (optional)
---------------------------------------------------------------------
Run build.bat. It uses PyInstaller and puts the result in
dist\SlidesHost\. The icon is included. (This script has not been
tested on many machines, and the resulting .exe is unsigned, so see the
SmartScreen note above.)
 
 
---------------------------------------------------------------------
  START MENU SHORTCUT
---------------------------------------------------------------------
Double-click add_to_start_menu.bat to add a SlidesHost shortcut (with
the app icon, no console window) to the Start menu. Right-click it to
pin it to the taskbar. This also refreshes the Windows icon cache.
 
 
---------------------------------------------------------------------
  HOW IT WORKS
---------------------------------------------------------------------
  - The PC app runs a small local web server (port 8765) on your WiFi.
  - The QR code opens a controller page served by the PC, and the phone
    talks to the PC over a WebSocket.
  - The PC app sends keystrokes to your presentation, streams a JPEG
    preview of your screen, and draws the laser, sketches, zoom, blur
    and curtain on a transparent click-through overlay.
 
Privacy and security
  - Everything stays on your local network. No cloud, no accounts, no
    data leaves your PC.
  - Pairing needs a one-time QR token plus your approval on the PC.
  - No device names or credentials are written to disk.
  - Anyone on the same WiFi who scans the QR code can ask to connect,
    but they cannot control anything until you click Allow.
 
 
---------------------------------------------------------------------
  TROUBLESHOOTING
---------------------------------------------------------------------
Phone can't connect
  - Make sure the phone and PC are on the same WiFi, and that the WiFi
    does not block device-to-device traffic ("client isolation", common
    on guest, school and conference networks). A phone hotspot or your
    PC's mobile hotspot works well as a fallback.
  - Allow Python (or SlidesHost) through Windows Firewall on private
    networks.
 
Brave browser on the phone
  - If the page says it can't reach your PC, tap the lion icon and turn
    Shields off for the page.
 
Slide controls do nothing
  - Click once inside your presentation app so it is the last window
    you used, then try again. Preview, laser, zoom and drawing use the
    primary display only.
 
Old or blurry icon
  - Run add_to_start_menu.bat to refresh the icon cache, then unpin and
    re-pin the taskbar icon.
 
 
---------------------------------------------------------------------
  PROJECT FILES
---------------------------------------------------------------------
  app.py                 Windows app: window, overlay, key sending
  server.py              Local web server, pairing and approvals
  web/index.html         The phone controller page
  web/logo.png, icon-*   Logos used by the app and the phone page
  logo.ico               App icon (14 sizes, 16 to 256 px)
  requirements.txt       Python packages
  run.bat                One-click run from source
  build.bat              Build an .exe with PyInstaller
  add_to_start_menu.*    Start menu shortcut helper
 
 
---------------------------------------------------------------------
  KNOWN LIMITS
---------------------------------------------------------------------
  - Windows only.
  - Sends keystrokes, so it controls whichever app you used last.
  - No slide counter or slide notes yet.
  - Screen features work on the primary display only.
  - Built quickly with AI help: not audited, and not tested on every
    app, browser or network.
 
 
---------------------------------------------------------------------
  CREDITS AND LICENSE
---------------------------------------------------------------------

Developed by: Charls K Varghes

Vibe-coded with Claude AI (Anthropic) and Copilot .
 
License: none
 
