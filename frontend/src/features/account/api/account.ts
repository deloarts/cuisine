/**
 * The account calls the tabs share: the avatar, the voluntary consents, the
 * user's own access tokens and connected apps, the data download and the deletion of the own
 * account.
 */
import { authApi } from '@/core/api/auth'
import type { Schemas } from '@/core/api/generated'
import { webApi, type WebRequestOptions } from '@/core/api/webRequest'
import type { CurrentUserResponse } from '@/core/types/user'

/** Sets the avatar to the image; the backend deletes the previous one. */
export function uploadAvatar(file: File): Promise<CurrentUserResponse> {
  const body = new FormData()
  body.append('file', file)
  return webApi.put('/users/me/avatar', { body })
}

export function removeAvatar(): Promise<CurrentUserResponse> {
  return webApi.delete('/users/me/avatar')
}

export type Consent = Schemas['ConsentResponse']
export type ConsentKind = 'health_data' | 'ai_agents'
export type PersonalToken = Schemas['PatResponse']

export function listConsents(): Promise<Consent[]> {
  return webApi.get('/users/me/consents')
}

export function grantConsent(kind: ConsentKind): Promise<Consent[]> {
  return webApi.put('/users/me/consents/{kind}', { path: { kind } })
}

/** Withdraws a consent; the backend deletes or revokes what depended on it. */
export function withdrawConsent(kind: ConsentKind): Promise<Consent[]> {
  return webApi.delete('/users/me/consents/{kind}', { path: { kind } })
}

export function listTokens(): Promise<PersonalToken[]> {
  return webApi.get('/users/me/personal-access-tokens')
}

export interface TokenInput {
  name: string
  permissions: string[]
  expires_at: string | null
}

export async function createToken(input: TokenInput): Promise<string> {
  return (await webApi.post('/users/me/personal-access-tokens', { body: input })).token
}

export function revokeToken(id: string): Promise<void> {
  return webApi.delete('/users/me/personal-access-tokens/{token_id}', { path: { token_id: id } })
}

export type ConnectedApp = Schemas['ConnectedAppResponse']

/** The apps connected through OAuth that can still act for the user. */
export function listConnectedApps(): Promise<ConnectedApp[]> {
  return webApi.get('/users/me/connected-apps')
}

/** Ends a connected app's access at once; its next call is refused. */
export function revokeConnectedApp(id: string): Promise<void> {
  return webApi.delete('/users/me/connected-apps/{app_id}', { path: { app_id: id } })
}

export type SelfDeletionImpactResponse = Schemas['SelfDeletionImpact']
export type PasskeyOptions = Schemas['PasskeyOptionsResponse']

/** Everything stored about the user, as the JSON the download saves. */
export function exportMyData(): Promise<unknown> {
  return webApi.get('/users/me/export')
}

export function ownDeletionImpact(): Promise<SelfDeletionImpactResponse> {
  return webApi.get('/users/me/deletion-impact')
}

/** A passkey challenge to confirm the deletion with, the same one the login uses. */
export async function passkeyChallenge(): Promise<PasskeyOptions> {
  return (await authApi.post<PasskeyOptions>('/login/passkey/options')).data
}

export function deleteOwnAccount(body: Schemas['SelfDeletionRequest']): Promise<void> {
  return webApi.delete('/users/me', { body })
}

/** The fields of the own profile a `PATCH /users/me` may change. */
export type ProfileChanges = WebRequestOptions<'/users/me', 'patch'>['body']

/** Saves changes to the own profile and returns the updated user. */
export function updateProfile(body: ProfileChanges): Promise<CurrentUserResponse> {
  return webApi.patch('/users/me', { body })
}

export type FoodRestriction = Schemas['FoodRestrictionResponse']
export type FoodRestrictionInput = WebRequestOptions<'/users/me/food-restrictions', 'post'>['body']

export function listFoodRestrictions(): Promise<FoodRestriction[]> {
  return webApi.get('/users/me/food-restrictions')
}

export async function addFoodRestriction(body: FoodRestrictionInput): Promise<void> {
  await webApi.post('/users/me/food-restrictions', { body })
}

export async function removeFoodRestriction(id: string): Promise<void> {
  await webApi.delete('/users/me/food-restrictions/{restriction_id}', { path: { restriction_id: id } })
}

/** The first catalogue ingredients matching a search, for the restriction picker. */
export async function searchIngredients(search: string, limit = 10) {
  return (await webApi.get('/ingredients', { query: { search, limit } })).items
}

/** The instance's privacy defaults, which bound the own default recipe visibility. */
export function getPrivacySettings() {
  return webApi.get('/settings/privacy')
}
