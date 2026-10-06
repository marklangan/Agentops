import asyncio

import pytest

from agentops.bus import MessageBus
from agentops.messages import Message, MessageType


def test_send_delivers_and_records_history():
    async def scenario():
        bus = MessageBus()
        inbox = bus.register("a")
        bus.register("b")
        msg = Message(sender="b", recipient="a", type=MessageType.TASK, content="hi")
        await bus.send(msg)
        assert await inbox.get() is msg
        assert bus.trace(msg.correlation_id) == [msg]

    asyncio.run(scenario())


def test_unknown_recipient_raises():
    async def scenario():
        bus = MessageBus()
        with pytest.raises(KeyError):
            await bus.send(Message("x", "nobody", MessageType.TASK, "hi"))

    asyncio.run(scenario())


def test_duplicate_register_raises():
    bus = MessageBus()
    bus.register("a")
    with pytest.raises(ValueError):
        bus.register("a")


def test_reply_keeps_correlation_id():
    msg = Message("orchestrator", "ci", MessageType.TASK, "do it")
    reply = msg.reply("done")
    assert (reply.sender, reply.recipient) == ("ci", "orchestrator")
    assert reply.correlation_id == msg.correlation_id
