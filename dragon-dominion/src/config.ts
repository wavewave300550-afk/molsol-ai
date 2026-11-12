/**
 * Project identity shared by every module.
 *
 * NAMESPACE is permanent: it is baked into entity ids, dynamic property keys and
 * saved worlds. VERSION is kept in sync with package.json and both manifests by
 * `npm run set-version -- X.Y.Z` (tools/version.py) and checked by tools/validate.py.
 */
export const ADDON_NAME = "Dragon Dominion";
export const NAMESPACE = "dragon_dominion";
export const VERSION = "0.1.0";

/** Local part of an identifier: lowercase snake_case, starting with a letter. */
export const LOCAL_ID_PATTERN = /^[a-z][a-z0-9_]*$/;

/** Builds a namespaced identifier: `nsId("status")` → `"dragon_dominion:status"`. */
export function nsId(name: string): string {
  return `${NAMESPACE}:${name}`;
}

/** True when `id` is `dragon_dominion:<snake_case>`. */
export function isOwnId(id: string): boolean {
  const prefix = `${NAMESPACE}:`;
  return id.startsWith(prefix) && LOCAL_ID_PATTERN.test(id.slice(prefix.length));
}
