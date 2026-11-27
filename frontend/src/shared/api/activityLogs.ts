/**
 * The agent call log and the security log, for the shared tables that show
 * either the signed-in user's own entries or, with the permission, everyone's.
 */
import { webApi, type QueryOf } from '@/core/api/webRequest'

type AgentCallQuery = QueryOf<'/agent-calls'>
type SecurityEventQuery = QueryOf<'/security-events'>

export const listAgentCalls = (query: AgentCallQuery) => webApi.get('/agent-calls', { query })

export const listOwnAgentCalls = (query: QueryOf<'/users/me/agent-calls'>) =>
  webApi.get('/users/me/agent-calls', { query })

export const listSecurityEvents = (query: SecurityEventQuery) => webApi.get('/security-events', { query })

export const listOwnSecurityEvents = (query: QueryOf<'/users/me/security-events'>) =>
  webApi.get('/users/me/security-events', { query })
