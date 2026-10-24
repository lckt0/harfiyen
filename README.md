# Harfiyen

**English** · [Türkçe](README.tr.md)

**Progressive touch typing practice in the terminal (and on the desktop).** You start with the
home row, and new letters unlock one at a time as you master the ones you already have. It
supports Turkish Q, Turkish F and US English layouts, and needs nothing beyond the Python
standard library.

![Harfiyen main screen](docs/screenshots/ana-ekran.png)

> **A note before you start:** Harfiyen was originally built for my own setup and daily use, and later shared in case it helps someone else. It reflects my own hardware, tools and preferences, so it may not fit every system or workflow. Issues and suggestions are welcome, but please keep that in mind.

**About language.** Harfiyen started as a Turkish project. The interface is available in both
Turkish and English, and so are the practice words: set the interface language in Settings
(F2 → Interface language) or with `"arayuz": "en"` in the settings file, and the practice
language separately with `"dil": "en"`. The command-line options, settings keys, theme fields
and file names are Turkish words; the tables below explain each of them. The screenshots show
the Turkish interface.

## Features

- **Progressive lessons.** The last 20 attempts at each letter are tracked (the window size is
  adjustable). Once every unlocked letter is flawless, the next one unlocks. You can also
  require a target speed for mastery.
- **Smart practice lines.** Real words plus pronounceable pseudo-words built from the unlocked
  letters, alternating vowels and consonants. Weak letters and the most recently unlocked
  letter show up more often.
- **Four modes.** Lesson, weak spots (the letters and letter pairs you struggle with most),
  speed test, and free text (built-in texts or your own `.txt` files).
- **Capitals, punctuation and numbers** as options. When Shift is needed, the Shift key on the
  opposite hand is shown as well.
- **keybr-style overview.** Speed, accuracy and score with the change from the previous line,
  letter chips colored by confidence, last and best speed for the current letter, learning
  rate, accuracy streak and daily goal.
- **Motivation.** Daily goal and day streak, levels and XP, 19 badges, and statistics for the
  last 14 days, fingers, letters and speed tests.
- **Readable keyboard.** Keycaps in finger colors or as an error heat map; adjustable key
  style (depth, flat, floating), edge height and keyboard size.
- **Large text.** The practice line can be shown small, normal, large or huge; the large sizes
  are drawn with a built-in pixel font.
- **Keyboard layouts.** Turkish Q, Turkish F and US English; ISO, ANSI and 102-key ANSI
  physical layouts; optional numpad. Each layout/language pair keeps its own progress.
- **Themes and settings in JSON.** Six built-in themes, plus your own themes that inherit from
  another one. Settings can be changed in the file or inside the app, with a live preview.
- **Mouse support.** Buttons, menus, setting arrows, letter chips and the scroll wheel; every
  window has a close button.
- **Key lighting.** On keyboards with per-key RGB lighting, the key to press lights up on the
  keyboard itself (through OpenRGB: Corsair, Razer, Logitech, SteelSeries, ASUS Aura and
  hundreds more).
- **Window and full screen.** At startup it can resize the window to fit, maximize it or go
  full screen. In full screen, indicators appear at the bottom of the screen, lined up with
  your physical fingers, showing which finger to use.

| Full screen | Settings | Statistics |
|---|---|---|
| ![Full screen](docs/screenshots/tam-ekran.png) | ![Settings](docs/screenshots/ayarlar.png) | ![Statistics](docs/screenshots/istatistik.png) |

## Installation

All you need is Python 3.9 or later. It is developed and tested on Linux and should also work
on macOS and other POSIX systems. It does not run natively on Windows, because the standard
library there has no `curses`; WSL works.

**With pipx (recommended):**

```sh
pipx install git+https://github.com/lckt0/harfiyen
```

**With pip:**

```sh
python3 -m pip install --user git+https://github.com/lckt0/harfiyen
```

**Arch Linux:** build a package with `paketleme/arch/PKGBUILD` (it downloads the archive of the
`v<version>` tag on GitHub). The PKGBUILD produces two packages: `harfiyen` (the terminal and
desktop interfaces, with their launchers) and the optional `harfiyen-mola` (see below).

```sh
cd paketleme/arch && makepkg -si
```

**Without installing:** the app is a single file, so you can just download and run it.

```sh
curl -O https://raw.githubusercontent.com/lckt0/harfiyen/main/harfiyen.py
python3 harfiyen.py
```

**Desktop launcher (for pip/pipx installs):**

```sh
install -Dm644 paketleme/harfiyen.desktop ~/.local/share/applications/harfiyen.desktop
```

