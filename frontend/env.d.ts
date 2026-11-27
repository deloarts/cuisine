/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Injected at build, dev and test time by vite.config.ts's `define`, from
// package.json's `version`.
declare const __APP_VERSION__: string
