/** The admin side of peering: this instance, invitations, paired instances and their channels. */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type OwnInstance = Schemas['OwnInstanceResponse']
export type Peer = Schemas['PeerResponse']
export type PeerInvitation = Schemas['PeerInvitationResponse']
export type CreatedPeerInvitation = Schemas['CreatedPeerInvitationResponse']
export type PeerSwitches = Schemas['PeerSwitchesRequest']
export type PeerChannel = Schemas['PeerChannelResponse']

export const peeringApi = {
  self: () => webApi.get('/admin/peers/self'),
  list: () => webApi.get('/admin/peers'),
  invitations: () => webApi.get('/admin/peers/invitations'),
  invite: () => webApi.post('/admin/peers/invitations'),
  revokeInvitation: async (id: string) => {
    await webApi.delete('/admin/peers/invitations/{invitation_id}', { path: { invitation_id: id } })
  },
  accept: (invitationUrl: string) => webApi.post('/admin/peers/accept', { body: { invitation_url: invitationUrl } }),
  saveSwitches: (id: string, body: PeerSwitches) =>
    webApi.put('/admin/peers/{peer_id}/switches', { path: { peer_id: id }, body }),
  refresh: (id: string) => webApi.post('/admin/peers/{peer_id}/refresh', { path: { peer_id: id } }),
  revoke: (id: string) => webApi.post('/admin/peers/{peer_id}/revoke', { path: { peer_id: id } }),
  sync: (id: string) => webApi.post('/admin/peers/{peer_id}/sync', { path: { peer_id: id } }),
  acceptWaiting: (id: string) =>
    webApi.post('/admin/peers/{peer_id}/incoming-recipes/accept', { path: { peer_id: id } }),
}

export type IncomingRecipe = Schemas['IncomingRecipeResponse']
export type NeededEntry = Schemas['NeededEntryResponse']
export type MappingDecision = Schemas['MappingDecisionRequest']
export type MappingCorrection = Schemas['MappingCorrectionRequest']
export type PeerMapping = Schemas['PeerMappingResponse']
export type IncomingStatus = IncomingRecipe['status']

/** Recipes paired instances share with this one, waiting for an administrator, and the per-peer catalogue mapping. */
export const incomingApi = {
  list: (status: IncomingStatus) => webApi.get('/admin/incoming-recipes', { query: { status } }),
  get: (id: string) => webApi.get('/admin/incoming-recipes/{item_id}', { path: { item_id: id } }),
  accept: (id: string, decisions: MappingDecision[]) =>
    webApi.post('/admin/incoming-recipes/{item_id}/accept', { path: { item_id: id }, body: { decisions } }),
  reject: (id: string) => webApi.post('/admin/incoming-recipes/{item_id}/reject', { path: { item_id: id } }),
  reopen: (id: string) => webApi.post('/admin/incoming-recipes/{item_id}/reopen', { path: { item_id: id } }),
  mappings: (peerId: string) => webApi.get('/admin/peers/{peer_id}/mappings', { path: { peer_id: peerId } }),
  correct: (peerId: string, kind: PeerMapping['kind'], sourceId: string, body: MappingCorrection) =>
    webApi.put('/admin/peers/{peer_id}/mappings/{kind}/{source_id}', {
      path: { peer_id: peerId, kind, source_id: sourceId },
      body,
    }),
}

export type PeerSuggestionRequest = Schemas['PeerSuggestionRequest']

/** Catalogue values paired instances offer for the local entries their mappings point at. */
export const suggestionsApi = {
  list: (query: { peer_id?: string; kind?: PeerSuggestionRequest['kind'] }) =>
    webApi.get('/admin/peer-suggestions', { query }),
  accept: async (body: PeerSuggestionRequest) => {
    await webApi.post('/admin/peer-suggestions/accept', { body })
  },
  dismiss: async (body: PeerSuggestionRequest) => {
    await webApi.post('/admin/peer-suggestions/dismiss', { body })
  },
}
