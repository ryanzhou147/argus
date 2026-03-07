from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ..models.enums import EventType


class EventRepository(ABC):
    @abstractmethod
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """Return event list records, optionally filtered."""
        ...

    @abstractmethod
    def get_event_by_id(self, event_id: str) -> Optional[dict]:
        """Return a single raw event dict or None if not found."""
        ...

    @abstractmethod
    def get_related_events(self, event_id: str) -> List[dict]:
        """Return related event dicts with relationship metadata."""
        ...

    @abstractmethod
    def get_filters(self) -> dict:
        """Return available filter options (event types, relationship types)."""
        ...

    @abstractmethod
    def get_timeline(self) -> List[dict]:
        """Return events ordered by start_time for timeline playback."""
        ...

    @abstractmethod
    def get_event_detail(self, event_id: str) -> Optional[dict]:
        """Return full event detail including sources, entities, engagement."""
        ...
