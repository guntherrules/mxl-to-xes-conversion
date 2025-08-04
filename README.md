# mxl-to-xes-conversion

This repository contains a script to convert sheet music in MusicXML format to event logs in XES format.
Before running the script make sure you have pandas, music21 and pm4py installed. The standard configuration 
parses the MusicXML files note by note and each note is turned into an event.

The script has the following input arguments:

```--input_dir```: path to a folder containing MusicXML files

```--output_dir```: path to folder for storing output XES files

```--lifecycles```: the lifecycles you want to include in the XES files (either start, complete or both)

```--measure_as_event```: make events based on measures

```--show_octave```: use pitch range across all octaves

```--include_rests```: consider rests while parsing the input files

```--intervals```: make events based on intervals between notes

```--harmony_shift_as_event```: make events based on estimated keys for song segments

```--multi_case```: make each part into a separate case

```--lead_part_only```: only parse the top part of the input files

Example for conversion with lifecycles start and complete, full octave range and intervals as events:

```python3 ./src/main.py --input_dir "/path/to/mxl/files" --output_dir "/path/to/output/files" --lifecycles start,complete --show_octave --intervals```
