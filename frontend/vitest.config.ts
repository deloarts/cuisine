import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      // A request no spec mocked fails the same way on every machine,
      // because the reserved .invalid domain never resolves.
      environmentOptions: { jsdom: { url: 'http://cuisine.invalid/' } },
      exclude: [...configDefaults.exclude, 'e2e/**'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      setupFiles: ['./vitest.setup.ts'],
      coverage: {
        provider: 'v8',
        include: ['src/**/*.{ts,vue}'],
        exclude: [
          'src/**/__tests__/**',
          'src/**/*.d.ts',
          'src/core/api/generated/**',
          'src/core/i18n/locales/**',
        ],
        reporter: ['text-summary', 'lcov'],
      },
      // Every spy is restored and every mock's call history cleared before
      // each test, so nothing carries over from one test to the next.
      restoreMocks: true,
      clearMocks: true,
    },
  }),
)
