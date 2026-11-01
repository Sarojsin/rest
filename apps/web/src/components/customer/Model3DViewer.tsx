import { useEffect, useRef, useState } from "react";
import type { MenuItem } from "../../lib/api";

/**
 * Loads the heavy <model-viewer> custom element only when a guest opens a 3D
 * view. The poster image stays underneath until the model fires `load`, so the
 * stage is never blank. If the model cannot be displayed (no WebGL, blocked
 * network, bad GLB) we fall back to the photographed dish instead of an empty
 * canvas.
 */
export function Model3DViewer({
  item,
  onLoaded,
  fallbackImage,
}: {
  item: MenuItem;
  onLoaded?: () => void;
  fallbackImage?: string;
}) {
  const viewerRef = useRef<HTMLElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [item.id, item.model_path]);

  useEffect(() => {
    void import("@google/model-viewer");
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    const handleLoad = () => onLoaded?.();
    const handleError = () => setFailed(true);
    viewer.addEventListener("load", handleLoad);
    viewer.addEventListener("error", handleError);
    return () => {
      viewer.removeEventListener("load", handleLoad);
      viewer.removeEventListener("error", handleError);
    };
  }, [item.id, item.model_path, onLoaded, failed]);

  if (failed) {
    return (
      <div className="m-model-fallback" role="status">
        {fallbackImage ? <img src={fallbackImage} alt="" aria-hidden="true" /> : null}
        <p>3D preview is not available on this device — showing the dish photo instead.</p>
      </div>
    );
  }

  return (
    <model-viewer
      ref={viewerRef}
      src={item.model_path}
      alt={`3D view of ${item.name}`}
      camera-controls
      auto-rotate
      touch-action="pan-y"
      shadow-intensity="1"
      exposure="1"
      interaction-prompt="auto"
      style={{ width: "100%", height: "100%" }}
    />
  );
}
