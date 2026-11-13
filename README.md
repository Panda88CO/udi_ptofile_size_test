# ProfileSizeTest

# ProfileSizeTest

A developer diagnostic plugin for eisy / PG3x. It measures how large a **dynamic JSON profile** `polyglot.updateJsonProfile()` will accept, by sending synthetic profiles of increasing size and reporting where updates start to fail.

Ported from the standalone test at https://github.com/Panda88CO/udi-yolink/tree/profile-size-test/profile_size_test and reshaped into a normal Controller plugin (no `PG3INIT` juggling, no static `profile/` folder).

## WARNING - run on a test system
Each test pushes extra `NODE_nnn` nodedefs and `*_n` editors into this plugin's profile. `updateJsonProfile` adds/replaces by `id`, so later sweep steps overwrite earlier ids, but the profile can still end up holding far more than the one payload under test. A rejected or oversized profile may leave the Admin Console with unresolved labels or blank node panels. Delete/uninstall the plugin to clean up (not verified to purge everything pushed).

## What you get
* Controller node **Profile Size Test** (`ST` is managed by PG3) with the commands **Run Size Sweep** and **Run Two-Tier Test**.
* Child node **Test Results** with: `ST` = result (Not Run / All Passed / Boundary Found / All Failed), `MIN_FAIL_KB` (smallest failing payload), `MAX_PASS_KB` (largest passing payload), `TIME` (last run).
* A full ASCII report in the plugin log after every run.

## Configuration (custom parameters)
| Key | Default | Meaning |
|---|---|---|
| `mode` | `sweep` | `sweep`, `test` (one small + one large), or `file` |
| `sweep_start` / `sweep_end` / `sweep_step` | 20 / 100 / 10 | KB range for sweep mode (max 2048) |
| `small_kb` / `large_kb` | 15 / 90 | sizes for test mode |
| `profile_file` | empty | JSON file (top-level `editors` + `nodedefs`) for file mode; relative paths resolve inside `persist/` |
| `include_st` | `true` | give each synthetic nodedef a valid `ST` property; `false` reproduces the original generator output |
| `run_on_start` | `false` | run automatically each time the plugin starts |

Saving a changed configuration after startup re-runs the test with the new values. Invalid values fall back to defaults and raise a notice.

## Differences from the original script
* Command ids are `RUN_SWEEP` / `RUN_TWOTIER` instead of `DON` / `DOF`; results live on a child node (`ST`, `MIN_FAIL_KB`, `MAX_PASS_KB`, `TIME`) instead of `GV1`-`GV3` on the controller, because the Controller template only declares `ST`.
* Synthetic nodedefs get an `ST` property by default (`include_st`), because the profile validator used by this tool set rejects non-controller nodedefs without one - a failure could otherwise reflect structure rather than size.
* The first run is gated behind `run_on_start`/commands rather than firing as soon as custom parameters arrive.
* Payload size is tracked incrementally (the original re-serialized the whole payload every step).
* Reports a "non-monotonic" warning if a larger payload passes than the smallest failure.
* No CLI mode: this is plugin-only.

## License Notice

This plugin's development referenced the following source(s), whose license is not on the standard permissive allowlist. Review their license terms before relying on or redistributing this plugin:

- [0.1.4 dynamic profile fails on PG3x 3.4.25/IoX 6.1.2 · Issue #2 · Panda88CO/udi-Kidde · GitHub](https://github.com/Panda88CO/udi-Kidde/issues/2) -- license: unknown

See LICENSE.md for full third-party attribution.
