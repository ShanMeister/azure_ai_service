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

def file_processing_flow():
    from doc2rag.file_scan import PDFScanner
    from doc2rag.file_split import FileSplitter
    from doc2rag.pure_text import PureTextFileProcessor

    sql_agent = SQLAgent()
    PDFScanner(sql_agent).scan()
    FileSplitter(sql_agent).process_files()
    PureTextFileProcessor(sql_agent).convert2markdown_and_chunking()


def di_flow():
    from doc2rag.doc_intel import DIProcessor
    from doc2rag.page_split import SplitFilesProcessor
    from doc2rag.figure import FigureDescriptionGenerator
    from doc2rag.bundle import TextTableImageBundler, BundleStatusUpdateAgent
    from doc2rag.chunking import ChunkGenerator

    sql_agent = SQLAgent()
    DIProcessor(sql_agent).run()
    SplitFilesProcessor(sql_agent).run()
    FigureDescriptionGenerator(sql_agent).generate()
    TextTableImageBundler(sql_agent).bundle()
    # BundleStatusUpdateAgent(sql_agent).update_split_files_status()
    # ChunkGenerator(sql_agent).generate()