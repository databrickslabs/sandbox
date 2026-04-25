/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_REGISTRY_API_URL?: string
  readonly VITE_SUPERVISOR_URL?: string
  readonly VITE_DATABRICKS_HOST?: string
  readonly VITE_DEBUG?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
