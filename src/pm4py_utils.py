import datetime
import warnings
from typing import Any, Collection, List, Optional, Tuple, Union

import pandas as pd
from pm4py.objects.log.util import dataframe_utils
from pm4py.util import constants, pandas_utils, xes_constants

INDEX_COLUMN = "@@index"
CASE_INDEX_COLUMN = "@@case_index"


def my_format_dataframe(
    df: pd.DataFrame,
    case_id: str = constants.CASE_CONCEPT_NAME,
    activity_key: str = xes_constants.DEFAULT_NAME_KEY,
    timestamp_key: str = xes_constants.DEFAULT_TIMESTAMP_KEY,
    start_timestamp_key: str = xes_constants.DEFAULT_START_TIMESTAMP_KEY,
    timest_format: Optional[str] = None,
) -> pd.DataFrame:
    """
    Give the appropriate format on the dataframe, for process mining purposes

    :param df: Dataframe
    :param case_id: Case identifier column
    :param activity_key: Activity column
    :param timestamp_key: Timestamp column
    :param start_timestamp_key: Start timestamp column
    :param timest_format: Timestamp format that is provided to Pandas
    :rtype: ``pd.DataFrame``

    .. code-block:: python3

        import pandas as pd
        import pm4py

        dataframe = pd.read_csv('event_log.csv')
        dataframe = pm4py.format_dataframe(dataframe, case_id_key='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp', start_timestamp_key='start_timestamp', timest_format='%Y-%m-%d %H:%M:%S')
    """
    if timest_format is None:
        timest_format = constants.DEFAULT_TIMESTAMP_PARSE_FORMAT

    for col in df.columns:
        if col not in [case_id, timestamp_key, activity_key]:
            del df[col]

    if case_id not in df.columns:
        raise Exception(case_id + " column (case ID) is not in the dataframe!")
    if activity_key not in df.columns:
        raise Exception(activity_key + " column (activity) is not in the dataframe!")
    if timestamp_key not in df.columns:
        raise Exception(timestamp_key + " column (timestamp) is not in the dataframe!")
    if case_id != constants.CASE_CONCEPT_NAME:
        if constants.CASE_CONCEPT_NAME in df.columns:
            del df[constants.CASE_CONCEPT_NAME]
        df[constants.CASE_CONCEPT_NAME] = df[case_id]
        del df[case_id]
    if activity_key != xes_constants.DEFAULT_NAME_KEY:
        if xes_constants.DEFAULT_NAME_KEY in df.columns:
            del df[xes_constants.DEFAULT_NAME_KEY]
        df[xes_constants.DEFAULT_NAME_KEY] = df[activity_key]
        del df[activity_key]
    if timestamp_key != xes_constants.DEFAULT_TIMESTAMP_KEY:
        if xes_constants.DEFAULT_TIMESTAMP_KEY in df.columns:
            del df[xes_constants.DEFAULT_TIMESTAMP_KEY]
        df[xes_constants.DEFAULT_TIMESTAMP_KEY] = df[timestamp_key]
        del df[timestamp_key]
    # makes sure that the timestamps column are of timestamp type
    df = dataframe_utils.convert_timestamp_columns_in_df(
        df, timest_format=timest_format
    )
    # drop NaN(s) in the main columns (case ID, activity, timestamp) to ensure functioning of the
    # algorithms
    prev_length = len(df)
    df = df.dropna(
        subset={
            constants.CASE_CONCEPT_NAME,
            xes_constants.DEFAULT_NAME_KEY,
            xes_constants.DEFAULT_TIMESTAMP_KEY,
        },
        how="any",
    )

    if len(df) < prev_length:
        if constants.SHOW_INTERNAL_WARNINGS:
            warnings.warn(
                "Some rows of the Pandas data frame have been removed because of empty case IDs, activity labels, "
                "or timestamps to ensure the correct functioning of PM4Py's algorithms."
            )

    # make sure the case ID column is of string type
    df.loc[:, constants.CASE_CONCEPT_NAME] = df[constants.CASE_CONCEPT_NAME].astype(
        "string"
    )
    # make sure the activity column is of string type
    df.loc[:, xes_constants.DEFAULT_NAME_KEY] = df[
        xes_constants.DEFAULT_NAME_KEY
    ].astype("string")
    # set an index column
    df = pandas_utils.insert_index(df, INDEX_COLUMN, copy_dataframe=False)
    # sorts the dataframe
    df = df.sort_values(
        [constants.CASE_CONCEPT_NAME, xes_constants.DEFAULT_TIMESTAMP_KEY, INDEX_COLUMN]
    )
    # re-set the index column
    df = pandas_utils.insert_index(df, INDEX_COLUMN, copy_dataframe=False)
    # sets the index column in the dataframe
    df = pandas_utils.insert_case_index(df, CASE_INDEX_COLUMN, copy_dataframe=False)
    # sets the properties
    if not hasattr(df, "attrs"):
        # legacy (Python 3.6) support
        df.attrs = {}
    if start_timestamp_key in df.columns:
        df[xes_constants.DEFAULT_START_TIMESTAMP_KEY] = df[start_timestamp_key]
        df.attrs[constants.PARAMETER_CONSTANT_START_TIMESTAMP_KEY] = (
            xes_constants.DEFAULT_START_TIMESTAMP_KEY
        )
    df.attrs[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = xes_constants.DEFAULT_NAME_KEY
    df.attrs[constants.PARAMETER_CONSTANT_TIMESTAMP_KEY] = (
        xes_constants.DEFAULT_TIMESTAMP_KEY
    )
    df.attrs[constants.PARAMETER_CONSTANT_GROUP_KEY] = xes_constants.DEFAULT_GROUP_KEY
    df.attrs[constants.PARAMETER_CONSTANT_TRANSITION_KEY] = (
        xes_constants.DEFAULT_TRANSITION_KEY
    )
    df.attrs[constants.PARAMETER_CONSTANT_RESOURCE_KEY] = (
        xes_constants.DEFAULT_RESOURCE_KEY
    )
    df.attrs[constants.PARAMETER_CONSTANT_CASEID_KEY] = constants.CASE_CONCEPT_NAME
    return df
