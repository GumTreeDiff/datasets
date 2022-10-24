from __future__ import annotations

import logging
import re
from typing import Callable, Iterable, Generator, Type

from . import events
from ._types import MessageTarget
from ._parser import Awaitable, Parser, TokenCallback
from ._ansi_sequences import ANSI_SEQUENCES

log = logging.getLogger("rich")


_re_mouse_event = re.compile("^" + re.escape("\x1b[") + r"(<?[\d;]+[mM]|M...)\Z")


class XTermParser(Parser[events.Event]):

    _re_sgr_mouse = re.compile(r"\x1b\[<(\d+);(\d+);(\d+)([Mm])")

    def __init__(self, sender: MessageTarget, more_data: Callable[[], bool]) -> None:
        self.sender = sender
        self.more_data = more_data
        super().__init__()

    @classmethod
    def parse_mouse_code(cls, code: str, sender: MessageTarget) -> events.Event | None:

        sgr_match = cls._re_sgr_mouse.match(code)
        if sgr_match:
            _buttons, x, y, state = sgr_match.groups()
            buttons = int(_buttons)
            button = 0

            event_class: Type[events._MouseBase]
            if buttons & 32:
                event_class = events.MouseMove
            else:
                event_class = events.MouseDown if state == "M" else events.MouseUp
                button = (4 if (buttons & 64) else 1) + (buttons & 3)
            event = event_class(
                sender,
                int(x) - 1,
                int(y) - 1,
                button,
                bool(buttons & 4),
                bool(buttons & 8),
                bool(buttons & 16),
            )
            return event
        return None

    def parse(self, on_token: TokenCallback) -> Generator[Awaitable, str, None]:

        ESC = "\x1b"
        read1 = self.read1
        get_ansi_sequence = ANSI_SEQUENCES.get
        more_data = self.more_data

        while not self.is_eof:
            character = yield read1()
            if character == ESC and ((yield self.peek_buffer()) or more_data()):
                sequence: str = character
                while True:
                    sequence += yield read1()
                    keys = get_ansi_sequence(sequence, None)
                    if keys is not None:
                        for key in keys:
                            on_token(events.Key(self.sender, key=key))
                        break
                    else:
                        mouse_match = _re_mouse_event.match(sequence)
                        if mouse_match is not None:
                            mouse_code = mouse_match.group(0)
                            event = self.parse_mouse_code(mouse_code, self.sender)
                            if event:
                                on_token(event)
                            break
            else:

                keys = get_ansi_sequence(character, None)
                if keys is not None:
                    for key in keys:
                        on_token(events.Key(self.sender, key=key))
                else:
                    on_token(events.Key(self.sender, key=character))


if __name__ == "__main__":
    parser = XTermParser()

    import os
    import sys

    for token in parser.feed(sys.stdin.read(20)):
        print(token)
