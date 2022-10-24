from time import monotonic
from typing import ClassVar

from rich.repr import rich_repr

from .case import camel_to_snake
from ._types import MessageTarget


@rich_repr
class Message:
    """Base class for a message."""

    __slots__ = [
        "sender",
        "name",
        "time",
        "_no_default_action",
        "_stop_propagation",
    ]

    sender: MessageTarget
    bubble: ClassVar[bool] = False
    default_priority: ClassVar[int] = 0

    def __init__(self, sender: MessageTarget) -> None:
        self.sender = sender
        self.name = camel_to_snake(self.__class__.__name__)
        self.time = monotonic()
        self._no_default_action = False
        self._stop_propagaton = False
        super().__init__()

    def __rich_repr__(self):
        return
        yield

    def __init_subclass__(cls, bubble: bool = False, priority: int = 0) -> None:
        super().__init_subclass__()
        cls.bubble = bubble
        cls.default_priority = priority

    def can_batch(self, message: "Message") -> bool:
        """Check if another message may supersede this one.

        Args:
            message (Message): [description]

        Returns:
            bool: [description]
        """
        return False

    def prevent_default(self, prevent: bool = True) -> None:
        """Suppress the default action.

        Args:
            prevent (bool, optional): True if the default action should be suppressed,
                or False if the default actions should be performed. Defaults to True.
        """
        self._no_default_action = prevent

    def stop_propagation(self, stop: bool = True) -> None:
        self._stop_propagaton = stop
