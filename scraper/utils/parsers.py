import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, date
from difflib import get_close_matches


def parse_metadata(page_html: BeautifulSoup) -> dict:
    """
    Parses the metadata about a particular game
    i.e. date, show number, contestants' names/ids

    Args:
        page_html (BeautifulSoup HTML object): the soup created by scraping
            one Jeopardy game

    Returns:
        (dict): containing episode date (date), show number (str), and 
            contestants' named and ids (dict)
    """

    game_title = page_html.select_one('#game_title').text

    long_date = game_title[game_title.find(',')+2:]
    episode_date = datetime.strptime(long_date, '%B %d, %Y').date()

    show_num = game_title.split('#')[1].split(' ')[0]

    contestants = page_html.select('.contestants')
    contestants_dict = {}
    for contestant in contestants:
        full_name = contestant.text.split(',')[0]
        player_id = contestant.a['href'].split('=')[1]
        contestants_dict[full_name] = player_id

    return {'date': episode_date,
            'show_num': show_num,
            'contestants': contestants_dict}


def parse_category_name(board_html: BeautifulSoup) -> list:
    """
    Parses category names from a round board

    Args:
        board_html (BeautifulSoup): the soup from one round

    Returns:
        cats (list): a list of round categories
    """

    category_names_html = board_html.select('.category_name')
    cats = []
    for category_name_html in category_names_html:
        cat = category_name_html.text
        cats.append(cat)

    return cats


def parse_value(clue_html: BeautifulSoup) -> dict:
    """
    Parses the clue values of non-Daily Double clues

    Args:
        clue_html (BeautifulSoup): the soup from one clue

    Returns:
        (dict): value (str) of the clue's value, was_daily_double (bool) 
            indicating whether the clue was a daily double, and wager (str) for 
            daily doubles only
    """

    value = clue_html.select_one('.clue_value')
    dd_value = clue_html.select_one('.clue_value_daily_double')

    if dd_value:
        value = None
        is_dd = True
        wager = dd_value.text \
                        .replace('DD: ', '') \
                        .replace('$', '')    \
                        .replace(',', '')
    else:
        value = value.text.replace('$', '').replace(',', '')
        is_dd = False
        wager = None

    return {'value': value,
            'was_daily_double': is_dd,
            'wager': wager}


def parse_response(clue_html: BeautifulSoup, html_parser: str) -> dict:
    """
    Parses the correct responders, responders (with name and whether correct),
    and whether the clue was a triple stumper.

    Args:
        clue_html (BeautifulSoup): the soup from one clue
        html_parser (str): configuration on how to parse the HTML

    Returns:
        response (dict): containing correct_response (str), 
            responders (list containing name of responder and boolean correct),
            and was_triple_stumper (bool)
    """

    response_html = clue_html.find('div', {'onmouseover': True})['onmouseover']
    response_soup = BeautifulSoup(response_html, html_parser)

    correct_response_soup = response_soup.select_one('.correct_response')
    correct_response = correct_response_soup.text

    response = {
        'correct_response': correct_response,
        'responders': [],
        'was_triple_stumper': False
    }

    correct_responder_soup = response_soup.select_one('.right')
    if correct_responder_soup:
        correct_response_dict = {
            'name': correct_responder_soup.text, 
            'was_correct': True
        }
        response['responders'].append(correct_response_dict)

    incorrect_responders_soup = response_soup.select('.wrong')
    if incorrect_responders_soup:
        for incorrect_responder in incorrect_responders_soup:
            if incorrect_responder.text == 'Triple Stumper':
                response['was_triple_stumper'] = True
            else:
                incorrect_response_dict = {
                    'name': incorrect_responder.text,
                    'was_correct': False
                }
                response['responders'].append(incorrect_response_dict)
        
    if not response['responders']:
        no_response_dict = {
                    'name': None,
                    'was_correct': None
        }
        response['responders'] = [no_response_dict]
        response['was_triple_stumper'] = True

    return response


