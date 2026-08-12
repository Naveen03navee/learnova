from contextvars import ContextVar
from typing import Optional
from uuid import UUID

_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_session_id: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
_batch_id: ContextVar[Optional[str]] = ContextVar("batch_id", default=None)
_paper_id: ContextVar[Optional[str]] = ContextVar("paper_id", default=None)

def set_request_id(request_id: str) -> None:
    _request_id.set(request_id)

def get_request_id() -> Optional[str]:
    return _request_id.get()

def set_session_id(session_id: str) -> None:
    _session_id.set(session_id)

def get_session_id() -> Optional[str]:
    return _session_id.get()

def set_batch_id(batch_id: str) -> None:
    _batch_id.set(batch_id)

def get_batch_id() -> Optional[str]:
    return _batch_id.get()

def set_paper_id(paper_id: str) -> None:
    _paper_id.set(paper_id)

def get_paper_id() -> Optional[str]:
    return _paper_id.get()

def get_context_dict() -> dict:
    ctx = {}
    if req := get_request_id():
        ctx["request_id"] = req
    if sess := get_session_id():
        ctx["session_id"] = sess
    if batch := get_batch_id():
        ctx["batch_id"] = batch
    if paper := get_paper_id():
        ctx["paper_id"] = paper
    return ctx
