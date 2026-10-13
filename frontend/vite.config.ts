import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  const devHost = env.VITE_DEV_HOST || '0.0.0.0';
  const devPort = parseInt(env.VITE_DEV_PORT || '5173', 10);
  const backendTarget = env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000';
  const wsTarget = backendTarget.replace(/^http/, 'ws');

  return {
    plugins: [react()],
    server: {
      host: devHost,
      port: devPort,
      allowedHosts:['dtpc'],
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: wsTarget,
          ws: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  };
});

