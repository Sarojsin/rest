import { useEffect, useState } from "react";
import { getToken } from "../lib/api";

/**
 * Renders an authenticated image endpoint (payment QR codes) as an object URL.
 * A plain <img src> cannot send the bearer token, so the preview would 401.
 */
export function AuthedImage({
  src,
  alt,
  className,
  width,
  height,
}: {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let created: string | null = null;
    setObjectUrl(null);
    setFailed(false);

    async function load() {
      try {
        const response = await fetch(src, {
          headers: { Authorization: `Bearer ${getToken() ?? ""}` },
          cache: "no-store",
        });
        if (!response.ok) throw new Error("image request failed");
        const blob = await response.blob();
        created = URL.createObjectURL(blob);
        if (!cancelled) setObjectUrl(created);
      } catch {
        if (!cancelled) setFailed(true);
      }
    }

    void load();
    return () => {
      cancelled = true;
      if (created) URL.revokeObjectURL(created);
    };
  }, [src]);

  if (failed) {
    return (
      <span className={className} role="img" aria-label={`${alt} (could not be loaded)`}>
        ⚠
      </span>
    );
  }

  if (!objectUrl) {
    return <span className={className} aria-hidden="true" />;
  }

  return <img src={objectUrl} alt={alt} className={className} width={width} height={height} />;
}
