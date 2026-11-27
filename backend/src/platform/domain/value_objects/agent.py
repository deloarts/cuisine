"""How an AI agent authenticated, and how one of its tool calls ended."""

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class AgentTokenKind(StrValueEnum):
    PAT = "pat"
    API_KEY = "api_key"
    # An app connected through OAuth; the token id is the grant's id, so
    # the budgets survive the hourly change of the access token.
    OAUTH = "oauth"


class AgentCallOutcome(StrValueEnum):
    # The tool ran and answered.
    OK = "ok"
    # The tool ran into a domain error or invalid arguments.
    ERROR = "error"
    # The call never ran: unknown tool, budget spent or not allowed.
    REFUSED = "refused"
