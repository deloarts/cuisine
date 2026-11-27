/**
 * The instance's privacy mode in the words the privacy statement uses, worked
 * out from the privacy settings. Instance, peers, public and private are the
 * locked modes the admin area names; any other locked default is a fixed
 * visibility, and an unlocked default means every user chooses per recipe.
 *
 * While the instance does not allow public recipes, a stored "public" reads
 * as "instance", and while peering is off a stored "peers" does too, the same
 * rule the backend applies.
 */
import type { Schemas } from '@/core/api/generated'

// The fields the mode depends on; the search engine switch plays no part.
export type PrivacySettings = Pick<
  Schemas['PrivacySettingsSchema'],
  'default_recipe_visibility' | 'users_may_change_visibility' | 'allow_public_recipes'
>
export type RecipeVisibility = PrivacySettings['default_recipe_visibility']
export type PrivacyMode = 'instance' | 'peers' | 'public' | 'private' | 'choice' | 'fixed'

/** Every visibility, narrowest first. */
export const RECIPE_VISIBILITIES: RecipeVisibility[] = [
  'private',
  'household',
  'shared',
  'instance',
  'peers',
  'public',
]

/**
 * The visibilities that may be picked: peers only while peering is on,
 * public only while the instance allows it.
 */
export function offeredVisibilities(publicAllowed: boolean, peering = false): RecipeVisibility[] {
  return RECIPE_VISIBILITIES.filter(
    (v) => (v !== 'public' || publicAllowed) && (v !== 'peers' || peering),
  )
}

/** The visibility that applies to a stored one. */
export function effectiveVisibility(
  value: RecipeVisibility,
  publicAllowed: boolean,
  peering = false,
): RecipeVisibility {
  if (value === 'public' && !publicAllowed) return 'instance'
  if (value === 'peers' && !peering) return 'instance'
  return value
}

export function privacyMode(settings: PrivacySettings, peering = false): PrivacyMode {
  if (settings.users_may_change_visibility) return 'choice'
  const fallback = effectiveVisibility(
    settings.default_recipe_visibility,
    settings.allow_public_recipes,
    peering,
  )
  if (fallback === 'instance') return 'instance'
  if (fallback === 'peers') return 'peers'
  if (fallback === 'public') return 'public'
  if (fallback === 'private') return 'private'
  return 'fixed'
}

/**
 * The visibility a new recipe of this user starts with: their own default
 * while users may choose, the instance default otherwise, read through the
 * public and peering switches.
 */
export function effectiveDefault(
  settings: PrivacySettings,
  own: string | null | undefined,
  peering = false,
): RecipeVisibility {
  const chosen =
    settings.users_may_change_visibility && isVisibility(own) ? own : settings.default_recipe_visibility
  return effectiveVisibility(chosen, settings.allow_public_recipes, peering)
}

export function isVisibility(value: unknown): value is RecipeVisibility {
  return RECIPE_VISIBILITIES.includes(value as RecipeVisibility)
}

export type PrivacySnapshot = Schemas['PrivacyModeResponse']

/**
 * The mode from the snapshot the backend sends with the current user, which
 * names only instance, peers, public, private and user choice; a locked
 * default other than those is the fixed visibility here.
 */
export function modeOfSnapshot(snapshot: PrivacySnapshot): PrivacyMode {
  if (snapshot.mode === 'user_choice') return 'choice'
  if (snapshot.mode === 'instance') return 'instance'
  if (snapshot.mode === 'peers') return 'peers'
  if (snapshot.mode === 'public') return 'public'
  return snapshot.default_visibility === 'private' ? 'private' : 'fixed'
}
