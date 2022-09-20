import numpy as np
import pandas as pd
from datetime import datetime, date
from difflib import get_close_matches

def name_to_full_name_map(first_names: list, full_names_and_ids: dict) -> (dict, dict):
    """
    Maps first names returned by parsing the rounds to the full name found in
    the game metadata.

    Args:
        first_names (list): the first names found in the game
        full_names_and_ids (dict): the {full_name : id} parsed
            in the game metadata in parse_metadata()

    Returns:
        name_map (dict): first name to full name mapping
        id_map (dict): first name to id mapping
    """

    name_map = {}
    id_map = {}
    contestants_full_names = list(full_names_and_ids.keys())
    for first_name in first_names:
        name_map[first_name] = get_close_matches(first_name, 
                                                     possibilities=contestants_full_names, 
                                                     n=1, 
                                                     cutoff=0.01
                                                )[0]
        id_map[first_name] = full_names_and_ids[name_map[first_name]]

    return name_map, id_map


def infer_clue_location(df: pd.DataFrame) -> pd.DataFrame:
    """
    For clues where the board location is ambiguous in the HTML soup, this 
    function infers the location based on the order of clues.

    Args:
        df (pd.DataFrame): a dataframe of round data

    Returns:
        df (pd.DataFrame): a dataframe of round data with clue_location added
    """

    clue_locations = \
    ['J_1_1','J_2_1','J_3_1','J_4_1','J_5_1','J_6_1',
     'J_1_2','J_2_2','J_3_2','J_4_2','J_5_2','J_6_2',
     'J_1_3','J_2_3','J_3_3','J_4_3','J_5_3','J_6_3',
     'J_1_4','J_2_4','J_3_4','J_4_4','J_5_4','J_6_4',
     'J_1_5','J_2_5','J_3_5','J_4_5','J_5_5','J_6_5']

    df['clue_location'] = clue_locations
    df['clue_location'] = np.where(df['round_num'] == 2, 
                                   'D' + df['clue_location'],
                                   df['clue_location']
                                  )
    return df


def infer_missing_value(df: pd.DataFrame, dt: date) -> pd.DataFrame:
    """
    For clues where the clue value is ambiguous in the HTML soup (such as with
    daily doubles), this function infers the value based on the clue location.

    Args:
        df (pd.DataFrame): a dataframe of round data
        dt (date): the game date (from parse_metadata())

    Returns:
        df (pd.DataFrame): a dataframe of round data with missing 'value' inferred
    """

    money_multiple = 200 if dt >= date(2001, 11, 26) else 100
    df['value'].fillna(value = df['round_num'] \
                                * df['clue_location'].str[-1].astype(int) \
                                * money_multiple, 
                       inplace=True
                      )
    return df