# Review fixes — 27 October 2026

Applies every item from the 22 October review on top of upstream `release/1.3` (3 commits after v1.3.0-rc2: #5054, #5062, #5067, merged cleanly). Built for ARM Release with toolchain v22 and checked with host tests. **Not tested on a physical Deluge.**

## Correctness

| ID | Fix | Where | Test |
| --- | --- | --- | --- |
| D1 | Plaits Morph has its own hybrid (additive) params `LOCAL_PLAITS_A/B_MORPH`, like Harmonics and Timbre. Modulation now opens Morph from any knob position. Old presets: the carrier-feedback value is copied on load (lossless, both give `0.5 + P/2^32` unmodulated) and cables to carrier feedback on a Plaits oscillator are retargeted to Morph. Carrier feedback is FM-only again. | `param.h`, `sound.cpp`, `patch_cable_set.cpp`, `voice.cpp`, `osc/source/plaits_morph.h` | `plaits/morph_probe.py`, `mdd_features/target_probe.py` |
| D2 | MDD route targets are saved by param file name (`mddRouteTargets`). V1/V2 numeric targets are migrated across the two inserted Morph params. Clip data is now `mddSnakeV3`. | `instrument_clip.cpp`, `codec.hpp` | `mdd/route_names_probe.py`, `mdd/codec_probe.cpp` |
| D3 | Unreadable MDD data no longer fails the whole song: the clip opens in Normal with default MDD settings. Unknown `mddBakedCustom` bits are masked. | `instrument_clip.cpp`, `controller.hpp` (`resetToDefault`) | `mdd/codec_probe.cpp` |
| D4 | MDD pad handling defers during SD card routines, like stock edit pads. | `instrument_clip_view.cpp` | `mdd/native_menu_probe.py` |
| D5 | One-Custom-per-destination is a UI rule (`Sound::mddCustomTargetTaken`) used by the patch source menu and MDD Map. It is no longer inside `maySourcePatchToParam()`, so `setupPatching()` never silently disables existing cables. | `sound.cpp`, `source_selection.cpp`, `mdd.cpp` | `mdd_features/target_probe.py`, `mdd/native_menu_probe.py` |
| D6 | All Map/Depth/Target access goes through a clamped `customIndex()`. | `mdd.cpp` | `mdd/native_menu_probe.py` |
| D7 | Shortcut range-edit permission uses `isGlobalPatchSource()`. | `sound_editor.cpp` | build |
| D8 | On a running switch back to Normal, rows with their own length are re-aligned to the live clip position and processed on that tick. | `instrument_clip.cpp` | `mdd/sync_probe.py` |
| D9 | MDD SCALE button and Song Key menu toggle scale mode keeping the stock grid's bottom note. | `instrument_clip.cpp` (`setScaleModeKeepingScroll`) | `mdd/scale_scroll_probe.py`, `mdd/scale_button_probe.py` |
| — | V3 files keep saved lane speeds on load (legacy files still normalise to 1/16 on first activation). | `instrument_clip.cpp` | `mdd/startup_probe.cpp` |

## Deluge integration and menus

| ID | Fix | Test |
| --- | --- | --- |
| U1 | BACK is Undo / SHIFT+BACK Redo in MDD view, as everywhere else. | `mdd/native_menu_probe.py` |
| U2 | SHIFT + main pad in MDD view opens the stock sound shortcut and never edits hidden notes. | `mdd/native_menu_probe.py` |
| U3 | Vertical encoder transposes Notes (SHIFT: octave); horizontal encoder rotates the selected lane's Shift. Neither touches the hidden clip. | build |
| U4 | Patch cable, automation and MDD Target lists name Plaits params "Osc1 Harmonics / Timbre / Morph" when the oscillator is Plaits. | build |
| U5 | Grid shows Notes, Gates, Velocity and the selected Custom as four 4×4 blocks with their own playheads; unreachable cells dimmed; one colour per Custom lane. | `mdd/grid_probe.py` |
| U6 | Sequencer / MDD Automation removed from the Note Row Editor. | build |
| U7 | Root/Scale page is titled "Song Key" ("Song Root", "Song Scale"). | `mdd/native_menu_probe.py` |
| U8 | MIDI clips: Map opens "Map to MIDI CC"; each Custom lane sends a CC (0–119), 7-bit, only on change. Saved in V3. | `mdd/playback_probe.py`, `mdd/native_menu_probe.py`, `mdd/codec_probe.cpp` |
| U9 | Legacy sound-level Snake Custom (unreachable menu, unused Plaits model overrides, per-Sound 404-byte config, 426-character attribute) removed. Old `snakeCustomV1/V2` attributes are skipped. Sources keep their file names (`snakeCustom1..4`); OLED shows "MDD Custom n". | `mdd_features/baked_source_probe.py` |
| U10 | Boot greeting is a Community Features toggle ("Boot Greeting", default on). | `startup/run.py` |

## Performance

| ID | Fix | Measured on host |
| --- | --- | --- |
| P1 | MDD schedules the transport only at the next lane step boundary or note-off instead of every tick; pending mode switches wait for the next 1/16 boundary. | Default 1/16: 32 events per bar instead of 96 (24 tpq) or 384 (96 tpq). Output identical to per-tick processing in 600 random configurations (`mdd/event_schedule_probe.py`). |
| P2 | One frame evaluation per processed tick. | — |
| P3 | Opt-in Plaits FM "Quality: Eco" per sound (2x instead of 4x oversampling, `[1 3 3 1]/8` decimator, same taming and feedback smoothing). Default High is bit-identical to before. | Eco ~0.52× host time at -O3; same pitch, level within 0.01 dB at timbre 0 (`plaits/eco_probe.cpp`). Not measured on ARM. |
| P4 | MDD 20 ms timer only runs while a pad is held or a switch is pending. | — |
| P5 | Playhead movement redraws only the four cell rows. | `mdd/grid_probe.py` |
| P6 | `Sound::updateSnakeCustom` returns after four integer reads for Sounds without MDD. | `mdd_features/baked_source_probe.py` |
| P7 | Per-Sound legacy config removed (~470 B each); per-clip `HeldNotes` 16→8 slots and 16-bit route targets. MDD data is only saved for clips that used MDD. Full lazy allocation of MDD state was not done (54 access sites; would need hardware testing). | ELF bss −1 056 B |

## Validation

- ARM Release build, toolchain v22: no new warnings (stock RWX linker warning only).
- Fork regression suites: `mdd` (20 PASS lines), `mdd_features` (5), `plaits` (9), `plaits/menu_probe`, `audio_audit`, `fx_menu` (8 groups), `startup`.
- Upstream spec tests (object_pool, pulse_rendering, rainfall, reverb, semver, starfield, string, tracking_allocator) and UnitTests pass when built 64-bit. The 32-bit memory tests and `scheduler_tests.cpp` (needs C++23 `<print>`) could not be built in this environment.
- clang-format 19 and Ruff format applied.

## Behaviour to check on the device

1. Load an older song with Plaits presets: Morph should sound the same; cables that went to Morph should still move it.
2. MDD at fast rates (1/64, 1/64T) and with Overlap: timing should be unchanged.
3. Switch MDD → Normal while playing a clip with different-length rows.
4. Plaits FM Eco on bright patches: decide by ear whether the CPU saving is worth it.
5. A heavy song with MDD on/off: compare the High CPU indicator and voice culling.
