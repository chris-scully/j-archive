import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import json

HTML_PARSER = 'html.parser'
ROBOTS_TXT_URL = 'http://www.j-archive.com/robots.txt'
EPISODE_BASE_URL = 'http://www.j-archive.com/showgame.php?game_id='


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
        response['responders'].append(no_response_dict)
        response['was_triple_stumper'] = True

    return response


def parse_value(clue_html):
    value = clue_html.select_one('.clue_value')
    dd_value = clue_html.select_one('.clue_value_daily_double')

    if dd_value:
        value = dd_value.text.replace('DD: ', '')
        is_dd = True
    else:
        value = value.text
        is_dd = False

    value = value.replace('$', '').replace(',', '')

    return {'value': value,
            'is_daily_double': is_dd}


def parse_clues(board_html):
    clues_html = board_html.select('.clue')

    clue_dicts = []
    for clue_html in clues_html:
        if clue_html.text.strip():
            value_dict = parse_value(clue_html)
            response_dict = parse_response(clue_html)

            answer = clue_html.select_one('.clue_text').text
            order_number = clue_html.select_one('.clue_order_number').text

            clue_dict = {'answer': answer,
                         'order_number': order_number}
            clue_dict.update(value_dict)
            clue_dict.update(response_dict)
        else:
            keys = ['answer', 'order_number', 'value', 'is_daily_double',
                    'correct_response', 'was_triple_stumper']
            clue_dict = {k: np.nan for k in keys}

        clue_dicts.append(clue_dict)

    return pd.DataFrame(clue_dicts)


def parse_rounds(page_soup):
    boards = page_soup.select('.round')

    clue_dfs = []
    for round_num, board in enumerate(boards):
        categories = category_name(board)
        clue_df = parse_clues(board)
        clue_df['category'] = categories * 5
        clue_df['round_num'] = round_num + 1
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

    df = pd.DataFrame(rows, columns=['name', 'response', 'value'])
    df['value'] = df['value'].str.replace('$','', regex=False).str.replace(',','', regex=False)
    df['answer'] = answer
    df['category'] = category
    df['correct_response'] = correct_response
    df['round_num'] = 3
    df['is_daily_double'] = False
    df['order_number'] = 1
    df['was_correct'] = df['name'].isin(correct_responders)
    df['was_triple_stumper'] = True if len(correct_responders) == 0 else False
    df.drop(columns=['response'], inplace=True)

    return df


def scrape_episode(scraper, episode_num):
    episode_url = EPISODE_BASE_URL + str(episode_num)
    page_html = scraper.get_page(episode_url)

    soup = BeautifulSoup(page_html, features=HTML_PARSER)

    rounds_df = parse_rounds(soup)
    rounds = rounds_df.to_json(orient='records')
    rounds = json.loads(rounds)
    rounds_df = pd.json_normalize(
        data = rounds,
        record_path = 'responders',
        meta=['answer', 'order_number', 'value', 'is_daily_double', 
              'correct_response', 'category', 'round_num', 'was_triple_stumper']
    )

    final_jep_df = parse_fj(soup)

    episode_df = pd.concat([rounds_df, final_jep_df], ignore_index=True)
    episode_df['was_revealed'] = np.where(episode_df['answer'].str.len()>0, True, False)
    episode_df['episode'] = episode_num

    col_order = ['episode', 'round_num', 'value', 'order_number', 'category',
                'answer', 'was_revealed', 'is_daily_double', 'correct_response',
                'name','was_correct', 'was_triple_stumper']
    episode_df = episode_df[col_order]
    episode_df.sort_values(by=['round_num', 'order_number'], inplace=True)

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
