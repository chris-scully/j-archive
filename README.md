# Jeopardy Analytics
This is an in-development repository that will scrape, parse, perform analytics, 
and visualize data from j-archive.com.

## Scraping/Parsing J-Archive
To scrape and parse episodes from j-archive.com, first determine the game IDs
 you wish to analyze. This number can be found in the URL of the J-Archive 
 contest (i.e. https://j-archive.com/showgame.php?game_id=4000). Run 
 `python j_archive_scraper.py <first game_id> <last game_id>` to scrape and 
 parse episodes from all contests between those IDs.