import type { DetailedHTMLProps, HTMLAttributes } from "react";

type ModelViewerAttributes = HTMLAttributes<HTMLElement> & {
  src?: string;
  alt?: string;
  poster?: string;
  "camera-controls"?: boolean | string;
  "auto-rotate"?: boolean | string;
  "disable-zoom"?: boolean | string;
  "touch-action"?: string;
  "shadow-intensity"?: string | number;
  exposure?: string | number;
  "interaction-prompt"?: "auto" | "none";
  "loading"?: "auto" | "eager" | "lazy";
  reveal?: "auto" | "interaction" | "manual";
};

declare global {
  namespace JSX {
    interface IntrinsicElements {
      "model-viewer": DetailedHTMLProps<ModelViewerAttributes, HTMLElement>;
    }
  }
}

export {};
