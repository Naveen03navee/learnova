import asyncio
from typing import Dict, AsyncGenerator
from uuid import UUID
from app.schemas.generation import GenerationEvent

class EventBus:
    def __init__(self):
        # A dictionary mapping session_id to a list of queues listening to that session
        self._listeners: Dict[UUID, list[asyncio.Queue]] = {}

    def subscribe(self, session_id: UUID) -> asyncio.Queue:
        if session_id not in self._listeners:
            self._listeners[session_id] = []
        queue = asyncio.Queue()
        self._listeners[session_id].append(queue)
        return queue

    def unsubscribe(self, session_id: UUID, queue: asyncio.Queue):
        if session_id in self._listeners:
            try:
                self._listeners[session_id].remove(queue)
            except ValueError:
                pass
            if not self._listeners[session_id]:
                del self._listeners[session_id]

    async def publish(self, event: GenerationEvent):
        """Publish an event to all queues listening to this session."""
        if event.session_id in self._listeners:
            for queue in self._listeners[event.session_id]:
                await queue.put(event)

# Global singleton event bus
event_bus = EventBus()

async def event_stream(session_id: UUID) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE formatted strings.
    """
    queue = event_bus.subscribe(session_id)
    try:
        while True:
            # Wait for the next event
            event: GenerationEvent = await queue.get()
            
            # Format as SSE
            yield f"data: {event.model_dump_json()}\n\n"
            
            # If the session is finished, close the stream
            if event.status in ["COMPLETED", "PARTIAL", "FAILED"]:
                break
    finally:
        event_bus.unsubscribe(session_id, queue)
