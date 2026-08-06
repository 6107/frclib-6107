# JetBrains / PyCharm Time-Tracking Plugins

A comparison of plugins that automatically measure time spent on a project, respect idle timeouts, break time down
per-project (and often per-task/branch/issue), expose an API or export path, are actively maintained, are free, **and
can consolidate data across multiple machines including periods with no network connectivity.**

## Evaluation criteria

| # | Criterion                                                                                                                                                                                                                    |
|---|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | Counts *active* time (typing, scrolling, editor focus, debugger, VCS actions).                                                                                                                                               |
| 2 | Configurable **idle timeout** – e.g. no keystroke/scroll for *N* minutes → stops the timer.                                                                                                                                  |
| 3 | Exports data (CSV / JSON / TSV / iCal / spreadsheet) for import into other tools.                                                                                                                                            |
| 4 | Programmatic **API** (REST / gRPC / local HTTP) to query the collected data.                                                                                                                                                 |
| 5 | Breaks time down **per-project**, and ideally **per-task / branch / changelist / issue**.                                                                                                                                    |
| 6 | **Free** – either fully free & open source, or a free tier that covers a single developer.                                                                                                                                   |
| 7 | **Actively maintained** – recent Marketplace releases, current JetBrains build-range support, responsive issue tracker, active upstream.                                                                                     |
| 8 | **Multi-machine + offline consolidation** – you code on a laptop, a desktop, and occasionally a plane. Time recorded while offline must survive, and all machines must roll up into one unified view without manual merging. |

> ⚠️ Marketplace release dates and version compatibility change frequently. Cross-check
> the plugin’s JetBrains Marketplace page and GitHub repo before adopting.

