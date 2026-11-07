import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

const repoRoot = fileURLToPath(new URL("../..", import.meta.url));
const sharedClient = fileURLToPath(new URL("../../packages/api-client/index.ts", import.meta.url));

/**
 * Development convenience only (PA-ADR-003): the shared Vite server serves the
 * Super Admin entry at `/admin`. Production builds the admin app separately
 * with `vite.admin.config.ts` and serves it from its own origin.
 */
function platformAdminDevEntry(): Plugin {
  return {
    name: "platform-admin-dev-entry",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const url = req.url ?? "";
        const [pathname, query] = url.split("?");
        const isAdminPath = pathname === "/admin" || pathname.startsWith("/admin/");
        const acceptsHtml = String(req.headers.accept ?? "").includes("text/html");
        if (isAdminPath && acceptsHtml) {
          req.url = `/admin.html${query ? `?${query}` : ""}`;
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), platformAdminDevEntry()],
  resolve: {
    alias: {
      "@rest/api-client": sharedClient,
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: [".monkeycode-ai.live"],
    // The admin build writes to dist-admin inside this root; never watch it.
    watch: { ignored: ["**/dist-admin/**"] },
    // The shared client lives outside apps/web.
    fs: { allow: [repoRoot] },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
