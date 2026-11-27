"""The query parameters the log tables share: filters, a date range and the
sort, turned into the repository filters. Dates are whole UTC days, both
ends included."""

from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Literal

from fastapi import Depends
from fastapi import Query

from src.platform.domain.exceptions import InvalidDateRangeError
from src.platform.domain.value_objects.agent import AgentCallOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventOutcome
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.repositories.log_filters import AgentCallFilter
from src.platform.ports.outbound.repositories.log_filters import SecurityEventFilter

LogSort = Literal["newest", "oldest"]


def _range(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    if date_from and date_to and date_from > date_to:
        raise InvalidDateRangeError("The start date must not lie after the end date.")
    since = (
        datetime(date_from.year, date_from.month, date_from.day, tzinfo=UTC) if date_from else None
    )
    until = (
        datetime(date_to.year, date_to.month, date_to.day, tzinfo=UTC) + timedelta(days=1)
        if date_to
        else None
    )
    return since, until


def security_event_filter(
    event_type: list[SecurityEventType] | None = Query(None),
    outcome: SecurityEventOutcome | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    sort: LogSort = Query("newest"),
) -> SecurityEventFilter:
    since, until = _range(date_from, date_to)
    return SecurityEventFilter(
        event_types=tuple(t.value for t in event_type or []),
        outcome=outcome.value if outcome else None,
        since=since,
        until=until,
        oldest_first=sort == "oldest",
    )


def agent_call_filter(
    tool: list[str] | None = Query(None),
    outcome: AgentCallOutcome | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    sort: LogSort = Query("newest"),
) -> AgentCallFilter:
    since, until = _range(date_from, date_to)
    return AgentCallFilter(
        tools=tuple(t for t in tool or [] if t),
        outcome=outcome.value if outcome else None,
        since=since,
        until=until,
        oldest_first=sort == "oldest",
    )


SecurityEventQuery = Depends(security_event_filter)
AgentCallQuery = Depends(agent_call_filter)
