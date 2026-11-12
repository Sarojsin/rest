# Plan: Add notification sound on browser push

## Problem
When a push notification arrives while the staff tab is open, `App.tsx` (lines 62-68) shows a silent visual toast. There is **no audio playback anywhere** in the frontend:
- No audio asset files exist (`apps/web/public` has no mp3/wav/ogg)
- No `new Audio()` / `.play()` calls exist anywhere
- No browser `Notification` API sound config
- The `setupForegroundListener` callback (App.tsx:63-66) only calls `setPush({title, body})`

Browsers also block audio autoplay without a prior user gesture, so the plan must handle that gracefully.

## Goal
Play a short notification sound when a push notification arrives while the staff tab is open, alongside the existing toast. Sound should be optional and respect user preference and browser autoplay policy.

## Files affected
- `apps/web/public/notification.mp3` (or .wav) — new short notification sound asset
- `apps/web/src/App.tsx` — play sound in the `setupForegroundListener` callback, alongside `setPush`
- `apps/web/src/lib/fcm.ts` — no changes needed (listener already exists)
- Optional: a settings toggle to enable/disable sound (out of scope for v1; can gate behind a localStorage key)

## Implementation steps
1. Add a short notification sound file to `apps/web/public/notification.mp3` (public so it's served at `/notification.mp3`)
2. In `App.tsx`:
   - Create an `Audio` object pointing to `/notification.mp3`
   - In the foreground-listener callback, after `setPush(...)`, attempt `audio.play()`
   - Wrap `play()` in try/catch; on `NotAllowedError` (autoplay blocked), log silently and do not crash — the toast still shows
   - Optional: remember a `soundEnabled` localStorage flag; if false, skip play
3. Verify typecheck passes (`tsc --noEmit`) — no new errors
4. Manually verify: trigger a push while tab is open → toast appears + sound plays (on user-interacted tab)

## Verification
- `tsc --noEmit` on `apps/web` reports no new errors
- No runtime console error when sound is blocked by browser policy
- Toast still appears even when sound is blocked

## Out of scope
- Persistent sound-on/off setting in database/settings
- Custom per-restaurant notification sounds
- Background/tab-closed push sound (handled by OS/browser push, not this app)
- Service-worker background message sound (separate concern)

## Open question
Which sound file should be used? If no suitable mp3 exists in the repo, I can add a tiny generated notification beep, or the user can supply one.