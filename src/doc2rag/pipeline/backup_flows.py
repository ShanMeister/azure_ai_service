from doc2rag.config_utils import SQLTypeConfig
from doc2rag.backup_utils import BackupManager

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


def daily_backup_flow():
    sql_agent = SQLAgent()
    backup_manager = BackupManager(sql_agent)
    backup_manager.schedule_new_backups()
    backup_manager.process_pending_backups()
    backup_manager.mark_for_deletion()
    backup_manager.process_deletions()
