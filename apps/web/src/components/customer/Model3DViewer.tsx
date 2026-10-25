import { useEffect, useRef } from "react";
import type { MenuItem } from "../../lib/api";

/**
 * Loads the heavy <model-viewer> custom element only when a guest opens a 3D view.
 * The poster image stays underneath until the model fires `load`, so the stage is
 * never blank.
 */
export function Model3DViewer({ item, onLoaded }: { item: MenuItem; onLoaded?: () => void }) {
  const viewerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    void import("@google/model-viewer");
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    const handle = () => onLoaded?.();
    viewer.addEventListener("load", handle);
    return () => viewer.removeEventListener("load", handle);
  }, [item.id, item.model_path, onLoaded]);

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
