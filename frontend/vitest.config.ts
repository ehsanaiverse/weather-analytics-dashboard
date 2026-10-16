import { defineConfig } from 'vitest/config'

/**
 * Vitest configuration.
 *
 * The tests cover pure logic (`normalise`, the feature-to-geometry mapping and
 * the timezone-aware formatters), so they run in the plain Node environment
 * with no DOM, no jsdom and no browser download.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    reporters: 'default',
  },
})