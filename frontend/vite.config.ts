import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import Components from 'unplugin-vue-components/vite'
import { PrimeVueResolver } from '@openvue/auto-import-resolver'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    // OpenVue components are imported on use, so a page only ships the
    // components it renders.
    Components({
      resolvers: [PrimeVueResolver()],
      dts: 'src/components.d.ts',
    }),
    // The service worker that makes Cuisine installable as an app and opens
    // it without a round trip. It precaches the app shell only (scripts,
    // styles, fonts, icons and index.html); everything below /api goes to
    // the network, so recipes and sessions are never served stale. The
    // manifest comes from the backend (index.html links it), because it
    // carries the instance's name and language. A new release activates on
    // the next start of the app.
    VitePWA({
      manifest: false,
      injectRegister: 'script-defer',
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        // The browser fetches these font subsets only for text in their
        // scripts, so precaching them would download them for nothing.
        globIgnores: ['**/*-{cyrillic,cyrillic-ext,vietnamese}-*.woff2'],
        cleanupOutdatedCaches: true,
        navigateFallback: '/index.html',
        // Paths the backend or nginx answer themselves, which a navigation
        // must reach instead of the cached app shell.
        navigateFallbackDenylist: [/^\/api\//, /^\/\.well-known\//, /^\/objects\//, /^\/robots\.txt$/, /^\/health$/, /^\/ready$/],
      },
    }),
  ],
  css: {
    preprocessorOptions: {
      // Every SCSS block, global or scoped, sees the breakpoint scale without
      // its own @use. The partial holds variables only, so it adds no CSS.
      scss: { additionalData: `@use '@/assets/styles/breakpoints' as *;\n` },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // npm sets `npm_package_version` from package.json for every `npm run`
  // script, so this is the single source of the running app's version.
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version ?? '0.0.0'),
  },
  // The app calls the API on its own port (VITE_API_URL), but OAuth clients
  // follow the URLs the backend derives from DOMAIN, which is this dev
  // server. These paths are passed on, so an MCP client can connect to a
  // local instance through OAuth as it would in production. The whole API is
  // passed on too, so a device on the local network can use the dev server
  // alone when VITE_API_URL is set empty in .env.development.local.
  server: {
    proxy: {
      '/.well-known/oauth-': 'http://localhost:3000',
      '/api': 'http://localhost:3000',
    },
  },
  build: {
    // The entry chunk carries the four OpenVue theme presets a user can
    // switch between at runtime, which puts it past the 500 kB default.
    chunkSizeWarningLimit: 800,
  },
})
