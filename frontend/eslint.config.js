import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { globalIgnores } from 'eslint/config'

/**
 * ESLint flat configuration.
 *
 * Three rule sets are combined:
 *  - `js.configs.recommended` for plain JavaScript mistakes,
 *  - `tseslint.configs.recommended` for type-aware-free TypeScript rules,
 *  - the React hooks and react-refresh plugin configs for component code.
 */
export default tseslint.config(
  globalIgnores(['dist', 'coverage', 'node_modules']),

  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    rules: {
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports', fixStyle: 'inline-type-imports' },
      ],
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },

  {
    // Config files and build tooling run in Node, not the browser.
    files: ['*.config.{ts,js}', 'vite.config.ts', 'tailwind.config.js', 'postcss.config.js'],
    languageOptions: {
      globals: globals.node,
    },
  },
)