if __name__ == '__main__':
    import os
    import sys
    from scraper.scraper_config import ScraperConfig
    from scraper.episode_scraper import scrape_episode
    from database.db_utils import df_to_db, table_schema
    from database.db_conf import db_conf

    HTML_PARSER = 'html.parser'
    ROBOTS_TXT_URL = 'http://www.j-archive.com/robots.txt'
    EPISODE_BASE_URL = 'http://www.j-archive.com/showgame.php?game_id='

    start_ep_num = int(sys.argv[1])
    end_ep_num = int(sys.argv[2])

    project_id = db_conf['project-id']

    j_scraper = ScraperConfig(robots_txt_url=ROBOTS_TXT_URL)
    for i in range(start_ep_num, end_ep_num+1):
        print(f'Scraping/parsing episode #{i}')
        episode_df = scrape_episode(j_scraper, i, HTML_PARSER, EPISODE_BASE_URL)
        df_to_db(episode_df, project_id, 'temp', 'test_3', table_schema)
