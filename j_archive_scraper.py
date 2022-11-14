if __name__ == '__main__':
    import os
    import sys
    from scraper.utils.scraper import Scraper
    from scraper.episode_scraper import scrape_episode
    from database.db_utils import df_to_db, game_table_schema
    from database.db_conf import db_conf

    HTML_PARSER = 'html.parser'
    ROBOTS_TXT_URL = 'http://www.j-archive.com/robots.txt'
    EPISODE_BASE_URL = 'http://www.j-archive.com/showgame.php?game_id='

    start_ep_num = int(sys.argv[1])
    end_ep_num = int(sys.argv[2])
    if_exists = sys.argv[3]

    project_id = db_conf['project-id']

    j_scraper = Scraper(robots_txt_url=ROBOTS_TXT_URL)
    for episode_num in range(start_ep_num, end_ep_num+1):
        print(f'Scraping/parsing episode #{episode_num}')
        episode_df = scrape_episode(j_scraper, episode_num, HTML_PARSER, EPISODE_BASE_URL)
        df_to_db(df=episode_df, 
                 project_id=project_id, 
                 dataset='dev_game_data', 
                 table_name='game_data', 
                 table_schema=game_table_schema, 
                 if_exists=if_exists
                )
