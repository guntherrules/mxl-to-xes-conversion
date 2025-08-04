import datetime as dt
import logging
import os
import pathlib
from pathlib import Path

import music21
from music21 import converter
from music21.repeat import Expander
from music21.stream import Stream
from music21.stream.base import Part

logger = logging.getLogger(__name__)


class Song:

    def __init__(self, filepath: Path) -> object:
        self.filepath = filepath
        self.filename = filepath.name  # with suffix .mxl
        self.name = filepath.stem

        try:
            self.stream = converter.parse(self.filepath)
        except:
            self.stream = None

        if self.stream is not None:
            self.parts = self.stream.parts

            self.is_expandable = self.check_is_expandable()
            self.expanded_stream = None
            self.expanded_parts = None
            self.expand()
        self.genre = None

    def expand(self) -> list[Part] | None:
        if self.is_expandable:
            self.expanded_stream = self.stream.expandRepeats()
            self.expanded_parts = self.expanded_stream.parts
            # TODO: raise error if expanded part lengths vary
        else:
            return
        return

    def check_is_expandable(self) -> bool:
        for part in self.parts:
            if (
                Expander(part).isExpandable() is None
                or Expander(part).isExpandable() == True
            ):
                continue
            elif not Expander(part).isExpandable():
                return False
        return True


dynamics_class = [  # event
    "Diminuendo",
    "Dynamic",
    "DynamicWedge",
]

instrument_class = [  # case attribute (multi part) or event attribute (merged parts)
    "Instrument",
]

clef_class = [  # event attribute
    "Clef",
]

key_signature_class = [  # event attribute
    "KeySignature",
]

time_signature_class = [  # event attribute
    "SenzaMisuraTimeSignature",
    "TimeSignature",
]

tempo_class = [  # event attribute
    "TempoIndication",
]
