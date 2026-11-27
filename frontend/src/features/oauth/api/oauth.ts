/**
 * The consent page's two calls. Both send the authorization request exactly
 * as the app put it in the URL; the backend validates it every time, so the
 * page holds nothing the server has to trust.
 */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type AuthorizationRequest = Schemas['AuthorizationRequestSchema']
export type AuthorizationPrompt = Schemas['AuthorizationPromptResponse']

export function inspectAuthorization(request: AuthorizationRequest): Promise<AuthorizationPrompt> {
  return webApi.post('/oauth/authorize/inspect', { body: request })
}

/** The address the browser continues to: back to the app, with the code or the refusal. */
export async function decideAuthorization(
  request: AuthorizationRequest,
  approve: boolean,
  permissions: string[],
): Promise<string> {
  return (await webApi.post('/oauth/authorize/decision', { body: { request, approve, permissions } }))
    .redirect_to
}
