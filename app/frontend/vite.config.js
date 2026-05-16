import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000';

  return {
    plugins: [react()],
    base: '/',
    build: {
      outDir: 'dist',
      emptyOutDir: true,
    },
    server: {
      port: Number(env.VITE_PORT) || 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/admin': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/media': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
      headers: {
        "Content-Security-Policy": "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;",
      },
    },
  };
});