The desktop app and Harfiyen Mola have a few extra steps of their own; see
[Desktop app](#desktop-app) and [Harfiyen Mola](#harfiyen-mola-optional).

## Usage

```sh
harfiyen                    # continue where you left off
harfiyen --ac istatistik    # open a window at startup: ayarlar (settings), istatistik (statistics),
                            #   yardim (help), menu, mod (practice mode)
harfiyen --pencere 10       # mastery window for this session only
harfiyen --temalar          # list themes and file paths
harfiyen --sifirla          # reset all progress
```

Progress can also be reset from inside the app: Settings (F2) → Data → "Reset progress". In the
dialog you can reset only the active profile (practice language + keyboard layout) or
everything (all profiles, XP, level, badges and the daily streak); the previous record is
backed up to `progress.json.yedek`.

Type the line on screen. If you press a wrong key, the cursor does not move and waits for the
right one; that character is counted as one error. The finger to use is shown both in the
message line and on the keyboard.

| Key | Action |
|---|---|
| Esc | menu |
| Ctrl-C | ask to quit (a second Ctrl-C quits) |
| Tab | new line |
| F1 | help |
| F2 | settings |
| F3 | toggle the error heat map |
| F4 | statistics |
| F5 / F6 | smaller / larger text |
| F7 | keyboard size |
| F8 | practice mode |
| F11 | toggle full screen |

With the mouse you can click the buttons in the top bar, the mode chip, the letter chips
(letter details), the setting arrows and the ✕ button of each window. Menus and info windows
close when you click outside them.

## Desktop app

Besides the terminal version there is a desktop interface drawn with Qt Quick:
`harfiyen-masaustu`. It uses the same core, progress file, settings and themes, and picks up
where you left off in the terminal.

![Desktop app](docs/screenshots/masaustu.png)

- **Focus card.** The line to type is shown in large text on a card in the middle, with the
  next line dimmed below it. The caret slides from letter to letter; on a wrong key the card
  shakes slightly and the key turns red on the keyboard. Under the card is a 4+4 finger strip:
  the next finger lifts up.
- **Top bar.** Speed, accuracy and score of the last line (with the change from the previous
  one), level and XP; below them, letter chips underlined by confidence and the daily goal.
- **Keyboard.** Unlocked letters are lightly tinted in their finger color; the key to press
  rises in the accent color, and if Shift is needed the Shift on the opposite hand is
  outlined. If the window is too short, the keyboard hides itself.
- **Zen mode (F9).** Only the text and the finger strip remain.
- **Letter confidence panel (F4).** Per-letter confidence bars and a speed chart of recent
  rounds.
- **Four modes (F8)**, speed test results (with a new record badge), and a menu (Esc).

| Zen mode | Light theme and letter panel | Speed test |
|---|---|---|
| ![Zen](docs/screenshots/masaustu-zen.png) | ![Light theme](docs/screenshots/masaustu-gunduz.png) | ![Speed test](docs/screenshots/masaustu-test.png) |

Shortcuts: **Tab** skip the line · **Esc** menu · **F4** letter panel · **F8** mode ·
**F9** zen · **F11** full screen · **Ctrl+Q** quit.

Installation: PySide6 (6.5+) is required. The font is JetBrains Mono (falling back to the
system monospace font).

```sh
pipx install "harfiyen[masaustu] @ git+https://github.com/lckt0/harfiyen"
install -Dm644 paketleme/harfiyen-masaustu.desktop ~/.local/share/applications/harfiyen-masaustu.desktop
```

On Arch, the `pyside6` and `ttf-jetbrains-mono` packages are enough; it also runs straight from
the repository with `python3 -m harfiyen_masaustu`. View preferences (zen, panel, line length)
are stored in `~/.config/harfiyen/masaustu.json`. Do not run the terminal and desktop versions
at the same time: both write to the same progress file (the desktop app warns you if this
happens).

## Harfiyen Mola (optional)

*Mola* means "break". While media is playing (say, while you watch a series), it puts a
10-word touch typing drill on top of the screen every 10 minutes. It pauses whatever is
playing the moment it appears, and when you finish typing (or skip with Esc) it resumes only
the media it paused itself. The words come from Harfiyen's lesson mode, and the keystrokes are
recorded in your Harfiyen progress. The source is in `mola/`.

| Drill | New record |
|---|---|
| ![Harfiyen Mola](docs/screenshots/mola.png) | ![New record](docs/screenshots/mola-rekor.png) |

- **Watch timer.** Accumulates MPRIS playback time. Paused time is not counted, but it does not
  clear what has accumulated either; seeking and pauses of a few seconds do not disturb the
  timer. If nothing plays for longer than `ara_sifirla_dk`, the timer starts over. The state is
  only read on the `PropertiesChanged` signal and when a player appears or goes away; the
  process does not wake up while waiting.
- **Window.** QML + LayerShellQt on the `overlay` layer (above full-screen video), with
  `exclusive` keyboard focus. Colors come from the theme selected in Harfiyen. In the 4+4
  strip under the card, the finger for the next letter lifts up.
- **Words.** Only unlocked letters, weighted toward weak ones. If Harfiyen itself is running,
  nothing is written to the progress file.
- **Record.** The WPM of each round is compared with your best break round; if you beat it, a
  "NEW RECORD" badge appears together with the difference from the previous best. Rounds
  below `rekor_en_az_dogruluk` accuracy do not count as records. The record is stored in
  `~/.local/share/harfiyen/mola-rekor.json`.
- **Media.** Any player that supports MPRIS (D-Bus): browsers, VLC, Spotify and so on. mpv
  needs `mpv-mpris`. It does not appear while the screen is locked.

**Requirements.** A Wayland session with a compositor that supports layer-shell (KDE Plasma,
Sway, Hyprland, etc.), PySide6, dbus-python and the QML module of LayerShellQt. These three
must come from system packages: the PySide6 wheel from pip cannot load the system's
LayerShellQt plugin.

```sh
sudo pacman -S pyside6 python-dbus layer-shell-qt ttf-jetbrains-mono    # Arch
```

On other distributions, install the equivalent packages (PySide6 QtQuick and QtDBus,
dbus-python, LayerShellQt for Qt 6).

**Installation (Arch).** Install the `harfiyen-mola` package as well with `makepkg -si`, then
enable the service for your user:

```sh
systemctl --user enable --now harfiyen-mola
```

**Installation (pipx).** Install with `--system-site-packages` so it can see the system
packages; the systemd user service and the launcher are copied from the repository:

```sh
pipx install --system-site-packages git+https://github.com/lckt0/harfiyen
git clone https://github.com/lckt0/harfiyen && cd harfiyen
mkdir -p ~/.config/systemd/user
sed 's|/usr/bin/harfiyen-mola|%h/.local/bin/harfiyen-mola|' mola/paketleme/harfiyen-mola.service \
    > ~/.config/systemd/user/harfiyen-mola.service
mkdir -p ~/.local/share/applications
sed "s|^Exec=harfiyen-mola|Exec=$HOME/.local/bin/harfiyen-mola|" mola/paketleme/harfiyen-mola.desktop \
    > ~/.local/share/applications/harfiyen-mola.desktop
systemctl --user daemon-reload
systemctl --user enable --now harfiyen-mola
```

If you installed with pip (`python3 -m pip install --user ...`), the paths are the same.

**Usage.** The service waits in the background. **Harfiyen Mola** in the application menu
(`harfiyen-mola --ac`) shows a drill right away: if the service is running it sends it
`SIGUSR1` (which also resets the timer), otherwise it opens a one-off drill. To try it by hand:
`harfiyen-mola --simdi --her-zaman` ("now", "always").

**Settings** live in `~/.config/harfiyen/mola.json` (created on first run):

| Key | Default | Meaning |
|---|---|---|
| `aralik_dk` | 10 | Show a drill after this many minutes of media playback |
| `ara_sifirla_dk` | 5 | If nothing plays for longer than this, the timer starts over |
| `kelime` | 10 | Number of words to type (text longer than 40 characters is wrapped at word boundaries) |
| `parmak_goster` | false | Show the finger for the next letter under the text (e.g. "Right index finger") |
| `haric_oynaticilar` | ["kdeconnect"] | MPRIS players whose names contain these strings are ignored |
| `ilerlemeye_kaydet` | true | Record keystrokes in your Harfiyen progress |
| `sonuc_suresi_sn` | 1.6 | How long the result stays on screen, in seconds |
| `rekor_en_az_dogruluk` | 90 | Rounds below this accuracy (%) do not count as records |

After changing them: `systemctl --user restart harfiyen-mola`

## Settings

Settings are stored in `~/.config/harfiyen/ayarlar.json`; the same settings can be changed in
the app with F2. Unknown or invalid values fall back to the default with a warning.

| Key | Values | Description |
|---|---|---|
| `tema` | `siyah`, `gece`, `gunduz`, `toprak`, `kontrast`, `terminal` or your own theme | color theme (black, night, day, earth, high contrast, terminal) |
| `arayuz` | `tr`, `en` | interface language |
| `yazi_boyutu` | `kucuk`, `normal`, `buyuk`, `dev` | practice line size (small, normal, large, huge) |
| `klavye_boyutu` | `otomatik_k`, `otomatik_uzun`, `gizli`, `kompakt`, `orta`, `buyuk` | key height (automatic, automatic tall, hidden, compact, medium, large) |
| `tus_stili` | `derinlik`, `duz`, `yuzen` | bottom edge of the keys (depth, flat, floating) |
| `tus_kenar` | `1`, `4`, `8`, `12`, `16` | edge height (in eighths of a row) |
| `klavye_gorunumu` | `parmak`, `isi` | finger colors or error heat map |
| `sonraki_satir`, `harf_paneli` | `true`, `false` | next line preview, letter confidence panel |
| `yazi_parmak` | `true`, `false` | finger indicator strip right under the text (finger to use, direction and letter) |
| `klavye` | `tr-q`, `tr-f`, `us` | keyboard layout |
| `fiziksel` | `iso`, `ansi`, `ansi102` | physical layout |
| `numpad` | `true`, `false` | numeric keypad |
| `dil` | `tr`, `en` | practice language |
| `ustalik_penceresi` | 5–50 | number of recent attempts considered for mastery |
| `ustalik_olcutu` | `dogruluk`, `dogruluk_hiz` | mastery criterion (accuracy, accuracy + speed) |
| `hedef_hiz` | 10–150 | target speed (WPM: five-character words per minute) |
| `buyuk_harf`, `noktalama`, `rakamlar` | `true`, `false` | add capitals, punctuation, numbers to practice lines |
| `gunluk_hedef_dk` | 0–240 | daily goal (minutes, 0 = off) |
| `test_suresi_sn` | 15–300 | speed test length (seconds) |
| `acilis_boyutu` | `dokunma`, `yeterli`, `kapla`, `tam_ekran` | window at startup (leave as is, enlarge to fit, maximize, full screen) |
| `gosterge` | `kapali`, `otomatik`, `her_zaman` | finger indicators (off, in full screen, always) |
| `gosterge_kaydirma_mm`, `gosterge_olcek` | mm, % | fine-tuning of the indicator position |
| `tus_araligi_mm`, `ekran_genisligi_mm` | mm (0 = automatic) | physical measurements (key pitch, screen width) |
| `fare` | `true`, `false` | mouse support |
| `rgb_isik` | `kapali`, `openrgb` | key lighting (off, OpenRGB) |
| `rgb_zemin` | `kapali`, `soluk`, `parmak` | other keys: off, dim white, or unlocked letters in finger colors |
| `rgb_parlaklik` | 10–100 | lighting brightness (%) |
| `rgb_adres` | `host:port` | OpenRGB SDK server (file only; default `127.0.0.1:6742`) |

<details>
<summary>Key styles and edge heights</summary>

From top to bottom: depth ⅛ row, depth ½ row (default), depth 1½ rows, flat, floating.

![Key styles](docs/screenshots/tus-stilleri.png)

</details>

## Themes

Put your own theme as a JSON file in `~/.config/harfiyen/temalar/`; the file name is the theme
ID. With `miras` ("inherit") you can base it on another theme and only write the fields you
want to change. An annotated `ornek.json` ("example") is created on first run.

```json
{
  "ad": "Benim temam",
  "miras": "gece",
  "vurgu": "#ff8fab",
  "tus_karisim": 0.5,
  "parmak": { "serce": "#b197fc", "isaret": "#8ce99a" }
}
```

Colors can be `#rrggbb`, `#rgb`, an xterm color number from 0 to 255, a name such as `red`, or
`null` (the terminal's own color). The fields are `ad` (name), `zemin` (background), `yuzey`
(surface), `yazi` (text), `soluk` (dim text), `cizgi` (lines), `baslik` (headings), `vurgu`
(accent), `vurgu_yazi` (text on accent), `dogru` (correct), `hata` (error), `hata_yazi` (text on
error), `uyari` (warning), `tus_yazi` (key labels), `ust_zemin` and `ust_yazi` (top bar
background and text), `golge` (shadow), and under `parmak` (fingers): `serce` (little),
`yuzuk` (ring), `orta` (middle), `isaret` (index), `basparmak` (thumb). The optional
`tus_karisim` (0–1) sets how much of the finger color goes into the key fill, and `tus_notr`
sets the fill of non-letter keys.

Because terminals draw with a 256-color palette, colors are rounded to the nearest palette
color, in a way that preserves the hue.

## Key lighting (OpenRGB)

If your keyboard supports per-key RGB lighting, Harfiyen lights up the key you need to press
on the keyboard itself: the target key in the theme's accent color, the Shift on the opposite
hand at half brightness when needed, and a wrong key briefly in red. Optionally, the unlocked
letters glow dimly in their finger colors. On exit, the keyboard's previous lighting and
effect are restored.

Harfiyen controls the lights through the SDK server of [OpenRGB](https://openrgb.org), so a
single method covers hundreds of brands and no extra dependency is needed.

1. Install OpenRGB (Arch: `pacman -S openrgb`) and make sure its udev rules are installed.
2. Start the server from the **SDK Server** tab in OpenRGB, or run OpenRGB with
   `openrgb --server --startminimized`.
3. In Harfiyen, choose **Settings → Keyboard lighting → Key lighting: OpenRGB**. The `RGB` chip
   in the top bar shows the connection (green: connected, red: could not connect; it retries
   every 15 seconds).

Keys are mapped by physical position, not by character: `ş` on Turkish Q sits where `;` is on
the US layout, whatever is printed on your keycap. Keyboards with only zone lighting are not
supported.

<details>
<summary>LED colors read back from the OpenRGB server</summary>

Real LED colors read from OpenRGB's test keyboard while Harfiyen is running: a capital letter
target with the opposite Shift, a wrong key, and the lighting restored after exit.

![Key lighting](docs/screenshots/tus-aydinlatmasi.png)

</details>

## Terminal compatibility

Harfiyen is not tied to any particular terminal. For terminal-specific features it tries the
standard way first, then a desktop-specific fallback, and if neither is available the app
switches to a compact layout.

- **Window size and full screen:** on KDE Plasma through a KWin script, whatever the terminal;
  on other desktops through xterm escape codes (`CSI 8/9/10 t`). Support for these codes
  varies between terminals: Konsole resizes the window, for example, while ghostty 1.3 ignores
  them.
- **Finger indicators:** the physical width of the screen is read from EDID; on KDE the window
  position comes from KWin. Elsewhere, set `gosterge` to `her_zaman` and align them with the
  fine-tuning settings.
- **Minimum size:** 72×22. The layout grows on its own in larger windows.

## Files

| Path | Contents |
|---|---|
| `~/.config/harfiyen/ayarlar.json` | settings |
| `~/.config/harfiyen/temalar/*.json` | your own themes |
| `~/.config/harfiyen/metinler/*.txt` | texts for free text mode |
| `~/.local/share/harfiyen/progress.json` | progress, statistics, badges |
| `~/.local/share/harfiyen/progress.json.yedek` | the record before the last in-app reset |
| `~/.config/harfiyen/mola.json` | Harfiyen Mola settings |
| `~/.local/share/harfiyen/mola-rekor.json` | Harfiyen Mola record |

`XDG_CONFIG_HOME` and `XDG_DATA_HOME` are respected.

## Uninstallation

If Harfiyen Mola is enabled, stop its service first:

```sh
systemctl --user disable --now harfiyen-mola
```

### Arch Linux (package)

```sh
sudo pacman -Rns harfiyen-mola harfiyen      # or just: sudo pacman -Rns harfiyen
```

### pipx / pip

```sh
pipx uninstall harfiyen                      # or: python3 -m pip uninstall harfiyen
rm -f ~/.local/share/applications/harfiyen.desktop \
      ~/.local/share/applications/harfiyen-masaustu.desktop \
      ~/.local/share/applications/harfiyen-mola.desktop \
      ~/.config/systemd/user/harfiyen-mola.service
systemctl --user daemon-reload
```

### Single file

Delete the `harfiyen.py` you downloaded.

### Settings and progress (optional)

Harfiyen does not change any system settings. The KWin script used for resizing the window
is loaded only while it runs, and the keyboard's own lighting is restored on exit. To delete
your progress, settings, themes and texts as well:

```sh
rm -r ~/.config/harfiyen ~/.local/share/harfiyen
```

## Development

```sh
python3 harfiyen.py                                # run directly
python3 -m harfiyen_masaustu                       # desktop app
python3 -m unittest discover -s tests -t . -v      # tests (the desktop tests need PySide6)
python3 -m unittest discover -s mola/tests -v      # Harfiyen Mola tests (PySide6, dbus-python)
PYTHONPATH=mola python3 -m harfiyen_mola --simdi --her-zaman --kaydetme   # try Mola from the repository
# render the desktop app to a PNG without opening a window (docs, visual checks):
QT_QPA_PLATFORM=offscreen python3 -m harfiyen_masaustu --goruntu ekran.png --zen
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details and [CHANGELOG.md](CHANGELOG.md) for release
notes.

## License

[MIT](LICENSE.md)
