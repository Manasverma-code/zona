# Zona — Product Requirements Document (PRD)

> **One-liner:** Zona is a location-gated, anonymous-first social feed that only exists inside your campus. Step outside the GPS boundary and the app goes blank.

**Version:** 0.2 (MVP / 30-day pilot)
**Status:** Backend v0.2 complete + verified (API tests green). Expo app scaffolded with the full MVP loop. Remaining: real campus polygon, pilot, metrics.

---

## 1. Problem

Campus life happens inside a physical space, but current social apps are global and permanent.
That makes them boring (the feed doesn't know where you are) and unsafe (posts follow you forever).

**Insight:** scarcity creates demand. A feed you can only see *while physically on campus* is
intrinsically exclusive, intrinsically ephemeral, and intrinsically interesting.

## 2. Solution

Zona = **a secret layer over your campus.**

- The app only unlocks when your GPS position is inside the campus polygon.
- Posts live for **24 hours**, then disappear forever.
- You are **anonymous** (auto-generated handle per week, no signup email).
- **Server rooms** — Discord-style, student-created rooms ("Hostel Wing B", "Freshers 2026") on top of 6 seeded defaults (Food, Lost & Found, Classes, Rumors, Events, Misc).
- Leaving campus = losing the feed + losing your streak. That loss is the product.

## 3. Goals & Non-Goals

| Goals (MVP) | Non-Goals (not in v0.1) |
|---|---|
| Prove the core loop: enter campus → open app → post/react → leave | Comments / threads / DMs |
| Geofence gate that is server-verified (spoof-resistant) | In-app chat |
| Ephemeral feed (24h expiry) | Public web version |
| Anonymous handles with no email signup | Profiles, followers, discover |
| Streaks that die when you don't post inside | Notifications, push |
| Report + auto-hide moderation | Campus Wi-Fi dependence (never) |
| Student-created server rooms (Discord-style) | Server admins / roles / invite-only rooms |
| Per-server feeds (rail UI, long-press manage/report) | Server search, pinned posts |

## 4. Target Users

- **Primary:** students on the 45-acre campus (hostel residents especially — they live inside the zone).
- **Secondary:** faculty/staff on campus (same gate, same feed).
- **Explicitly excluded:** anyone outside the GPS boundary, bots, alumni watching from afar.

## 5. Core User Journey

```
┌──────────────┐   walk onto campus   ┌─────────────────┐
│ Blank screen │ ───────────────────► │ Feed unlocks    │
│ "You're      │                      │ streak ticking  │
│ outside."    │                      └────────┬────────┘
└──────────────┘                               │ post / react
        ▲                                      ▼
        │                              ┌─────────────────┐
        └──────── leave campus ◄───────│ 24h posts       │
                              expire   └─────────────────┘
```

1. Student installs app → device gets an anonymous identity (no account).
2. Student walks into campus → app flips from blank to live feed.
3. Student picks a room (Food, Lost & Found, their wing's room…) and scrolls today's posts.
4. Student posts (≤ 300 chars) or reacts (🔥😂🙌👀) — or makes their own room.
5. Post dies in 24h. Streak += 1 for today.
6. Student leaves campus → blank state returns. Curiosity pulls them back tomorrow.

## 6. Feature Spec (MVP)

### 6.1 The Gate (P0)
- Server-side point-in-polygon check using a **campus polygon** (not a circle) stored in config.
- Client sends: `lat`, `lon`, GPS `fix timestamp`, and **hashed WiFi BSSID fingerprints**
  (second proof — only collectable on campus, hard to fake remotely).
- **Pilot note:** BSSID proof is designed but OFF (`ZONA_REQUIRE_BSSID_PROOF=0`) — Expo Go has no
  BSSID API. The app's `location.ts collectBssids()` hook is ready; flip on when the app is built
  with a wifi dev-build plugin.
- Server rejects any write (post/reaction/streak) from outside the polygon.
- Blank state UX: dark screen, one line — *"You're outside the zone. Nothing to see."*
- GPS fallback: if accuracy > 50 m, the app shows "moving to a better spot" instead of a hard reject.

### 6.2 Ephemeral Feed (P0)
- Posts expire **24 hours** after creation (server-enforced: expiry stored + lazy cleanup).
- Feed = newest-first, filtered to unexpired, **per server room** (`GET /v1/feed?server_id=`).
- No feed outside the polygon — hard 403, same blank-screen message.

### 6.3 Anonymous Identity (P0)
- Client sends a random `device_id` (generated once, stored on device).
- Server mints a **weekly random handle** like `Violet-384` (adjective + number) from that device id.
- No email, no password, no phone number. Reinstall = new identity.

### 6.4 Streaks (P1)
- Posting (or opening while inside) on consecutive days increments a streak.
- Miss a day while on campus → streak resets. Off-campus days are excused automatically.

### 6.5 Reactions (P0)
- Emoji-only reactions: 🔥 😂 🙌 👀 ❤️
- One reaction per device per post (can change, no spamming).

### 6.6 Moderation (P0)
- Report button on every post.
- **5 reports → post auto-hidden** (soft delete).
- **5 reports → server room auto-hidden** (same rule, `reports` table points at posts OR servers).
- `moderator` flag on device for batch-level human mods.

### 6.7 Rate Limits / Abuse (P0)
- Max 5 posts / device / hour. 1 post per 60 s minimum gap.
- Server rooms: max **1 room / device / hour**, max **5 rooms / device** total.
- Server-side validation everywhere. Never trust the client.

### 6.8 Server Rooms (P0 — Discord-style)
- 6 default rooms seeded on first boot: `Food`, `Lost & Found`, `Classes`, `Rumors`, `Events`, `Misc`.
- Students create rooms (name ≤ 40 chars, optional description ≤ 160) — gated + BSSID-proofed like posts.
- Every post lives in exactly one room. Room feeds via `GET /v1/feed?server_id=N`.
- Creator can soft-delete their own room (`DELETE /v1/servers/{id}`, server-verified creator match).
- Default rooms have no creator → undeletable by users.
- Long-press a room in the app rail → report or delete (creator only).

## 7. Non-Functional Requirements

| Area | Requirement |
|---|---|
| **Spoof resistance** | All checks server-side; WiFi BSSID hash as second factor; short-lived tokens |
| **Battery** | No background GPS polling — gate checked on app-open + foreground refresh |
| **Privacy** | No email/phone; posts tied to device only; no IP logs beyond ops needs |
| **Scale (pilot)** | 5,000 devices, ~500 DAU, SQLite → Postgres at >1k posts/day |
| **Uptime** | Single VPS, 99% is fine for pilot |
| **Offline** | Blank state works without network; feed needs data (by design, mobile data only) |

## 8. Success Metrics (30-day pilot)

| Metric | Target |
|---|---|
| Opens on arrival (opens within 10 min of entering campus) | > 40% |
| Posts / active user / day | > 0.7 |
| D1 retention | > 35% |
| Day-30 streak survivors | > 20% of active users |
| Daily unique reactors | > 30% of DAU |
| Reports / 1,000 posts | < 5 (else moderation fails) |

**Kill criteria:** if DAU < 30 after 2 weeks of pilot, the feed value is missing — iterate on
rooms/content before scaling.

## 9. Architecture (Cloud-Only, No Campus Hardware)

```
[Expo RN app (app/)] --HTTPS--> [FastAPI server (server/) on VPS]
                                    │
                       ┌─────────┴──────────┐
                       │ Postgres/SQLite    │
                       │ (posts, devices)   │
                       └────────────────────┘
   Geofence = config polygon + BSSID hashes. No Wi-Fi needed. Mobile data only.
```

- **Backend:** Python FastAPI + SQLAlchemy (readable, type-checked, auto-docs at `/docs`).
- **DB:** SQLite for local dev → Postgres in prod (one `DATABASE_URL` swap).
- **App:** Expo / React Native TypeScript, one codebase, iOS + Android (`app/`).
  Auto-detects the backend host from the Expo dev server; override via `extra.apiUrl` in app.json.
- **Realtime:** WebSocket for live feed refresh (v0.2; polling every 15 s is fine for MVP).

## 10. Milestones

| Week | Deliverable | Status |
|---|---|---|
| 0–1 | Backend: gate + auth + ephemeral posts + reactions + streaks + server rooms | ✅ done, API-tested (46 checks) |
| 1–2 | App: blank state, server rail, feed, composer, room creation, gate polling (Expo) | ✅ done, `tsc` + Metro bundle clean |
| 2–3 | Spoof-proofing (BSSID dev build), 20-friend pilot, moderation tuning | ⬜ next — BSSID hook in `app/src/location.ts` |
| 3–4 | Metrics dashboard, room tuning, 30-day pilot launch | ⬜ next |

**Bugs found + fixed during verification:** geofence ray-casting had lat/lon axes swapped (gate
rejected everyone); naive/aware datetime crash on the 2nd post; report endpoint 500'd for users who
had reacted (report now lives in its own table); report auto-hide count was off-by-one (explicit
flush); emoji-in-header now percent-encoded end-to-end.

## 11. Open Questions

1. Which campus coordinate polygon? (Replace `campus polygon` in config before launch.)
2. iOS background GPS rules — confirm we never poll in background (battery + App Store review).
3. One image per post — keep in MVP or defer? (Deferred by default; text-only launches faster.)
4. BSSID proof needs a dev build — decide: Expo Go pilot (BSSID off) vs. dev build before the 20-friend pilot.
5. Room naming — allow duplicates or enforce unique names campus-wide?

## 12. Risks

| Risk | Mitigation |
|---|---|
| GPS accuracy indoors (10–50 m drift) | Tolerance buffer on polygon + BSSID proof + accuracy gate |
| Anonymous abuse / doxxing | Report + auto-hide, device reputation, mods per batch |
| Novelty wears off | Ephemerality + streaks make absence cost something |
| Campus admin concerns | No tracking history; delete-on-leave policy documented |
| Room spam (junk rooms drowning the rail) | 1 room/hour + 5 rooms/device caps; report → auto-hide at 5 |
| Geofence bug silently gates everyone out | The v0.2 axis-swap bug is fixed; add a `GET /v1/health`-style "am I inside?" debug screen before pilot |
