import path from 'path';
import { execSync } from 'child_process';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { fileURLToPath } from 'url';
import { visualizer } from 'rollup-plugin-visualizer';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Get the application version using the same logic as version.py.
 *
 * Priority: SHUSAI_VERSION env > git describe > fallback.
 */
function getAppVersion(): string {
  if (process.env.SHUSAI_VERSION) return process.env.SHUSAI_VERSION;
  try {
    const raw = execSync('git describe --tags --long --always', {
      encoding: 'utf-8',
      timeout: 5000,
    }).trim();

    // Parse "v1.2.3-5-ga1b2c3d" format
    const match = raw.match(/^(.+?)-(\d+)-g([a-f0-9]+)$/);
    if (match) {
      const [, tag, commits, hash] = match;
      return commits === '0' ? tag : `${tag}-dev.${commits}+${hash}`;
    }

    // No tags — just a commit hash
    return `v0.0.0-dev+${raw}`;
  } catch {
    return 'v0.0.0-dev+unknown';
  }
}

/**
 * Vite plugin that injects the app version into the service worker.
 *
 * Uses a source-level transform (enforce: 'pre') to guarantee the
 * replacement happens regardless of how vite-plugin-pwa processes
 * the SW file in dev vs production builds.
 */
function swVersionPlugin(): Plugin {
  const version = getAppVersion();
  return {
    name: 'sw-version',
    enforce: 'pre',
    transform(code, id) {
      if (id.endsWith('/sw.ts') || id.endsWith('/sw.js')) {
        return code.replace(
          '__SW_BUILD_VERSION__',
          JSON.stringify(version),
        );
      }
    },
  };
}

export default defineConfig({
  plugins: [
    swVersionPlugin(),
    react(),
    // PWA support (Issue #114)
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      registerType: 'autoUpdate',
      includeAssets: [
        'favicon.svg',
        'favicon.ico',
        'favicon-192.png',
        'apple-touch-icon.png',
        'icons/*.png',
      ],
      manifest: {
        name: 'ShutterSense.ai',
        short_name: 'ShutterSense',
        description: 'Capture. Process. Analyze. Professional photo collection management.',
        theme_color: '#09090b',
        background_color: '#09090b',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: '/icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: '/icons/maskable-icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'maskable',
          },
          {
            src: '/icons/maskable-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
      },
      devOptions: {
        enabled: true,
        type: 'module',
      },
    }),
    // Bundle analyzer - generates stats.html after build
    visualizer({
      filename: './dist/stats.html',
      open: false, // Set to true to auto-open in browser
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Enable WebSocket proxying
        ws: true,
        // Suppress EPIPE errors on WebSocket proxy (happens during page reload/HMR)
        configure: (proxy) => {
          proxy.on('error', (err) => {
            if ((err as NodeJS.ErrnoException).code !== 'EPIPE') {
              console.error('Proxy error:', err)
            }
          })
        },
      },
    },
  },
  build: {
    // Output directory
    outDir: 'dist',
    // Generate sourcemaps for production debugging
    sourcemap: false,
    // Chunk size warning limit (500 KB)
    chunkSizeWarningLimit: 500,
    // Rollup options for optimization
    rollupOptions: {
      output: {
        // Manual chunk splitting for better caching
        manualChunks: {
          // Vendor chunks
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'radix-vendor': [
            '@radix-ui/react-dialog',
            '@radix-ui/react-select',
            '@radix-ui/react-tabs',
            '@radix-ui/react-tooltip',
            '@radix-ui/react-checkbox',
            '@radix-ui/react-label',
            '@radix-ui/react-slot',
          ],
          'form-vendor': ['react-hook-form', 'zod', '@hookform/resolvers'],
          'utils-vendor': ['axios', 'clsx', 'tailwind-merge', 'class-variance-authority'],
        },
        // Asset file naming
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name?.split('.') || [];
          const ext = info[info.length - 1];
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext)) {
            return `assets/images/[name]-[hash][extname]`;
          } else if (/woff|woff2|eot|ttf|otf/i.test(ext)) {
            return `assets/fonts/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },
        // JS chunk naming
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
      },
    },
    // Minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.logs in production
        drop_debugger: true,
      },
    },
  },
});
