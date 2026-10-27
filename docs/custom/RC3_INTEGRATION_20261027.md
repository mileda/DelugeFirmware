# MDD Snake + Plaits on Deluge 1.3.0 RC3

The custom firmware now sits on upstream **v1.3.0-rc3** (`c0725ce5`, 26 October 2026), the latest released Community Firmware. All custom features and the [27 October review fixes](REVIEW_FIXES_20261027.md) are layered on top. Unofficial build; not tested on a physical Deluge.

## What RC3 brings over the previous base

28 upstream commits after RC2 + the three earlier `release/1.3` fixes, including: OLED/CV shared-bus handshake, OLED frame deduplication and skipped unchanged transfers, launch countdown fixes, analog delay performance, DX7 parameter shortcut overlay, automation undo memory fix, MIDI CC interpolation at fast tempo, String refcount underflow fix, audio track recording source fixes, looper overdub halving fix, kit sample stretching fix, saturating exp-param patch cable sums, and a two-level Shortcut Overlay setting (Off / Menu only / Menu + Clip).

Not in RC3 (and therefore not here): USB audio and the SD cluster pre-loading performance work. They are on upstream `main` for the next release.

## Rule for overlaps

Where a custom bug fix and an upstream fix address the same problem, the upstream solution is used. Review result:

| Custom change | Upstream RC3 | Result |
| --- | --- | --- |
| Song load applies saved reverb HPF | Unchanged upstream | Custom fix kept |
| `Submenu::drawPixelsForOled` before-begin iterator | Unchanged upstream | Custom fix kept |
| Granular setup before shutdown-wrap calculation | Unchanged upstream | Custom fix kept |
| SHIFT select-encoder acceleration in 32 bits | Unchanged upstream | Custom fix kept |
| Startup F4 failsafe cleanup | Unchanged upstream | Custom fix kept |
| OLED side scroller during playback | Upstream added skip-unchanged-transfer logic | Upstream logic kept, custom per-scroller opt-in layered on it |
| Sound editor greyout while MDD is shown | Upstream added shortcut-overlay greyout | Upstream check first, MDD rule after it |
| Community settings / strings | Upstream added overlay options | Both kept, Boot Greeting appended |
| Plaits Morph (hybrid param) | #5099 saturating cable sums | Upstream maths applies to Morph too; probe updated |

## Validation

- ARM Release build, `RELEASE_TYPE=rc`, toolchain v22; version string `1.3.0-rc-37bb6912f`. No new warnings.
- Fork suites: `mdd` 20 PASS, `mdd_features` 5, `plaits` 9 + menu probe, `audio_audit`, `fx_menu` 8 groups, `startup`.
- Upstream tests built 64-bit: 11/11 pass, including the new `OledHandshakeDriverTests` and `OledCVDriverTests`. Not built here: 32-bit `MemoryManagerTests` and `scheduler_tests.cpp` (toolchain limits of the build environment).

## Check on the device

Everything in the review-fix checklist, plus: OLED and CV outputs together (the RC3 shared-bus handshake), and MDD scrolling text while playing.