> ℹ️ **TakaTime** ([plugin 31861](https://plugins.jetbrains.com/plugin/31861-takatime))
> is included in this revision as an *emerging* open-source, self-hosted (BYODB
> MongoDB) alternative to WakaTime. It is philosophically similar to Wakapi but is
> new (repo created 2026-01-03), has a very small install base (~56 downloads at time
> of writing), is maintained by a single author, and does not yet document offline
> heartbeat queueing, a plugin REST API, or per-branch reporting. See the summary
> matrix and the TakaTime deep-dive below.

---

## Summary matrix

| Plugin                                                  | Active detection                                        | Idle timeout                                           | Export                                   | API                                                                                                     | Per-project                  | Per-task/branch                                        | Free tier                       | Maintenance                                                                                                                                                         | Multi-machine + offline                                                                                                                                                                                                                                       |
|---------------------------------------------------------|---------------------------------------------------------|--------------------------------------------------------|------------------------------------------|---------------------------------------------------------------------------------------------------------|------------------------------|--------------------------------------------------------|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **WakaTime** (cloud)                                    | ✅                                                      | ✅ default 15 min                                      | ✅ CSV, JSON                             | ✅ REST                                                                                                 | ✅                           | ✅ per branch/file/language                            | ✅ Free tier: rolling dashboard | 🟢 Excellent                                                                                                                                                        | 🟢 **Excellent** — CLI buffers heartbeats to a local SQLite when offline and flushes on reconnect; every machine posts to one account ⇒ automatic consolidation                                                                                               |
| **Wakapi** (self-hosted WakaTime backend)               | Same as WakaTime                                        | ✅                                                     | ✅ full DB dump                          | ✅ WakaTime-compatible REST                                                                             | ✅                           | ✅ per branch/file                                     | ✅ 100% free, open source       | 🟢 Excellent                                                                                                                                                        | 🟢 **Excellent** — same offline queueing as WakaTime; all machines point at one Wakapi URL ⇒ single unified view. Can be exposed via VPN/Tailscale for road use                                                                                               |
| **TakaTime** (self-hosted, BYODB MongoDB)               | ✅ typing, file focus, "smart heartbeat" pauses on idle | ✅ dynamic (documented but no exposed timeout key yet) | ⚠️ via `mongoexport` on your own MongoDB | ⚠️ no plugin-side REST API; you query MongoDB directly (or use the built-in TUI / GH-Action stats card) | ✅ per-project, per-language | ⚠️ per-branch/per-task **not documented** as of v2.2.6 | ✅ MIT, no accounts             | 🟡 **Fair / emerging** — created 2026-01, active weekly commits, but single maintainer, **~56 total Marketplace downloads**, 51 open issues vs 103 ★, bus-factor 1 | 🟡 **Partial** — cross-machine consolidation works (all machines point at one MongoDB), but **no documented offline heartbeat queue**; if MongoDB is unreachable the heartbeats' fate is unclear. Verify before relying on it for offline sessions            |
| **ActivityWatch (core)**                                | ✅ system-wide + editor watchers                        | ✅ AFK watcher                                         | ✅ JSON/CSV via query API                | ✅ Local REST on `:5600`                                                                                | ✅                           | ⚠️ requires custom AQL for branch                      | ✅ 100% free, open source       | 🟢 Excellent (core)                                                                                                                                                 | 🔴 **Weak by default** — data lives in a per-machine SQLite; no first-class multi-host sync. Workarounds: Syncthing on the bucket dir, `aw-sync-*` experiments, or export/import JSON per machine. All are DIY                                                |
| **ActivityWatch JetBrains watcher** (`aw-watcher-idea`) | Reports project/file to local AW                        | Inherits AFK                                           | Via AW                                   | Via AW                                                                                                  | ✅                           | ⚠️                                                     | ✅                              | 🟡 Fair (community)                                                                                                                                                 | 🔴 Same as core AW                                                                                                                                                                                                                                            |
| **Code Time** (software.com)                            | ✅                                                      | ✅ built-in                                            | ⚠️ CSV via dashboard                     | ⚠️ limited public API                                                                                   | ✅                           | ⚠️ per-project only                                    | ✅ (account required)           | 🔴 Poor / uncertain                                                                                                                                                 | 🟡 Cloud consolidation works when online, but offline queueing and cross-machine behavior are poorly documented and vendor continuity is a risk                                                                                                               |
| **Clockify**                                            | ⚠️ desktop app auto-timer; plugin = manual timer        | ✅ (desktop)                                           | ✅ CSV/PDF/Excel                         | ✅ REST                                                                                                 | ✅                           | ✅ per task/tag                                        | ✅ Free tier: unlimited users   | 🟢 Good (vendor)                                                                                                                                                    | 🟡 **Good when online.** Desktop app buffers offline entries; the **JetBrains plugin itself needs a live connection** to start/stop timers, so pure-IDE offline capture is limited. All machines using the same account ⇒ automatic consolidation once online |
| **Toggl Track**                                         | ⚠️ desktop auto-tracker; plugin = timer                 | ✅ (desktop)                                           | ✅ CSV/PDF                               | ✅ REST v9                                                                                              | ✅                           | ✅ per task/tag                                        | ✅ Free tier: ≤5 users          | 🟡 Mixed (community plugin)                                                                                                                                         | 🟡 Same pattern as Clockify — desktop app has offline queueing, IDE plugin does not. Cloud account consolidates across machines                                                                                                                               |
| **TimeCamp**                                            | ✅ desktop auto-tracker                                 | ✅                                                     | ✅ CSV/PDF/Excel                         | ✅ REST                                                                                                 | ✅                           | ✅ per task                                            | ✅ Free “Solo” tier             | 🟢 Good                                                                                                                                                             | 🟡 Same as Clockify/Toggl                                                                                                                                                                                                                                     |
| **TMetric**                                             | ✅ desktop auto-tracker; plugin timers                  | ✅                                                     | ✅ CSV/Excel                             | ✅ REST                                                                                                 | ✅                           | ✅ per task/issue                                      | ⚠️ Free tier limited            | 🟢 Good                                                                                                                                                             | 🟡 Same as Clockify/Toggl                                                                                                                                                                                                                                     |
| **Tempo Timesheets / Jira integration**                 | Manual + Jira-linked                                    | ✅                                                     | ✅                                       | ✅ REST                                                                                                 | ✅                           | ✅ per Jira issue                                      | ❌ Paid                         | 🟢 Excellent (enterprise)                                                                                                                                           | 🟢 Cloud-consolidated                                                                                                                                                                                                                                         |

Legend: ✅ full · ⚠️ partial · ❌ not supported · 🟢 excellent/good · 🟡 fair/mixed · 🔴 poor/at-risk

---

## Why WakaTime + Wakapi wins on “multi-machine + offline”

The single biggest differentiator once you add criterion #8 is **offline heartbeat queueing**. The WakaTime CLI
(`wakatime-cli`, invoked by the JetBrains plugin) writes every heartbeat first to a **local SQLite queue file**
(typically
`~/.wakatime/offline_heartbeats.bdb`). If the API POST fails — because you are on a plane, in a lab with no route, or
the Wakapi VPN is down — the entries stay in that queue and are flushed the next time the CLI can reach the server.
Because every machine posts to the **same account/API URL**, all your laptops/desktops merge into one dashboard
automatically. There is no per-machine export/import step.

Consolidation model:

```
laptop  ─┐
desktop ─┼──► wakatime-cli ──► offline SQLite queue ──► POST ──► Wakapi (self-host) ──► single dashboard + REST
plane   ─┘                          (drains on reconnect)
```

Practical setup for a road warrior:

1. Deploy Wakapi (Docker image, single Go binary) on a home server or small VM.
2. Expose it either publicly (HTTPS + reverse proxy) or over a mesh VPN (Tailscale/WireGuard). Mesh is preferred — no
   public exposure required.
3. On every machine, install the WakaTime IntelliJ plugin and set
   `~/.wakatime.cfg` to point at the Wakapi URL with the same API key per user (or one key per machine if you want to
   attribute time by host).
4. Do nothing else. Offline periods self-heal.

---

## Recommended picks (with multi-machine + offline in mind)

### 1. WakaTime + self-hosted Wakapi — best overall

- Meets **all eight** criteria.
- Multi-machine consolidation is automatic; offline periods are transparently queued.
- Fully free, open source, healthy upstream (`wakatime/jetbrains-wakatime`,
  `muety/wakapi`).
- Branch-level breakdown ⇒ per-task reports when branches follow `NUPC-*` naming.
- Recommended for `nupc_proto`.

### 2. Clockify (fallback if you must have a hosted vendor)

- Vendor-maintained IDE plugin, generous free tier, mature REST API, cloud-native ⇒ multi-machine consolidation is
  inherent to the account.
- Caveat: the **IDE plugin itself** relies on the network; the automatic offline-capable tracker lives in the **desktop
  companion app**. If you code offline often, run the desktop app alongside PyCharm — the IDE plugin alone will miss
  offline sessions.

### 3. ActivityWatch — *only* if you accept DIY sync

- Strongest system-wide detail (measures browser/terminal/docs too, not just the IDE).
- **Not recommended if multi-machine consolidation is a hard requirement.** There is no officially supported sync; you
  would rely on Syncthing on the bucket directory, the experimental `aw-sync-http` fork, or a nightly export/import
  cron. All work, none are as seamless as WakaTime’s built-in queue.
- Fine as a **complement** to WakaTime on a single primary machine, to see time in non-IDE tools.

### 4. TakaTime — emerging self-hosted alternative (worth watching, not yet a replacement)

- **Marketplace:** [`31861-takatime`](https://plugins.jetbrains.com/plugin/31861-takatime), xmlId
  `com.takatime.jetbrains`, latest **v2.2.6**, MIT, free, compatible with **build 252.0+** (PyCharm 2025.2 and newer,
  all JetBrains IDE families).
- **Model:** open-source WakaTime alternative. Go core binary shared across the JetBrains, VS Code, and Neovim plugins.
  **BYODB** — you run your own MongoDB and the plugin writes telemetry to it. In-IDE **TUI dashboard** and a
  GitHub-Actions stats-card generator that reads from the same MongoDB.
- **Detection & idle:** heartbeat model similar to WakaTime; the v2.2.4 changelog introduced a *dynamic heartbeat
  calculator* that pauses during inactivity. The exact idle-timeout key is not documented in the README.
- **Per-project / per-task:** per-project and per-language are documented; **per-branch / per-task is not called out**
  in the README as of v2.2.6.
- **Export:** whatever `mongoexport` on your MongoDB gives you (JSON/CSV) — no first-class CSV export UI.
- **API:** no plugin-provided REST endpoint. Consumers query MongoDB directly.
- **Multi-machine + offline:** pointing all machines at the same MongoDB gives automatic cross-machine consolidation.
  **No offline heartbeat queue is documented**, so behavior when MongoDB is unreachable (plane, lab without VPN) is
  unverified. This is the single biggest gap versus Wakapi.
- **Maintenance signal:** GitHub repo created **2026-01-03**; single maintainer (`Rtarun3606k`); active weekly commits;
  frequent releases (three versions in one day recently, fixing a listener-lifecycle bug); **103 ★ / 24 forks / 51 open
  issues / 3 watchers / ~56 total Marketplace downloads** at the time of writing. Translation: promising, actively
  developed, but very young, tiny install base, bus-factor 1.
- **Verdict:** currently a **complementary/experimental choice**, not a replacement for Wakapi. It matches Wakapi
  philosophically (self-hosted, privacy-first, open-source, one DB across all machines) but has not yet reached parity
  on documented offline queueing, REST API, per-branch reporting, or maintenance breadth. Re-evaluate every few months.

### Not recommended when offline/multi-machine matters

- **Code Time** — cloud-only, opaque offline handling, weak vendor signal.
- **Toggl / TimeCamp / TMetric plugins** — same offline caveat as Clockify but with either community-maintained IDE
  plugins (Toggl) or more restrictive free tiers (TMetric). Choose Clockify if you want that model.

---

## Feature deep-dive

### Idle / activity detection

| Plugin                                | What counts as “active”                                                         | How it stops                                                          |
|---------------------------------------|---------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| WakaTime                              | Any keystroke, save, file switch, debug tick, VCS action inside a JetBrains IDE | No heartbeat for `timeout` minutes ⇒ interval closes, not counted     |
| ActivityWatch                         | Editor focused **AND** AFK watcher reports “not-afk”                            | AFK watcher flips to `afk` after N seconds of no keyboard/mouse input |
| Code Time                             | Keystrokes + file focus                                                         | Automatic ~15 min                                                     |
| Clockify / Toggl / TimeCamp / TMetric | Timer running + desktop app’s idle detector                                     | Prompts user or discards idle on resume                               |

### Per-task / per-changelist strategies

1. **Git branch = task** — WakaTime and ActivityWatch both capture the branch; naming branches `NUPC-123-fix-rm` yields
   per-issue reports.
2. **JetBrains Tasks & Contexts** — built-in *Tools → Tasks & Contexts* opens/closes tasks that map to Jira/GitHub
   issues and auto-create branches; combined with WakaTime you get per-issue time via branch.
3. **Manual timer bound to an issue** — Clockify/Toggl/TMetric plugins let you attach the timer to a Jira/GitHub issue
   directly.

### Offline behaviour (criterion #8) in detail

| Plugin                                | Where offline data lives                                    | How it merges when online                                         | Cross-machine merge                                             |
|---------------------------------------|-------------------------------------------------------------|-------------------------------------------------------------------|-----------------------------------------------------------------|
| WakaTime / Wakapi                     | `~/.wakatime/offline_heartbeats.bdb` (SQLite)               | CLI drains queue in the background                                | Automatic — one account, N machines                             |
| TakaTime                              | Not documented in README (needs source/issue-tracker check) | Presumed direct MongoDB write; behavior on unreachable DB unclear | Automatic when online (one MongoDB, N machines)                 |
| ActivityWatch                         | Per-machine SQLite in `~/.local/share/activitywatch/`       | Nothing — data stays local                                        | **Manual** — Syncthing / export-import / experimental sync fork |
| Code Time                             | Limited local buffer                                        | Undocumented                                                      | Cloud account (when online)                                     |
| Clockify / Toggl / TimeCamp / TMetric | Desktop app buffers; **IDE plugin does not**                | Desktop app pushes on reconnect                                   | Cloud account (when online)                                     |
| Tempo / Jira                          | N/A (manual entries)                                        | Manual save                                                       | Cloud (Jira)                                                    |

### Export formats

| Plugin         | CSV                  | JSON                 | Excel/PDF | Raw DB dump          |
|----------------|----------------------|----------------------|-----------|----------------------|
| WakaTime cloud | ✅                   | ✅ (API)             | ❌        | ❌ (paid tier only)  |
| Wakapi         | ✅                   | ✅                   | ❌        | ✅ (SQLite/Postgres) |
| TakaTime       | ⚠️ via `mongoexport` | ⚠️ via `mongoexport` | ❌        | ✅ (MongoDB)         |
| ActivityWatch  | ✅ (via `aw-client`) | ✅                   | ❌        | ✅ (SQLite/Peewee)   |
| Clockify       | ✅                   | ✅ (API)             | ✅        | ❌                   |
| Toggl          | ✅                   | ✅ (API)             | ✅        | ❌                   |
| Code Time      | ✅ (dashboard)       | ⚠️                   | ❌        | ❌                   |

### APIs at a glance

```text
WakaTime / Wakapi     GET /api/v1/users/current/summaries?start=&end=&project=
TakaTime              (no plugin REST API — query your MongoDB directly)
ActivityWatch         POST /api/0/query    (AQL body)
Clockify              GET /api/v1/workspaces/{wsId}/user/{userId}/time-entries
Toggl Track           GET /api/v9/me/time_entries?start_date=&end_date=
TimeCamp              GET /third_party/api/entries?from=&to=
TMetric               GET /api/accounts/{accountId}/timeentries
```

### How to vet a plugin before installing

1. **JetBrains Marketplace page** — check “Last update” and “Compatible build”. If the upper build bound is older than
   your PyCharm build number, expect breakage.
2. **GitHub repo** — inspect *Releases*, latest commit date on `main`, open-vs-closed issue ratio, and whether recent
   issues are answered within days.
3. **Ownership** — vendor-owned plugins (Clockify, TimeCamp, TMetric, WakaTime) keep pace with new IntelliJ builds more
   reliably than community plugins (Toggl,
   `aw-watcher-idea`).
4. **Backend continuity** — for cloud-only services consider what happens to your history if the vendor changes plans.
   Self-hosted options (Wakapi, ActivityWatch)
   sidestep this entirely.
5. **Offline test** — kill the network, work for 20 minutes, restore the network, and verify the last 20 minutes show up
   in your dashboard. This is the single best check for criterion #8.

---

## Recommendation for this workspace (`nupc_proto`)

For a developer who works on multiple machines, occasionally offline, and wants **free, fine-grained, exportable,
well-maintained, seamlessly-consolidated** time data with a real API:

1. **Primary: self-hosted Wakapi + WakaTime PyCharm plugin.**
    - Zero-cost, unlimited retention, WakaTime-compatible REST API.
    - Offline heartbeats are queued locally and drained on reconnect on every machine.
    - All machines POST to one Wakapi ⇒ single, always-up-to-date view.
    - Expose Wakapi over Tailscale/WireGuard so no public endpoint is required.
2. **Complementary (optional): ActivityWatch on your primary workstation** to see time spent outside the IDE. Do **not**
   rely on it for multi-machine roll-ups.
3. **Team-facing / billable reports (optional): Clockify** — vendor-maintained plugin, generous free tier, mature API.
   Run the Clockify desktop app alongside PyCharm on any machine that needs offline capture.
4. **Watch (do not adopt yet): TakaTime.** Same self-hosted-BYODB philosophy as Wakapi, but as of August 2026 it is too
   young, too thinly maintained, and lacks documented offline queueing / REST API / per-branch reporting. Re-evaluate in
   6–12 months.

---

## Reference links

- WakaTime plugin: <https://plugins.jetbrains.com/plugin/7425-wakatime>
- WakaTime plugin source: <https://github.com/wakatime/jetbrains-wakatime>
- WakaTime CLI (offline queue): <https://github.com/wakatime/wakatime-cli>
- Wakapi (self-hosted, MIT): <https://github.com/muety/wakapi>
- TakaTime plugin: <https://plugins.jetbrains.com/plugin/31861-takatime>
- TakaTime source: <https://github.com/Rtarun3606k/TakaTime>
- ActivityWatch: <https://activitywatch.net/>
- ActivityWatch JetBrains watcher: <https://github.com/2e3s/aw-watcher-idea>
- ActivityWatch sync discussions: <https://github.com/ActivityWatch/activitywatch/issues/35>
- Code Time: <https://plugins.jetbrains.com/plugin/10687-code-time>
- Clockify plugin: <https://plugins.jetbrains.com/plugin/12256-clockify-time-tracker>
- Toggl Track plugin: <https://plugins.jetbrains.com/plugin/9807-toggl-integration>
- TimeCamp plugin: <https://plugins.jetbrains.com/plugin/11976-timecamp>
- TMetric plugin: <https://plugins.jetbrains.com/plugin/9540-tmetric>

