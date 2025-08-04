import datetime as dt
import logging
import re
from typing import Any, Dict, Hashable, List

import music21
import pandas as pd
import pm4py
from music21.clef import Clef
from music21.duration import Duration
from music21.interval import Interval
from music21.key import KeySignature
from music21.meter import TimeSignature
from music21.tempo import TempoIndication
from pm4py.objects.log.obj import Event, EventLog, Trace

from conversion_methods.event_log import Case, EventIdHandler
from conversion_methods.song import Song
from utils import KeyAnalyzer

logger = logging.getLogger(__name__)


class LogMaker:
    """Object to transform one xml-file to an event log

    Attributes:
        -

    Methods:
        - get_timespans: get music21 timespan trees for song
        - make_event_for_each_lifecycle: make events for each lifecycle defined by user input for one muscial element
        - make_harmony_events: identify harmonic shifts and make them into events (only if harmony_shift_as_event is set)
        - group_events_by_measure: make measure events (only if measure_as_event is True)
        - get_pitch: get numeric pitch from a note limited to 12 base pitches
        - get_pitch_and_octave: get MIDI number of a note
        - get_interval: get number of semitones between two notes
        - get_rest
    """

    context_classes = [
        "Clef",
        "Instrument",
        "KeySignature",
        "SenzaMisuraTimeSignature",
        "TempoIndication",
        "TimeSignature",
        "Part",
    ]

    pitched_modules = [
        "music21.chord",
        "music21.note",
    ]

    start_time = dt.datetime(2024, 1, 1, 0, 0, 0)

    def __init__(
        self,
        song: Song,
        lifecycles: list[str],
        include_rests=False,
        harmony_shift_as_event=False,
        measure_as_event=False,
        multi_case=False,
        show_octave=False,
        intervals=False,
        lead_part_only=False,
    ):
        self.song = song
        self.cases = []

        self.harmony_shift_as_events = harmony_shift_as_event
        self.measure_as_event = measure_as_event
        self.multi_case = multi_case

        self.case_attribute_classes = self.context_classes
        self.event_attributes = self.context_classes

        self.lifecycles = lifecycles
        self.include_rests = include_rests
        self.show_octave = show_octave
        self.intervals = intervals
        self.lead_part_only = lead_part_only

        self.note_event_count = dict()
        self.measure_event_count = dict()

        self.base_event_variables = [
            "id",
            "name",
            "type",
            "timestamp",
            "lifecycle",
        ]

        self.id_handler = EventIdHandler()
        self.last_pitched_element = None
        print("Parsing mxl:")
        if not self.harmony_shift_as_events:
            self.cases = self.timespans_to_cases
            if self.lead_part_only:
                self.cases = [self.cases[0]]
        if self.harmony_shift_as_events and self.song.is_expandable:
            print("make harmony events")
            # if self.harmony_shift_as_events == "separate":
            case = Case(name="harmonic_shifts", attributes=None)
            case.trace.extend(self.make_harmony_events())
            self.cases = [case]
            # elif self.harmony_shift_as_events == "merged":
            #     for case in self.cases:
            #         harmony_events = self.make_harmony_events()
            #         case.trace.extend(harmony_events)

        print("Finished parsing mxl")

    def get_timespans(self) -> dict[Any, Any] | None:
        """Get timespan trees for whole song or separate parts

        :return: dictionary of timespan trees and their names
        """
        if not self.song.is_expandable:
            return None
        ts = dict()

        for part in self.song.expanded_parts:
            # name part according to instrument. name will be used as case name
            name = part.partName
            pattern = re.compile(re.escape(name) + ".*")
            used_names = list(ts.keys())
            new_suffix = sum([len(pattern.findall(s)) for s in used_names]) + 1
            new_name = name + " " + str(new_suffix)

            ts[new_name] = part.asTimespans()
            self.note_event_count[new_name] = 0
            self.measure_event_count[new_name] = 0

        return ts

    def make_event_for_each_lifecycle(
        self,
        name: str,
        event_type: str,
        measure: int | None,
        attributes: dict,
        timestamps: dict[str, dt.datetime],
    ) -> list[dict]:
        """

        :rtype: list of dictionaries with each dict representing an event
        """
        events = []

        for lifecycle, timestamp in timestamps.items():
            event = {
                "id": self.id_handler.get_id(),
                "name": name,
                "type": event_type,
                "timestamp": timestamp,
                "lifecycle": lifecycle,
                "measure": measure,
            }
            event.update(attributes)
            events.append(event)
        return events

    def make_harmony_events(self):
        self.note_event_count["harmonic_shifts"] = 0
        self.measure_event_count["harmonic_shifts"] = 0
        chordified_song = self.song.expanded_stream.chordify()
        measures = [
            m for m in chordified_song.getElementsByClass(music21.stream.Measure)
        ]
        num_measures = len(measures)

        ka = KeyAnalyzer(chordified_song)
        ka.windowSize = 1
        estimated_keys = ka.getRawKeyByMeasure()

        assert len(estimated_keys) == num_measures

        base_key = chordified_song.analyze("key")
        base_scale = base_key.getScale(base_key.mode)
        scale_intervals = [
            Interval(base_scale.getTonic(), p).semitones
            for p in base_scale.getPitches()
        ]

        events = []
        last_harmony = {"roman_numeral": None, "mode": None}
        last_key = base_key
        timestamps = dict()

        if "start" in self.lifecycles:
            timestamps["start"] = self.start_time

        for measure_idx in range(0, len(estimated_keys)):
            key = estimated_keys[measure_idx]
            if key is None:
                print("no key detected in current measure. use last seen key")
                key = last_key
            last_key = key
            scale_degree = base_scale.getScaleDegreeFromPitch(key.getTonic())

            if scale_degree is None:
                semitonal_distance = (
                    12
                    + music21.interval.Interval(
                        base_scale.getTonic(), key.getTonic()
                    ).semitones
                ) % 12
                scale_degree = (
                    len([x for x in scale_intervals if x < semitonal_distance]) + 0.5
                )

            current_harmony = {"roman_numeral": scale_degree, "mode": key.mode}

            if (
                last_harmony != current_harmony
                or measure_idx == len(estimated_keys) - 1
            ) and measure_idx > 0:
                context_measure = measures[measure_idx]

                tempo = context_measure.getContextByClass("music21.tempo.MetronomeMark")
                if tempo is None:
                    tempo = music21.tempo.MetronomeMark(
                        number=80, referent=music21.note.Note(type="quarter")
                    )

                if "complete" in self.lifecycles:
                    timestamps["complete"] = self.start_time + dt.timedelta(
                        seconds=tempo.durationToSeconds(context_measure.offset)
                    )

                event = self.make_event_for_each_lifecycle(
                    name=self.m21_obj_to_str(key),
                    event_type="harmonic_shift",
                    measure=measure_idx,
                    attributes=last_harmony,
                    timestamps=timestamps,
                )

                if "start" in self.lifecycles:
                    duration = context_measure.highestTime
                    timestamps["start"] = self.start_time + dt.timedelta(
                        seconds=tempo.durationToSeconds(
                            context_measure.offset + duration
                        )
                    )

                events.extend(event)
                self.measure_event_count["harmonic_shifts"] += 1
            last_harmony = current_harmony
        return events

    def group_events_by_measure(
        self, events: list[dict]
    ) -> list[dict[str, Any]] | None:
        df = pd.DataFrame(events)
        transformed_events = []
        self.id_handler.reset()
        if df.empty:
            return None

        for measure, events_in_measure in df.groupby("measure"):
            for lifecycle, lc_events_in_measure in events_in_measure.groupby(
                "lifecycle"
            ):
                event = {
                    "name": "_".join(lc_events_in_measure["name"].to_list()),
                    "id": self.id_handler.get_id(),
                    "type": "measure",
                    "lifecycle": lifecycle,
                    "measure": measure,
                }

                if lifecycle == "start":
                    event["timestamp"] = lc_events_in_measure["timestamp"].min()
                else:
                    event["timestamp"] = lc_events_in_measure["timestamp"].max()

                attributes = dict()
                for attribute_label in self.event_attributes:
                    attribute_group = lc_events_in_measure[
                        attribute_label
                    ].value_counts()
                    if len(attribute_group) > 0:
                        attributes[attribute_label] = attribute_group.idxmax()

                event.update(attributes)
                transformed_events.append(event)

        return transformed_events

    def m21_obj_to_str(self, attribute):
        """Improve readibility of attributes like key signature etc"""
        str_repr = str(attribute)

        if isinstance(
            attribute, (KeySignature, TimeSignature, TempoIndication, Clef, Duration)
        ):
            str_repr = str_repr.split(".")[-1].replace(">", "")
        return str_repr

    @property
    def timespans_to_cases(self) -> list[Any] | None:
        timespans = self.get_timespans()
        if timespans is None:
            return None
        traces = dict()

        for case_name, ts in timespans.items():
            self.last_pitched_element = None
            trace = []
            events = []
            previous_measure = None
            offset = 0

            for timed_element in ts:
                element = timed_element.element
                module = getattr(element, "__module__")

                # make consecutive measure numbers in repeats
                orig_measure_number = timed_element.measureNumber
                measure_number = orig_measure_number
                if orig_measure_number is not None:
                    measure_number = orig_measure_number + offset
                    if (
                        previous_measure is not None
                        and orig_measure_number < previous_measure
                    ):
                        offset = previous_measure
                        measure_number = measure_number + offset

                    previous_measure = orig_measure_number

                # Timestamps
                tempo = element.getContextByClass("music21.tempo.MetronomeMark")
                if tempo is None or tempo.getQuarterBPM() is None:
                    tempo = music21.tempo.MetronomeMark(
                        number=80, referent=music21.note.Note(type="quarter")
                    )

                timestamps = dict()
                timestamp_offsets = {
                    "start": timed_element.offset,
                    "complete": timed_element.endTime,
                }

                for lifecycle in self.lifecycles:
                    timestamps[lifecycle] = self.start_time + dt.timedelta(
                        seconds=tempo.durationToSeconds(timestamp_offsets[lifecycle])
                    )

                # Attributes
                attributes = dict()
                for event_attr_class in self.event_attributes:
                    attributes[event_attr_class] = self.m21_obj_to_str(
                        element.getContextByClass(event_attr_class)
                    )
                attributes["Part"] = case_name

                if isinstance(element, music21.note.Unpitched):
                    continue

                if module in self.pitched_modules:
                    if not element.isRest:
                        event_type = "pitch"
                        if not self.intervals and self.show_octave:
                            event_names = self.get_pitch_and_octave(element)
                        elif self.intervals:
                            event_names = self.get_interval(element)
                            event_type = "interval"
                        else:
                            event_names = self.get_pitch(element)
                    elif element.isRest and self.include_rests:
                        event_names = self.get_rest(element)
                        event_type = "rest"
                    else:
                        event_names = None
                        event_type = None

                    if event_names is not None:
                        for name in event_names:
                            self.note_event_count[case_name] += 1
                            events.extend(
                                self.make_event_for_each_lifecycle(
                                    str(name),
                                    event_type=event_type,
                                    measure=measure_number,
                                    attributes=attributes,
                                    timestamps=timestamps,
                                )
                            )

            if self.measure_as_event:
                measure_events = self.group_events_by_measure(events)
                if measure_events is not None:
                    trace.extend(measure_events)
                    self.measure_event_count[case_name] += len(measure_events) / len(
                        self.lifecycles
                    )
            else:
                trace.extend(events)

            traces[case_name] = sorted(trace, key=lambda e: e["timestamp"])

        cases = []

        if not self.multi_case:
            case = Case(name=self.song.name, attributes=None)
            for case_name in timespans.keys():
                case.trace.extend(traces[case_name])
            cases.append(case)
            self.measure_event_count[self.song.name] = sum(
                self.measure_event_count.values()
            )
            self.note_event_count[self.song.name] = sum(self.note_event_count.values())

        else:
            for case_name in timespans.keys():
                case = Case(name=case_name, attributes=None)
                case.trace.extend(traces[case_name])
                cases.append(case)

        return cases

    def convert_trace(self, case: Case) -> Trace:
        # build a trace object
        trace = Trace()
        # to add attributes to a trace, use the .attribute member of the trace
        # .attributes is a dictionary
        trace.attributes["concept:name"] = case.name
        if case.attributes is not None:
            for key, attr in case.attributes.items():
                trace.attributes[key] = attr

        for event in case.trace:
            e = Event()
            e["concept:name"] = event["name"]
            e["time:timestamp"] = event["timestamp"]
            e["lifecycle:transition"] = event["lifecycle"]
            e["type"] = event["type"]
            e["id"] = event["id"]
            for key, attr in event.items():
                if key not in self.base_event_variables:
                    e[key] = attr
            trace.append(e)
        return trace

    def convert_to_log(self):
        event_log = EventLog(**{"attributes": {"concept:name": self.song.name}})
        traces = []
        for case in self.cases:
            traces.append(self.convert_trace(case))
        event_log._list = traces
        return event_log

    def export_logfile(self, output_path):
        pm4py.write_xes(
            self.convert_to_log(),
            output_path,
            "concept:name",
            extensions=["Lifecycle", "Time", "Concept"],
        )

    def get_pitch(self, element):
        event_names = []
        # event_name = "%s-%s" % (pitch_name, str(element.duration.quarterLength))
        if element.isChord:
            for pitch in element.sortAscending().pitches:
                event_name = str(pitch.pitchClass)
                event_names.append(event_name)
        else:
            event_names.append(str(element.pitch.pitchClass))
        return event_names

    def get_pitch_and_octave(self, element):
        event_names = []
        if element.isChord:
            for pitch in element.sortAscending().pitches:
                event_name = str(pitch.midi)
                event_names.append(event_name)
        else:
            event_names.append(str(element.pitch.midi))
        return event_names

    def get_interval(self, element):
        if element.isChord:
            pitch = element.sortAscending().pitches[-1]
        else:
            pitch = element

        if self.last_pitched_element is None:
            self.last_pitched_element = pitch
            return None

        interval = music21.interval.Interval(self.last_pitched_element, pitch)
        if self.show_octave:
            event_name = interval.semitones
        else:
            event_name = abs(interval.semitones) % 12 * interval.direction
        self.last_pitched_element = pitch
        return [event_name]

    def get_rest(self):
        event_names = ["rest"]
        return event_names
