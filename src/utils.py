import datetime as dt
import logging
import os
import pathlib
import random

import music21
import pandas as pd
import pm4py
from music21 import key, stream
from music21.stream import Stream

from pm4py_utils import my_format_dataframe

logger = logging.getLogger(__name__)


def validate_log(path_to_log, event_count: dict, lifecycle_count):
    log = pm4py.objects.log.importer.xes.importer.apply(path_to_log)
    for trace in log:
        assert "concept:name" in trace.attributes  # Every trace should have a case ID
        assert event_count[trace.attributes["concept:name"]] * lifecycle_count == len(
            trace
        )
        for event in trace:
            assert "concept:name" in event  # Event name exists
            assert "time:timestamp" in event  # Timestamp exists


class KeyAnalyzer(music21.analysis.floatingKey.KeyAnalyzer):
    def getRawKeyByMeasure(self):
        keyByMeasure = []
        for i in range(self.numMeasures):
            # now `m` is a measure-slice of the entire stream
            # use 4 measure window to determine key of current measure
            m = self.stream.measures(i, i + 3, indicesNotNumbers=True)
            if m is None or not m.recurse().notes:
                k = None
            else:
                k = m.analyze("key")
            keyByMeasure.append(k)
        self.rawKeyByMeasure = keyByMeasure
        return keyByMeasure

    # def smoothInterpretationByMeasure(self):
    #     smoothedKeysByMeasure = []
    #     algorithm = self.weightAlgorithm
    #
    #     for i in range(self.numMeasures):
    #         baseInterpretations = self.getInterpretationByMeasure(i)
    #         if baseInterpretations is None:
    #             smoothedKeysByMeasure.append(None)
    #             continue
    #         for j in range(-1 * self.windowSize, self.windowSize + 1):  # -2, -1, 0, 1, 2 etc.
    #             mNum = i + j
    #             if mNum < 0 or mNum >= self.numMeasures or mNum == i:
    #                 continue
    #             newInterpretations = self.getInterpretationByMeasure(mNum)
    #             if newInterpretations is not None:
    #                 for k in baseInterpretations:
    #                     coefficient = algorithm(newInterpretations[k], j)
    #                     baseInterpretations[k] += coefficient
    #         bestName = max(baseInterpretations, key=baseInterpretations.get)
    #         smoothedKeysByMeasure.append(key.Key(bestName))
    #
    #     return smoothedKeysByMeasure
