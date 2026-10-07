"""Message protocol shared by every agent.

All communication goes through Message objects on the bus. Agents never call
each other directly, which keeps them decoupled and makes every interaction
traceable.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class MessageType(str, Enum):
    TASK = "task"      # a request for an agent to do some work
    RESULT = "result"  # a successful response to a TASK
    ERROR = "error"    # a failed response to a TASK


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass(frozen=True)
class Message:
    sender: str
    recipient: str
    type: MessageType
    content: str
    correlation_id: str = field(default_factory=_new_id)
    id: str = field(default_factory=_new_id)
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def reply(self, content: str, type: MessageType = MessageType.RESULT, **metadata) -> Message:
        """Build a response routed back to the sender, keeping the correlation id."""
        return Message(
            sender=self.recipient,
            recipient=self.sender,
            type=type,
            content=content,
            correlation_id=self.correlation_id,
            metadata=metadata,
        )
