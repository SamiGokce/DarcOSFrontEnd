import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

/** Put stylesheet before JS so CSS is applied before React paints. */
function cssBeforeJs() {
  return {
    name: "css-before-js",
    transformIndexHtml(html) {
      const linkTag = html.match(/<link rel="stylesheet"[^>]*>/)?.[0];
      const scriptTag = html.match(/<script type="module"[^>]*><\/script>/)?.[0];
      if (!linkTag || !scriptTag) return html;

      let out = html.replace(linkTag, "").replace(scriptTag, "");
      out = out.replace("</head>", `    ${linkTag}\n    ${scriptTag}\n  </head>`);
      return out;
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react(), cssBeforeJs()],
    base: "/",
    build: {
      outDir: "dist",
      emptyOutDir: true,
      cssCodeSplit: false,
    },
    server: {
      port: Number(env.VITE_PORT) || 5173,
      strictPort: true,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/admin": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/media": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
      headers: {
        "Content-Security-Policy":
          "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;",
      },
    },
  };
});
