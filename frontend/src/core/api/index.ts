import axios from 'axios'

import { isPrivacyRequired } from '@/core/privacy/privacyGate'

const API_ROOT = import.meta.env.VITE_API_URL ?? ''

// The session lives in an httponly cookie that scripts cannot read (see
// auth_deps.py). withCredentials sends it, also across the dev ports, and
// the CSRF header protects the unsafe methods it authenticates.
export const CSRF_HEADER_NAME = 'X-Requested-With'
export const CSRF_HEADER_VALUE = 'cuisine'

const api = axios.create({
  baseURL: `${API_ROOT}/api/v1/web`,
  withCredentials: true,
  paramsSerializer: (params) => {
    const usp = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (Array.isArray(value)) {
        for (const v of value) usp.append(key, String(v))
      } else if (value !== undefined && value !== null) {
        usp.append(key, String(value))
      }
    }
    return usp.toString()
  },
})

api.defaults.headers.common[CSRF_HEADER_NAME] = CSRF_HEADER_VALUE

// A session ending mid-visit sends the user to sign in, and a request refused
// because the privacy statement is not acknowledged brings the statement
// back. The store is imported lazily to avoid an import cycle through the
// router. The login steps use `authApi`, so bad credentials never land here.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const { useCurrentUserStore } = await import('@/core/stores/currentUserStore')
      useCurrentUserStore().sessionExpired()
    } else if (isPrivacyRequired(error)) {
      const { useCurrentUserStore } = await import('@/core/stores/currentUserStore')
      useCurrentUserStore().requirePrivacyAcknowledgement()
    }
    return Promise.reject(error)
  },
)

export default api
