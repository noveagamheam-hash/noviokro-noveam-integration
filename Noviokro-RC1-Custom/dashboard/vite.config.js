import {defineConfig} from 'vite';
// Native development uses loopback; Compose supplies its manager DNS name.
const target = process.env.NOVIOKRO_MANAGER_URL || 'http://127.0.0.1:8002';
export default defineConfig({server: {host: '127.0.0.1', proxy: {
  '/api': {target, changeOrigin: true},
  '/health': {target, changeOrigin: true},
}}});
