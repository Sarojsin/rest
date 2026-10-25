import { useEffect, useState } from "react";

/**
 * A coarse clock for ticket ages. Fifteen seconds is fine for "12 min" labels
 * and avoids a render loop on a busy kitchen tablet.
 */
export function useNow(intervalMs = 15_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}
