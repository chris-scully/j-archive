import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

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

    correct_responder_soup = response_soup.select_one('.right')
    if correct_responder_soup:
        correct_responder = correct_responder_soup.text
        is_correct = True
    else: 
        correct_responder = None
        is_correct = False

    incorrect_responders_soup = response_soup.select('.wrong')
    if incorrect_responders_soup:
        incorrect_responders = []
        for incorrect_responder in incorrect_responders_soup:
            incorrect_responder = incorrect_responder.get_text(' ', strip=True)
            if incorrect_responder != 'Triple Stumper':
                incorrect_responders.append(incorrect_responder)
        incorrect_responders = incorrect_responders if len(incorrect_responders)>0 else None
    else:
        incorrect_responders = None

    return {'correct_response': correct_response,
            'correct_responder': correct_responder,
            'incorrect_responders': incorrect_responders,
            'is_correct': is_correct}


def parse_value(clue_html):
    value = clue_html.select_one('.clue_value')
    dd_value = clue_html.select_one('.clue_value_daily_double')

    if dd_value:
        value = dd_value.text.replace('DD: ', '')
        is_dd = True
    else:
        value = value.text
        is_dd = False

    value = value.replace('$', '')

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
                    'correct_response', 'correct_responder', 'incorrect_responders', 
                    'is_correct']
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

    df = pd.DataFrame(rows, columns=['responder', 'response', 'value'])
    df['answer'] = answer
    df['category'] = category
    df['correct_response'] = correct_response
    df['round_num'] = 3
    df['correct_responder'] = None
    df['incorrect_responders'] = None
    df['is_daily_double'] = False
    df['order_number'] = 1
    df['is_correct'] = df['responder'].isin(correct_responders)
    df.loc[df['is_correct'], 'correct_responder'] = df['responder']
    df.loc[~df['is_correct'], 'incorrect_responders'] = df['responder']
    df.drop(columns=['responder', 'response'], inplace=True)

    return df


def scrape_episode(scraper, episode_num):
    episode_url = EPISODE_BASE_URL + str(episode_num)
    page_html = scraper.get_page(episode_url)

    soup = BeautifulSoup(page_html, features=HTML_PARSER)

    rounds_df = parse_rounds(soup)
    final_jep_df = parse_fj(soup)

    episode_df = pd.concat([rounds_df, final_jep_df], ignore_index=True)
    episode_df['episode'] = episode_num
    episode_df = episode_df.explode(column='incorrect_responders', ignore_index=True)
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
