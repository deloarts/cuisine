/** The signed-in user's household, read by the shared household cache. */
import { webApi } from '@/core/api/webRequest'

export const getMyHousehold = () => webApi.get('/households/mine')
