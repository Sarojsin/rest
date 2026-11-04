/**
 * Production build for the Super Admin console.
 *
 * `vite.config.ts` builds only the tenant app (`index.html`). This config builds
 * only `admin.html` into `dist-admin`, served from the root of the admin origin.
 * Local development does not use this config: the shared Vite dev server serves
 * the admin entry at `/admin` (see the middleware in `vite.config.ts`).
 */
import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const appRoot = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = fileURLToPath(new URL("../..", import.meta.url));
const sharedClient = fileURLToPath(new URL("../../packages/api-client/index.ts", import.meta.url));

/**
 * CSP skeleton (plan 06 §8.12). `connect-src` is narrowed to the API origin and
 * never widened to `*`. The platform domain is deliberately not hard-coded
 * (PA-ADR-011): it comes from the deployment environment.
 */
function contentSecurityPolicy(apiOrigin: string): string {
  const connectSrc = ["'self'", apiOrigin].filter(Boolean).join(" ");
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    `connect-src ${connectSrc}`,
    "img-src 'self' data:",
    "font-src 'self' data:",
    "style-src 'self' 'unsafe-inline'",
    "script-src 'self'",
  ].join("; ");
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, appRoot, "");
  const apiOrigin = (env.VITE_PLATFORM_API_URL ?? "").replace(/\/+$/, "");
  const declaredEnv = (env.VITE_PLATFORM_ENV ?? "").toLowerCase();

  if (!apiOrigin) {
    if (declaredEnv === "production") {
      throw new Error(
        "VITE_PLATFORM_API_URL must be set for a production admin build so CSP connect-src can be narrowed to the API origin."
      );
    }
    // A local/staging build may legitimately run same-origin behind a proxy.
    console.warn(
      "[admin build] VITE_PLATFORM_API_URL is empty; CSP connect-src is limited to 'self'."
    );
  }

  return {
    root: appRoot,
    // The admin app is served from the root of its own origin in production.
    base: "/",
    plugins: [react()],
    resolve: {
      alias: {
        "@rest/api-client": sharedClient,
      },
    },
    server: {
      // `npm run dev:admin` is a convenience; normal local dev uses /admin on
      // the shared server, which proxies /api from the same origin.
      host: "0.0.0.0",
      port: 5174,
      fs: { allow: [repoRoot] },
    },
    preview: {
      host: "0.0.0.0",
      port: 5174,
      headers: {
        "Content-Security-Policy": contentSecurityPolicy(apiOrigin),
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Cache-Control": "no-store",
      },
    },
    build: {
      outDir: "dist-admin",
      emptyOutDir: true,
      // Never ship the tenant document in the admin bundle.
      rollupOptions: {
        input: fileURLToPath(new URL("admin.html", import.meta.url)),
      },
    },
  };
});
