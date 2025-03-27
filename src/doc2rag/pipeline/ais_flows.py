from doc2rag.config_utils import SQLTypeConfig

# Map SQL types to corresponding agent classes
SQL_AGENT_MAPPING = {
    "sqlite": "doc2rag.db_utils.database.SQLiteAgent",
    "mssql": "doc2rag.db_utils.database.MSSQLAgent",
}

# Retrieve SQL type from configuration
sql_type = SQLTypeConfig().sql_type

if sql_type in SQL_AGENT_MAPPING:
    module_name, class_name = SQL_AGENT_MAPPING[sql_type].rsplit(".", 1)
    SQLAgent = getattr(__import__(module_name, fromlist=[class_name]), class_name)
else:
    raise ValueError(
        f"Invalid SQL type '{sql_type}' in config file. "
        f"Supported types are: {', '.join(SQL_AGENT_MAPPING.keys())}."
    )


def upload_flow():
    from doc2rag.ai_search import UploadController

    sql_agent = SQLAgent()
    UploadController(sql_agent).upload()


def delete_flow():
    from doc2rag.ai_search import DeleteController
    from doc2rag.delete import DeleteFilesAgent

    sql_agent = SQLAgent()
    DeleteController(sql_agent).delete()
    DeleteFilesAgent(sql_agent).delete_files()
