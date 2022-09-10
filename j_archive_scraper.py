import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import json
from datetime import datetime, date

HTML_PARSER = 'html.parser'
ROBOTS_TXT_URL = 'http://www.j-archive.com/robots.txt'
EPISODE_BASE_URL = 'http://www.j-archive.com/showgame.php?game_id='

def parse_metadata(page_html):
    game_title = page_html.select_one('#game_title').text

    long_date = game_title[game_title.find(',')+2:]
    episode_date = datetime.strptime(long_date, '%B %d, %Y').date()

    show_num = game_title.split('#')[1].split(' ')[0]

    return {'date': episode_date,
            'show_num': show_num}


def category_name(board_html):
    category_names_html = board_html.select('.category_name')
    cats = []
    for category_name_html in category_names_html:
        cat = category_name_html.text
        cats.append(cat)

    return cats


def parse_response(clue_html):
    response_html = clue_html.find('div', {'onmouseover': True})['onmouseover']
    response_soup = BeautifulSoup(response_html, HTML_PARSER)

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


def parse_value(clue_html):
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


def parse_clues(board_html):
    clues_html = board_html.select('.clue')

    clue_dicts = []
    for clue_html in clues_html:
        if clue_html.text.strip():
            value_dict = parse_value(clue_html)
            response_dict = parse_response(clue_html)

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

def infer_clue_location(df):
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

def infer_missing_value(df, dt):
    money_multiple = 200 if dt >= date(2001, 11, 26) else 100
    df['value'].fillna(value = df['round_num'] \
                                * df['clue_location'].str[-1].astype(int) \
                                * money_multiple, 
                       inplace=True
                      )
    return df

def parse_rounds(page_soup, episode_date):
    boards = page_soup.select('.round')

    clue_dfs = []
    for round_num, board in enumerate(boards):
        categories = category_name(board)
        clue_df = parse_clues(board)
        clue_df['category'] = categories * 5
        clue_df['round_num'] = round_num + 1
        clue_df = infer_clue_location(clue_df)
        clue_df = infer_missing_value(clue_df, episode_date)
        clue_dfs.append(clue_df)

    return pd.concat(clue_dfs)


def parse_fj(page_soup):
    fj_board = page_soup.select_one('.final_round')
    category = fj_board.select_one('.category_name').text

    answer = fj_board.select_one('.clue_text').text

    response_html = fj_board.find('div', {'onmouseover': True})['onmouseover']
    response_soup = BeautifulSoup(response_html, HTML_PARSER)
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


def scrape_episode(scraper, episode_num):
    episode_url = EPISODE_BASE_URL + str(episode_num)
    page_html = scraper.get_page(episode_url)

    soup = BeautifulSoup(page_html, features=HTML_PARSER)

    meta = parse_metadata(soup)
    episode_date = meta['date']
    show_num = meta['show_num']

    rounds_df = parse_rounds(soup, episode_date)
    rounds = rounds_df.to_json(orient='records')
    rounds = json.loads(rounds)
    rounds_df = pd.json_normalize(
        data = rounds,
        record_path = 'responders',
        meta=['clue_id', 'clue_location', 'answer', 'order_num', 'value',
              'was_daily_double', 'correct_response', 'category', 'round_num', 
              'was_triple_stumper', 'wager', 'was_revealed']
    )

    final_jep_df = parse_fj(soup)
    episode_df = pd.concat([rounds_df, final_jep_df], ignore_index=True)

    episode_df['game_id'] = episode_num
    episode_df['date'] = episode_date
    episode_df['show_num'] = show_num

    col_order = ['show_num', 'game_id', 'date', 'clue_id', 'clue_location', 'round_num', 'value',
                'order_num', 'category','answer', 'correct_response', 'name', 
                'was_correct', 'was_revealed', 'was_triple_stumper', 
                'was_daily_double', 'wager']
    episode_df = episode_df[col_order]
    episode_df.sort_values(by=['round_num', 'order_num'], inplace=True)

    return episode_df


if __name__ == '__main__':
    import os
    from scraper import Scraper

    CSV_OUTPUT_DIR = 'data'

    j_scraper = Scraper(robots_txt_url=ROBOTS_TXT_URL)
    for i in range(4000, 4001):
        print(f'Scraping/parsing episode #{i}')
        episode_csv = os.path.join(CSV_OUTPUT_DIR, 'episode', f'show_{i}.csv')
        episode_df = scrape_episode(j_scraper, episode_num=i)
        episode_df.to_csv(episode_csv, index=False)
