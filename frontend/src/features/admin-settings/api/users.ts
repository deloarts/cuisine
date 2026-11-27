/** The user and group administration: accounts, groups, the directory and account deletion. */
import { webApi, type QueryOf, type WebRequestOptions } from '@/core/api/webRequest'

export type UserCreateBody = WebRequestOptions<'/users', 'post'>['body']
export type UserUpdateBody = WebRequestOptions<'/users/{user_id}', 'patch'>['body']
export type GroupCreateBody = WebRequestOptions<'/groups', 'post'>['body']
export type GroupUpdateBody = WebRequestOptions<'/groups/{group_id}', 'patch'>['body']
export type UserDeletionQuery = QueryOf<'/users/{user_id}', 'delete'>

export const usersApi = {
  list: () => webApi.get('/users'),
  directory: () => webApi.get('/users/directory'),
  create: (body: UserCreateBody) => webApi.post('/users', { body }),
  update: (id: string, body: UserUpdateBody) => webApi.patch('/users/{user_id}', { path: { user_id: id }, body }),
  /** Sets the user's avatar to the image; the backend deletes the previous one. */
  uploadAvatar: (id: string, file: File) => {
    const body = new FormData()
    body.append('file', file)
    return webApi.put('/users/{user_id}/avatar', { path: { user_id: id }, body })
  },
  removeAvatar: (id: string) => webApi.delete('/users/{user_id}/avatar', { path: { user_id: id } }),
  resetTotp: (id: string) => webApi.post('/users/{user_id}/reset-totp', { path: { user_id: id } }),
  logout: (id: string) => webApi.post('/users/{user_id}/logout', { path: { user_id: id } }),
  deletionImpact: (id: string) => webApi.get('/users/{user_id}/deletion-impact', { path: { user_id: id } }),
  remove: async (id: string, query: UserDeletionQuery) => {
    await webApi.delete('/users/{user_id}', { path: { user_id: id }, query })
  },
}

export const groupsApi = {
  list: () => webApi.get('/groups'),
  create: (body: GroupCreateBody) => webApi.post('/groups', { body }),
  update: (id: string, body: GroupUpdateBody) => webApi.patch('/groups/{group_id}', { path: { group_id: id }, body }),
  remove: async (id: string) => {
    await webApi.delete('/groups/{group_id}', { path: { group_id: id } })
  },
}
