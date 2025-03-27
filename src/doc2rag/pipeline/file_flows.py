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


def file_initialize_flow():
    from doc2rag.initialize import Initializer

    Initializer().create_dirs()


def word_scan_flow():
    from doc2rag.file_scan import WORDScanner

    WORDScanner().scan_and_convert()


def ppt_scan_flow():
    from doc2rag.file_scan import PPTScanner

    PPTScanner().scan_and_convert()


def excel_scan_flow():
    from doc2rag.file_scan import EXCELScanner

    EXCELScanner().scan_and_convert()


def file_processing_flow():
    from doc2rag.file_scan import PDFScanner
    from doc2rag.file_split import FileSplitter
    # from doc2rag.pure_text import PureTextFileProcessor

    sql_agent = SQLAgent()
    PDFScanner(sql_agent).scan()
    FileSplitter(sql_agent).process_files()
    # PureTextFileProcessor(sql_agent).convert2markdown_and_chunking()


async def di_flow():
    from doc2rag.doc_intel import DIProcessor
    from doc2rag.page_split import SplitFilesProcessor
    from doc2rag.figure import FigureDescriptionGenerator
    from doc2rag.bundle import TextTableImageBundler, BundleStatusUpdateAgent
    # from doc2rag.chunking import ChunkGenerator

    sql_agent = SQLAgent()
    await DIProcessor(sql_agent).run()
    await SplitFilesProcessor(sql_agent).run()
    await FigureDescriptionGenerator(sql_agent).generate()
    merged_bundle = await TextTableImageBundler(sql_agent).bundle()
    return merged_bundle


def delete_flow():
    from doc2rag.delete import (
        ScanDeleteAgent,
        ScanDuplicateAgent,
        LabelChunksDeleteAgent,
    )

    sql_agent = SQLAgent()
    ScanDeleteAgent(sql_agent).scan_wait_for_delete()
    ScanDuplicateAgent(sql_agent).scan_exists_in_both_wait_done()
    LabelChunksDeleteAgent(sql_agent).label_chunks_for_delete()
