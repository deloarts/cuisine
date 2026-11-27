/** The household endpoints: one's own household, its invitations and the ones received. */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type HouseholdResponse = Schemas['HouseholdResponse']
export type ReceivedInvitation = Schemas['ReceivedInvitationResponse']
export type SentInvitation = Schemas['SentInvitationResponse']

export const createHousehold = (name: string): Promise<HouseholdResponse> =>
  webApi.post('/households', { body: { name } })

export const renameHousehold = (name: string): Promise<HouseholdResponse> =>
  webApi.put('/households/mine', { body: { name } })

export const leaveHousehold = (): Promise<void> => webApi.post('/households/mine/leave')

export const inviteToHousehold = (userId: string): Promise<SentInvitation> =>
  webApi.post('/households/mine/invitations', { body: { user_id: userId } })

export const revokeInvitation = (id: string): Promise<void> =>
  webApi.delete('/households/mine/invitations/{invitation_id}', { path: { invitation_id: id } })

export const receivedInvitations = (): Promise<ReceivedInvitation[]> => webApi.get('/households/invitations')

export const acceptInvitation = (id: string): Promise<HouseholdResponse> =>
  webApi.post('/households/invitations/{invitation_id}/accept', { path: { invitation_id: id } })

export const declineInvitation = (id: string): Promise<void> =>
  webApi.post('/households/invitations/{invitation_id}/decline', { path: { invitation_id: id } })

export const directory = (): Promise<Schemas['DirectoryUserResponse'][]> => webApi.get('/users/directory')
