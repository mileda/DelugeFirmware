# MDD Snake + Plaits — OLED firmware download

Unofficial custom firmware based on Deluge Community Firmware 1.3.0 RC3 (Derbyshire). This build targets the OLED interface. It has been compiled for ARM, but has not been tested on a physical Deluge. Treat it as an experimental build, not a stable official release.

## Download

[Download the firmware BIN](https://raw.githubusercontent.com/mileda/DelugeFirmware/main/firmware/deluge-mdd-plaits-oled-rc3-37bb6912.bin)

[Exact corresponding source](https://github.com/mileda/DelugeFirmware/tree/37bb6912fa5ae5a71a9ee85f8c26da2dfc032a08) · [Source ZIP](https://github.com/mileda/DelugeFirmware/archive/37bb6912fa5ae5a71a9ee85f8c26da2dfc032a08.zip) · [SHA256SUMS](SHA256SUMS) · [Build record](BUILD_INFO.json)

SHA-256: `ea4b619bae9411a20c8db2c84442246199fb4d39473a06617f4ea60d03e95d1e`

Earlier builds are no longer kept in this folder; they remain in the git history.

## Install

1. Back up your SD card, songs and presets before trying this custom firmware. Keep a known-working firmware available.
2. Download the `.bin` file itself; do not save the GitHub HTML page. Do not extract the BIN or rename it to ELF.
3. With the Deluge powered off, put the BIN in the top-level directory of its FAT32 SD card. Remove other firmware BIN files from that directory so only the intended update is present.
4. Insert the SD card. Hold **SHIFT** while powering on the Deluge.
5. Let the firmware update complete and the Deluge boot. Do not interrupt the update.

These steps follow the retained [upstream SD-card update guide](../website/src/content/docs/manual/device_overview/sd_card.mdx). To reinstall a known-working firmware, repeat the update procedure with its BIN. Custom song/preset compatibility across firmware versions is not guaranteed; keep the backups.

## Included

Base: upstream `v1.3.0-rc3` (26 October 2026). See [RC3 integration](../docs/custom/RC3_INTEGRATION_20261027.md).

Latest: all review fixes — Plaits Morph and FM Quality (Eco), four-block MDD grid, BACK = Undo, encoders, MIDI CC lanes, Song Key, event-driven MDD timing and MDD file format V3. See [review fixes](../docs/custom/REVIEW_FIXES_20261027.md). Songs saved with this build lose their MDD settings on older firmware; back up first.


Custom automation WRITE with atomic Undo/Redo, one Custom per destination, true Tie across loop boundaries, Legato and adjustable Overlap are included. See [new features and controls](../docs/custom/MDD_WRITE_TIES_20261012.md).

MDD clip sequencer, four Custom modulation lanes, Plaits FM/Waveshaping/Virtual Analog sources, Plaits optimization, all 15 selected custom changes, the upstream 1.3.0 RC2 fixes and retained reverb additions. See [RC2 integration and optimization notes](../docs/custom/RC2_INTEGRATION_20261020.md). See the [modification notice](../CUSTOM_CHANGES.md) and [audit](../docs/custom/CPU_AUDIT.md).

## License and authorship

Distributed under GPL-3.0-or-later as part of the combined Deluge firmware; see [LICENSE](../LICENSE). Original Synthstrom/community notices are preserved. The Plaits/stmlib subset by Emilie Gillet retains its MIT notices; see [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). This is not an official Synthstrom, Mutable Instruments or MDD Snake release.
