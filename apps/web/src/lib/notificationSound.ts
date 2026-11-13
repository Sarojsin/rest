let audio: HTMLAudioElement | null = null;
let unlocked = false;

function getAudio(): HTMLAudioElement | null {
  if (typeof window === "undefined") return null;
  if (!audio) {
    audio = new Audio("/notification.wav");
    audio.preload = "auto";
  }
  return audio;
}

/**
 * Call once on a user gesture to satisfy browser autoplay policies.
 * Safe to call multiple times.
 */
export function unlockNotificationSound(): void {
  if (unlocked) return;
  const a = getAudio();
  if (!a) return;
  const prevMuted = a.muted;
  const prevVol = a.volume;
  a.muted = true;
  a.volume = 0;
  const p = a.play();
  if (p && typeof p.then === "function") {
    p.then(() => {
      a.pause();
      a.currentTime = 0;
      a.muted = prevMuted;
      a.volume = prevVol;
      unlocked = true;
    }).catch(() => {
      a.muted = prevMuted;
      a.volume = prevVol;
    });
  }
}

/** Play the notification sound (best-effort; no-op if blocked). */
export function playNotificationSound(): void {
  const a = getAudio();
  if (!a) return;
  try {
    a.currentTime = 0;
    const p = a.play();
    if (p && typeof p.catch === "function") p.catch(() => undefined);
  } catch {
    // ignore
  }
}