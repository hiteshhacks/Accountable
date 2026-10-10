import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// In development the frontend calls /api/*, which Vite forwards to the VYOM FastAPI server.
// Override the target with VYOM_API_TARGET, or set VITE_API_BASE to call the API directly.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const apiTarget = env.VYOM_API_TARGET || 'http://127.0.0.1:8000';
  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/api/, ''),
        },
      },
    },
  };
});
