import asyncio
from typing import Dict, AsyncGenerator
from uuid import UUID
from app.schemas.generation import GenerationEvent

class EventBus:
    def __init__(self):
        # A dictionary mapping session_id to a list of queues listening to that session
        self._listeners: Dict[UUID, list[asyncio.Queue]] = {}
        # A dictionary mapping session_id to a list of past events (replay buffer)
        self._history: Dict[UUID, list[GenerationEvent]] = {}

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
                # Keep history for a while, or clear it if needed. 
                # For safety, we keep history until the background task finishes.

    def cleanup_history(self, session_id: UUID):
        if session_id in self._history:
            del self._history[session_id]

    async def publish(self, event: GenerationEvent):
        """Publish an event to all queues listening to this target."""
        target_id = event.session_id or event.resource_id
        if target_id:
            # Store in history buffer (max 100 events to prevent leak)
            if target_id not in self._history:
                self._history[target_id] = []
            self._history[target_id].append(event)
            if len(self._history[target_id]) > 100:
                self._history[target_id] = self._history[target_id][-100:]
                
            if target_id in self._listeners:
                for queue in self._listeners[target_id]:
                    await queue.put(event)

# Global singleton event bus
event_bus = EventBus()

async def event_stream(target_id: UUID) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE formatted strings.
    """
    queue = event_bus.subscribe(target_id)
    try:
        # 1. Yield historical events immediately
        if target_id in event_bus._history:
            for past_event in event_bus._history[target_id]:
                yield f"data: {past_event.model_dump_json()}\n\n"
                
        # 2. Wait for new events
        while True:
            # Wait for the next event
            event: GenerationEvent = await queue.get()
            
            # Format as SSE
            yield f"data: {event.model_dump_json()}\n\n"
            
            # If the session is finished, close the stream
            if event.status in ["COMPLETED", "PARTIAL", "FAILED", "READY"]:
                break
    finally:
        event_bus.unsubscribe(target_id, queue)
