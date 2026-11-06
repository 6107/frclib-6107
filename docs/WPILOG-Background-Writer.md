# WPILOG writing: switch to `DataLogBackgroundWriter`

This document describes the change made to pykit's WPILOG receiver in `lib_6107`
(`frclib-6107` repo, `src/lib_6107/pykit/wpilog/wpilogwriter.py`), how it was tested, how the
behavior differs from before, and what remains to make it solid.

## Why

`WPILOGWriter.put_table()` runs once per robot cycle on the robot loop thread (`RobotThread`).
It used `wpiutil.DataLogWriter`, which is a **synchronous** native writer:

- `append*()` only buffers records in memory.
- `Flush()` is the only place data reaches the file, and it writes on the **calling thread**.
- `BufferFull()` just returns `false`; nothing is written when the buffer fills.
- It has no thread of its own (verified from the exported symbols in `libwpiutil.so` and the
  upstream `datalog/src/main/native/cpp/DataLogWriter.cpp`).

`put_table()` called `self.log.flush()` at the end of every cycle, so every disk write happened
inside the 20 ms loop. On a RoboRIO writing to a USB drive or flash, a slow write directly
becomes a loop overrun.

## What changed

All edits are in `wpilogwriter.py` (plus its test file).

| Area | Before | After |
|---|---|---|
| Class | `DataLogWriter(full_path, header)` | `DataLogBackgroundWriter(folder, filename, FLUSH_PERIOD, header)` |
| Per-cycle flush | `self.log.flush()` at end of `put_table()` | Removed. The native writer thread flushes every `FLUSH_PERIOD` (0.25 s) |
| Auto-rename | `os.rename()` on the open file | `self.log.setFilename(new_name)` (the writer owns the file and renames it on its thread) |
| Shutdown (`end()`) | `flush()` then `stop()` | `isOpen = False`, `flush()`, then `del self.log` (see below) |
| Constant | none | `FLUSH_PERIOD = 0.25` (seconds, module level) |

Tests (`lib_6107/tests/pykit/wpilog/test_wpilogwriter.py`):

- The two existing tests patched `wpilogwriter.DataLogWriter`; they now patch
  `DataLogBackgroundWriter`.
- Added `test_wpilogwriter_end_drains_all_records_to_disk`: writes 500 cycles through a real
  `WPILOGWriter`, calls `end()`, reads the file back with `DataLogReader`, and asserts the file
  is valid and holds every record (one timestamp + one counter per cycle).

## How the behavior differs

- **Threading.** Appends still happen on the robot thread (they are in-memory buffer writes), but
  all file I/O now happens on a native C++ thread inside `libwpiutil.so`, outside the GIL and the
  robot loop. In the sim this thread shows up as an additional native thread of the process.
- **Latency of data on disk.** Previously data hit the file every cycle (20 ms). Now it can lag by
  up to `FLUSH_PERIOD` (0.25 s). After an abrupt process death (SIGKILL, power loss, crash that
  skips `end()`), up to about 0.25 s of data can be lost.
- **`stop()` discards data.** `DataLogBackgroundWriter.stop()` only stops appending and does *not*
  drain buffered records. Experiments with a 1,000-record log:

  | Shutdown sequence | Records on disk |
  |---|---|
  | `stop()` only | 0 (file size 0) |
  | `flush()` then `stop()` immediately | partial / racy |
  | `flush()`, wait, `stop()` | all |
  | `del writer` (destructor) | all |

  `flush()` on the background writer is **asynchronous**. The destructor sets the shutdown flag,
  forces a final flush, and **joins** the writer thread, which makes it the only synchronous
  drain available from Python. `end()` therefore releases the object instead of calling `stop()`.
  After `end()`, `self.log` no longer exists; `isOpen = False` makes `put_table()` a no-op.
- **Back-pressure behavior.** If appends outrun the writer thread, upstream's
  `BufferFull()` logs "outgoing buffers exceeded threshold, pausing logging" and **pauses
  logging until `resume()` is called**. The old synchronous writer never paused (it just grew
  memory). In a synthetic burst test (50,000 appends in a tight loop, far above real robot
  rates) one run lost about 11,000 records this way.

## How it was verified

1. Ran the sim with `.github/skills/robotpy/bin/sim-unix.sh`. The log file was created, renamed to
   `pykit_<timestamp>.wpilog` by the auto-rename path, and grew continuously with no leftover
   temp files.
2. Stopped the sim and read the log back with `DataLogReader`: valid file, about 53k records.
3. Standalone experiments on the shutdown semantics (table above).
4. Unit tests: all 3 in `test_wpilogwriter.py` pass, repeated 5 times with no flakiness.

Not verified (see below): a graceful full-robot shutdown, behavior on a real RoboRIO, and any
loop-time improvement.

## Remaining work to make this solid

1. **Measure the benefit.** Compare loop overrun counts and `put_table()` time before and after
   (for example with the `pyspy` skill or the existing timing stats). A loop-overrun message was
   seen in the sim after the change, but no baseline was compared. The Python diff/append loop in
   `put_table()` still runs on the robot thread and holds the GIL; only file I/O moved.
2. **Handle the "paused" state.** Detect when the writer has paused logging (watch the console
   message or compare record counts), call `self.log.resume()`, and surface an alert/telemetry
   counter so log loss is not silent. Consider tuning `FLUSH_PERIOD` (smaller = less buffered
   data and less chance of hitting the threshold; larger = fewer disk writes).
3. **Make `end()` robust.** `del self.log` raises `AttributeError` if `end()` is called twice or
   after a failed `start()` (the constructor error path returns before `self.log` exists). Guard
   with `isOpen` or a `getattr`.
4. **Exercise the real shutdown path.** `SIGINT`/`SIGTERM` did not trigger `end()` on the GUI sim.
   Verify `Logger.end()` -> `WPILOGWriter.end()` runs on a real `endCompetition()`/robot
   teardown and that other receivers (NT4) are not left depending on the file. Consider an
   `atexit` safety net.
5. **Test on hardware.** Confirm behavior and USB (`/U/logs`) write performance on a RoboRIO,
   including free-space handling (the native writer stops logging on low disk space).
6. **More unit tests.** Cover the auto-rename path through `setFilename()` (simulation currently
   skips auto-rename when a filename is given), the double-`end()` case, and the abrupt-stop
   data-loss window.
7. **Housekeeping.** `ruff` was not available in the robot venv, so lint was not run. The change
   is in the `frclib-6107` repository (through the `lib_6107` link), so it must be committed
   there, not in `2026-Rebuilt`. `git` also warns about CRLF line endings in that repo's
   working tree; this is unrelated to the change.
8. **Known unrelated quirk.** `WPILOGWriter(filename, path)` ignores `path` in simulation
   (it always uses `pyLogs`). Left as is.
