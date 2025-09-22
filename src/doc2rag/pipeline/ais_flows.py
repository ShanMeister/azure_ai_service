import sys
import asyncio

# https://stackoverflow.com/questions/63860576/asyncio-event-loop-is-closed-when-using-asyncio-run
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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

def upload_async_flow():
    from doc2rag.config_utils import EmbeddingPoolConfig, AzureAISearchConfig
    from doc2rag.ai_search_async import main as upload_async_main

    sql_agent = SQLAgent()
    embedding_pool_config = EmbeddingPoolConfig()
    embedding_pool = embedding_pool_config.embedding_pool
    ais_config = AzureAISearchConfig()
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If an event loop is already running, use asyncio.create_task()
        asyncio.create_task(
            upload_async_main(sql_agent, embedding_pool, ais_config)
        )
    else:
        # If no event loop is running, start a new one
        asyncio.run(upload_async_main(sql_agent, embedding_pool, ais_config))


def delete_flow():
    from doc2rag.ai_search import DeleteController
    from doc2rag.delete import DeleteFilesAgent

    sql_agent = SQLAgent()
    DeleteController(sql_agent).delete()
    DeleteFilesAgent(sql_agent).delete_files()
