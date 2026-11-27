/**
 * Assembles the messages of one UI language from the core locale file and
 * the feature modules. A feature keeps its strings in
 * `src/features/<feature>/locales/{en-GB,de-AT}.ts`, each exporting one
 * object whose top-level keys are the feature's own namespaces, so two
 * features never edit the same file. The app loads the modules through
 * import.meta.glob and the i18n parity check through the file system; both
 * merge them here.
 */

export type Messages = Record<string, unknown>

export interface MergeResult {
  messages: Messages
  /** Top-level keys that more than one source defines. */
  collisions: string[]
}

/**
 * Merges the core messages and the modules on their top-level keys. A key
 * that two sources define is reported rather than merged, since a feature
 * that wrote into another namespace would silently overwrite its strings.
 */
export function mergeMessages(core: Messages, modules: Record<string, Messages>): MergeResult {
  const messages: Messages = { ...core }
  const owners = new Map<string, string>(Object.keys(core).map((key) => [key, 'core']))
  const collisions: string[] = []
  for (const [source, module] of Object.entries(modules)) {
    for (const [key, value] of Object.entries(module)) {
      const owner = owners.get(key)
      if (owner) {
        collisions.push(`${key} (${owner} and ${source})`)
        continue
      }
      owners.set(key, source)
      messages[key] = value
    }
  }
  return { messages, collisions }
}

/** The feature name of a module path such as `../../features/recipes/locales/en-GB.ts`. */
export function featureOf(path: string): string {
  const match = /features\/([^/]+)\/locales\//.exec(path)
  return match?.[1] ?? path
}
