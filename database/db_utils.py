import pandas_gbq

game_table_schema = [
    {'name': 'game_id', 'type': 'INTEGER'},
    {'name': 'show_num', 'type': 'INTEGER'}, 
    {'name': 'date', 'type': 'DATE'},
    {'name': 'clue_id', 'type': 'INTEGER'},
    {'name': 'clue_location', 'type': 'STRING'},
    {'name': 'round_num', 'type': 'INTEGER'},
    {'name': 'value', 'type': 'INTEGER'},
    {'name': 'order_num', 'type': 'INTEGER'},
    {'name': 'category', 'type': 'STRING'},
    {'name': 'answer', 'type': 'STRING'},
    {'name': 'correct_response', 'type': 'STRING'},
    {'name': 'name', 'type': 'STRING'},
    {'name': 'player_id', 'type': 'INTEGER'},
    {'name': 'was_correct', 'type': 'BOOLEAN'},
    {'name': 'was_revealed', 'type': 'BOOLEAN'},
    {'name': 'was_triple_stumper', 'type': 'BOOLEAN'},
    {'name': 'was_daily_double', 'type': 'BOOLEAN'},
    {'name': 'wager', 'type': 'INTEGER'}
]

def df_to_db(df, project_id, dataset, table_name, table_schema, if_exists):
    """
    Pushes a DataFrame to a database. By default uses BigQuery, but modifyable
    to fit database of choice.

    Args:
        df (pd.DataFrame): the DataFrame that will be pushed to the DB
        project_id (str): the DB project name
        dataset (str): the DB schema within the project
        table_name (str): the name of the table when saved to the DB
        table_schema (dict): [{'name': 'col1', 'type': 'STRING'},...]
        if_exists: replace, append, or fail

    Returns:
        None
    """
    pandas_gbq.to_gbq(dataframe=df, 
                      destination_table=dataset + '.' + table_name, 
                      project_id=project_id, 
                      if_exists=if_exists, 
                      table_schema=table_schema,
                      progress_bar=False)

    return None