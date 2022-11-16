if __name__ == '__main__':
    import sys
    from os import path
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
        try:
            episode_df = scrape_episode(j_scraper, episode_num, HTML_PARSER, EPISODE_BASE_URL)
            df_to_db(df=episode_df, 
                    project_id=project_id, 
                    dataset='dev_question_data', 
                    table_name='question_data', 
                    table_schema=game_table_schema, 
                    if_exists=if_exists
                    )
        except Exception as e:
            path_to_log = path.join('log', 'scraper_error_game_id_log.txt')
            log = open(path_to_log, 'a')
            log.write(str(episode_num)+'\n')
            log.close()
            print('\tError Episode #'+str(episode_num)+':', e)
