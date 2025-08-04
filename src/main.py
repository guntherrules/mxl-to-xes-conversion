import argparse
import logging
import os
import shutil
from pathlib import Path

from conversion_methods.mxl_parser import LogMaker
from conversion_methods.song import Song
from utils import validate_log


def list_of_strings(arg):
    return arg.split(",")


parser = argparse.ArgumentParser()

parser.add_argument(
    "--input_dir",
    type=Path,
    help="path to folder containing mxl files",
)

parser.add_argument(
    "--output_dir",
    type=Path,
    help="path to folder for storing xes-files",
)

parser.add_argument(
    "--lifecycles",
    type=list_of_strings,
    help="list containing start, complete or both as strings",
)

parser.add_argument(
    "--measure_as_event",
    action="store_true",
    help="uses notes as events if false and measure if True",
)

parser.add_argument(
    "--show_octave",
    action="store_true",
    help="shows octaves for pitches",
)

parser.add_argument(
    "--include_rests",
    action="store_true",
    help="includes rests in event log if True",
)

parser.add_argument(
    "--intervals",
    action="store_true",
    help="names events after intervals between notes intead of pitchnames",
)

parser.add_argument(
    "--harmony_shift_as_event",
    action="store_true",
    help="adds harmony shifts to each case",
)

parser.add_argument(
    "--multi_case",
    action="store_true",
    help="makes each part a separate case if true. Only makes sense if merge_parts is False",
)

parser.add_argument(
    "--lead_part_only",
    action="store_true",
    help="only use first part",
)


if __name__ == "__main__":
    logname = "mxlConverter.log"
    logging.basicConfig(filename="mxlConverter_conf5.log", level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Started")

    args = parser.parse_args()

    files = os.listdir(args.input_dir)
    processed_files = os.listdir(args.output_dir)
    good, bad = 0, 0

    exception_dir = os.path.join(args.output_dir, "exceptions")
    too_big_dir = os.path.join(exception_dir, "large_files")

    if not os.path.exists(exception_dir):
        os.makedirs(exception_dir)

    if not os.path.exists(too_big_dir):
        os.makedirs(too_big_dir)

    MAX_FILESIZE = 10000

    for file in files:
        print(file)

        filesize = os.path.getsize(Path(os.path.join(args.input_dir, file)))
        src = os.path.join(args.input_dir, file)
        dst = os.path.join(exception_dir, file)

        if file.replace(".mxl", ".xes") in processed_files:
            print("Song %s already processed." % file)
            continue

        if filesize > MAX_FILESIZE:
            print("Song %s file too big" % file)
            shutil.copyfile(src, os.path.join(too_big_dir, file))
            bad += 1
            continue

        song = Song(Path(os.path.join(args.input_dir, file)))

        if song.stream is None:
            logger.warning("No parsing: %s" % file)
            shutil.copyfile(src, dst)
            print("Song %s could not be parsed" % file)
            bad += 1
            continue

        elif not song.is_expandable:
            logger.warning("Not expandable: %s" % file)
            shutil.copyfile(src, dst)
            print("Song %s is not expandable" % file)
            bad += 1

        else:
            parser = LogMaker(
                song,
                lifecycles=args.lifecycles,
                multi_case=args.multi_case,
                measure_as_event=args.measure_as_event,
                harmony_shift_as_event=args.harmony_shift_as_event,
                show_octave=args.show_octave,
                include_rests=args.include_rests,
                intervals=args.intervals,
                lead_part_only=args.lead_part_only,
            )
            new_filename = file.replace(".mxl", ".xes")
            output_path = os.path.join(args.output_dir, new_filename)
            if parser.cases is not None:
                parser.export_logfile(output_path)
                counter = parser.note_event_count
                if args.measure_as_event or args.harmony_shift_as_event:
                    counter = parser.measure_event_count
                validate_log(output_path, counter, len(args.lifecycles))
                good += 1
            else:
                logger.warning("Unknown error: %s" % file)
                bad += 1

            del song
        print(good, bad)
