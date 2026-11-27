/** The people the signed-in user may see, for the person pickers and filters. */
import type { Schemas } from '@/core/api/generated'
import { webApi } from '@/core/api/webRequest'

export type DirectoryUser = Schemas['DirectoryUserResponse']

export const listDirectory = (): Promise<DirectoryUser[]> => webApi.get('/users/directory')
