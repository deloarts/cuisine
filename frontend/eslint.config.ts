import type { Linter } from 'eslint'
import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVueA11y from 'eslint-plugin-vuejs-accessibility'
import pluginVitest from '@vitest/eslint-plugin'
import pluginOxlint from 'eslint-plugin-oxlint'
import skipFormatting from 'eslint-config-prettier/flat'

const APP_SOURCE = ['src/**/*.{ts,vue}']

// Frontend request and response types come from the generated OpenAPI
// schema (`export type XResponse = Schemas['XResponse']`), never written by
// hand: a hand-written shape drifts from the backend silently instead of
// failing the `check:api-types` gate.
const WIRE_TYPE_MESSAGE =
  "Hand-written interfaces named *Response/*Request drift from the backend silently. Alias the generated schema instead, e.g. export type XResponse = Schemas['XResponse']."
const WIRE_NAME = '/(Response|Request)$/'
const noHandWrittenWireTypes = [
  { selector: `TSInterfaceDeclaration[id.name=${WIRE_NAME}]`, message: WIRE_TYPE_MESSAGE },
  { selector: `TSTypeAliasDeclaration[id.name=${WIRE_NAME}] > TSTypeLiteral`, message: WIRE_TYPE_MESSAGE },
]

// HTTP calls go through `webApi` (core/api/webRequest.ts), which checks the
// path, method, query and body against the generated schema. A raw
// `api.get<T>()` on the axios instance only asserts T.
const RAW_API_MESSAGE =
  "Call the backend through webApi from '@/core/api/webRequest' (or authApi for the login steps), which checks the route, query, body and response against the generated schema."
const noRawApiCalls = [
  {
    selector: `Program:has(ImportDeclaration[source.value='@/core/api'] > ImportDefaultSpecifier[local.name='api']) MemberExpression[object.name='api'][property.name=/^(get|post|put|patch|delete)$/]`,
    message: RAW_API_MESSAGE,
  },
]

const restrictedSyntax: Linter.RuleEntry = ['error', ...noHandWrittenWireTypes, ...noRawApiCalls]

// Specs select elements by role, label, text or data-testid, never by
// OpenVue's internal `.p-*` classes, which an upgrade may rename.
const OPENVUE_INTERNAL_SELECTOR = String.raw`/(^|[\s>+~,(])\.(p|mdi)-/`
const noOpenVueInternalSelectors: Linter.RuleEntry = [
  'error',
  {
    selector: `Literal[value=${OPENVUE_INTERNAL_SELECTOR}]`,
    message: 'Do not select on OpenVue internal .p-* or .mdi-* classes in specs.',
  },
]

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{vue,ts,mts,tsx}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**', 'src/core/api/generated/**']),

  ...pluginVue.configs['flat/strongly-recommended'],
  vueTsConfigs.recommended,

  // Accessibility checks on templates. A label counts as tied to its control
  // when it wraps it or names its id. Moving focus to a dialog's first field
  // is the dialog pattern, so autofocus is allowed.
  ...pluginVueA11y.configs['flat/recommended'],
  {
    name: 'app/accessibility',
    rules: {
      'vuejs-accessibility/label-has-for': [
        'error',
        {
          required: { some: ['nesting', 'id'] },
          controlComponents: ['Checkbox', 'ToggleSwitch', 'RadioButton', 'InputText', 'InputNumber', 'Textarea', 'DatePicker', 'Password'],
        },
      ],
      'vuejs-accessibility/no-autofocus': 'off',
    },
  },

  // Optional props are intentionally undefined when omitted; a real default
  // is expressed through withDefaults where one exists.
  {
    name: 'app/no-require-default-prop',
    rules: {
      'vue/require-default-prop': 'off',
    },
  },

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
    rules: {
      ...pluginVitest.configs.recommended.rules,
      'vue/one-component-per-file': 'off',
    },
  },

  // A promise nobody awaits or catches turns a failed request into an
  // unhandled rejection the user never sees.
  {
    name: 'app/promise-handling',
    files: APP_SOURCE,
    rules: {
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
    },
  },

  {
    name: 'app/restricted-syntax',
    files: APP_SOURCE,
    ignores: ['src/**/__tests__/**', 'src/core/api/generated/**'],
    rules: { 'no-restricted-syntax': restrictedSyntax },
  },

  {
    name: 'app/no-openvue-internal-selectors-in-specs',
    files: ['src/**/__tests__/**/*.spec.ts'],
    rules: { 'no-restricted-syntax': noOpenVueInternalSelectors },
  },

  // Specs and the Node scripts run no type-aware rule and skip the project
  // service, which saves a good part of the time typed linting adds.
  {
    name: 'app/untyped-parse',
    files: ['src/**/__tests__/**', 'src/**/*.spec.ts', 'scripts/**'],
    languageOptions: { parserOptions: { projectService: false } },
    rules: {
      '@typescript-eslint/no-floating-promises': 'off',
      '@typescript-eslint/no-misused-promises': 'off',
    },
  },

  ...pluginOxlint.buildFromOxlintConfigFile('.oxlintrc.json'),

  skipFormatting,
)
