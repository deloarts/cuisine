"""The base every API schema inherits: unknown fields are refused, so a
typo in a request is an error instead of a silent no-op."""

from pydantic import BaseModel
from pydantic import ConfigDict


class RequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](ResponseSchema):
    items: list[T]
    total: int