def parse_clues(board_html: BeautifulSoup, html_parser: str) -> pd.DataFrame:
    """
    Parses all information from all clues and also applies the parse_value() and 
    parse_value() functions. Converts from dictionaries to a dataframe.

    Args:
        board_html (BeautifulSoup): the soup from one round
        html_parser (str): configuration on how to parse the HTML

    Returns:
        (pd.DataFrame): a dataframe containing the following clue fields:
            'clue_id', 'clue_location', 'answer', 'order_num', 'value',
            'was_daily_double', 'wager', 'correct_response', 'responders',
            'was_triple_stumper', 'responders', 'was_revealed'
    """

    clues_html = board_html.select('.clue')

    clue_dicts = []
    for clue_html in clues_html:
        if clue_html.text.strip():
            value_dict = parse_value(clue_html)
            response_dict = parse_response(clue_html, html_parser)

            clue_id = clue_html.a['href'].split('=')[-1]
            answer = clue_html.select_one('.clue_text').text
            order_num = clue_html.select_one('.clue_order_number').text

            clue_dict = {'clue_id': clue_id,
                         'answer': answer,
                         'order_num': order_num,
                         'was_revealed': True}
            clue_dict.update(value_dict)
            clue_dict.update(response_dict)
        else:
            keys = ['clue_id', 'clue_location', 'answer', 'order_num', 
                    'value', 'was_daily_double', 'wager',
                    'correct_response', 'responders', 'was_triple_stumper']
            clue_dict = {k: np.nan for k in keys}
            clue_dict['responders'] = [{'name': None, 'was_correct': None}]
            clue_dict['was_revealed'] = False

        clue_dicts.append(clue_dict)

    return pd.DataFrame(clue_dicts)


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


def parse_rounds(page_soup: BeautifulSoup, episode_date: date, \
                 html_parser: str) -> pd.DataFrame:
    """
    Parses over all rounds in the game. Calls parse_clues() and
    parse_category_name().

    Args:
        page_soup (BeautifulSoup): the full page of soup from one game
        episode_date (date): the game date (from parse_metadata()) 
        html_parser (str): configuration on how to parse the HTML

    Returns:
        (pd.DataFrame): a dataframe of round data
    """

    boards = page_soup.select('.round')

    clue_dfs = []
    for round_num, board in enumerate(boards):
        categories = parse_category_name(board)
        clue_df = parse_clues(board, html_parser)
        clue_df['category'] = categories * 5
        clue_df['round_num'] = round_num + 1
        clue_df = infer_clue_location(clue_df)
        clue_df = infer_missing_value(clue_df, episode_date)
        clue_dfs.append(clue_df)

    return pd.concat(clue_dfs)


def parse_fj(page_soup: BeautifulSoup, html_parser: str) -> pd.DataFrame:
    """
    A parser for Final Jeopardy.

    Args:
        page_soup (BeautifulSoup): the full page of soup from one game
        html_parser (str): configuration on how to parse the HTML

    Returns:
        pd.DataFrame: a dataframe of Final Jeopardy data
    """

    fj_board = page_soup.select_one('.final_round')
    category = fj_board.select_one('.category_name').text

    answer = fj_board.select_one('.clue_text').text

    response_html = fj_board.find('div', {'onmouseover': True})['onmouseover']
    response_soup = BeautifulSoup(response_html, html_parser)
    correct_responders = response_soup.select('.right')
    correct_responders = [cr.text for cr in correct_responders]

    correct_response = response_soup.select('em')[-1].text

    rows = []
    row = []
    response_table = response_soup.select('tr')
    for row_i, tr in enumerate(response_table):
        td = tr.find_all('td')
        contents = [tr.text for tr in td]
        if row_i % 2 == 0:
            row = contents
        else:
            row += contents
            rows.append(row)

    df = pd.DataFrame(rows, columns=['name', 'response', 'wager'])
    df['wager'] = df['wager'].str.replace('$','', regex=False).str.replace(',','', regex=False)
    df['clue_id'] = None
    df['clue_location'] = 'FJ'
    df['answer'] = answer
    df['category'] = category
    df['correct_response'] = correct_response
    df['round_num'] = 3
    df['was_daily_double'] = False
    df['order_num'] = 1
    df['was_correct'] = df['name'].isin(correct_responders)
    df['was_triple_stumper'] = True if len(correct_responders) == 0 else False
    df['value'] = None
    df['was_revealed'] = True
    df.drop(columns=['response'], inplace=True)

    return df

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

col_order_and_dtypes = {
    'game_id': 'float', 
    'show_num': 'float', 
    'date': 'datetime64[ns]', 
    'clue_id': 'float', 
    'clue_location': 'str', 
    'round_num': 'float', 
    'value': 'float', 
    'order_num': 'float', 
    'category': 'str',
    'answer': 'str', 
    'correct_response': 'str', 
    'name': 'str', 
    'player_id': 'float', 
    'was_correct': 'bool', 
    'was_revealed': 'bool', 
    'was_triple_stumper': 'bool', 
    'was_daily_double': 'bool', 
    'wager': 'float'
}
    