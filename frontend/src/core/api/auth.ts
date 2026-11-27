import axios from 'axios'

import { CSRF_HEADER_NAME, CSRF_HEADER_VALUE } from '@/core/api'

const API_ROOT = import.meta.env.VITE_API_URL ?? ''

/**
 * The login steps and the logout, on their own prefix (/api/v1/auth), and
 * the public info the login page reads (/api/v1/public).
 *
 * withCredentials: the "trust this device" cookie, path-scoped to
 * /api/v1/auth, must ride along on the login requests, and the login
 * responses set the session cookie. The CSRF header is attached always;
 * the logout needs it.
 */
export const authApi = axios.create({
  baseURL: `${API_ROOT}/api/v1/auth`,
  withCredentials: true,
})
authApi.defaults.headers.common[CSRF_HEADER_NAME] = CSRF_HEADER_VALUE

export const publicApi = axios.create({ baseURL: `${API_ROOT}/api/v1/public` })
