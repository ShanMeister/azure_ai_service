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
import typer

app = typer.Typer(
    help="Document Digestion CLI. Remember to adjust config.yml file before running the commands."
)


@app.command()
def initialize():
    """Initialize the directories."""
    from doc2rag.initialize import Initializer

    Initializer().create_dirs()


@app.command("scan-files")
def scan_files():
    """Scans directories and processes PDF files for text and text-image data."""
    from doc2rag.file_scan import PDFScanner

    sql_agent = SQLAgent()
    PDFScanner(sql_agent).scan()


@app.command("split-files")
def split_files():
    """Split PDF files into smaller files."""
    from doc2rag.file_split import FileSplitter

    sql_agent = SQLAgent()
    FileSplitter(sql_agent).process_files()


@app.command("di-analyze")
def di_analyze():
    """Perform document intelligence analysis."""
    from doc2rag.doc_intel import DIProcessor

    sql_agent = SQLAgent()
    DIProcessor(sql_agent).run()


@app.command("split-pages")
def split_pages():
    """Split PDF files into individual pages."""
    from doc2rag.page_split import SplitFilesProcessor

    sql_agent = SQLAgent()
    SplitFilesProcessor(sql_agent).run()


@app.command("fig-gen-desc")
def fig_gen_description():
    """Generate descriptions for figures."""
    from doc2rag.figure import FigureDescriptionGenerator

    sql_agent = SQLAgent()
    FigureDescriptionGenerator(sql_agent).generate()


@app.command("bundle")
def bundle():
    """Bundle text, tables, and images."""
    from doc2rag.bundle import TextTableImageBundler, BundleStatusUpdateAgent

    sql_agent = SQLAgent()
    TextTableImageBundler(sql_agent).bundle()
    BundleStatusUpdateAgent(sql_agent).update_split_files_status()


@app.command("chunking")
def chunking():
    """
    Perform chunking.
    """
    from doc2rag.chunking import ChunkGenerator

    sql_agent = SQLAgent()
    ChunkGenerator(sql_agent).generate()


@app.command("process-pure-text")
def process_pure_text():
    """Process pure text files."""
    from doc2rag.pure_text import PureTextFileProcessor

    sql_agent = SQLAgent()
    PureTextFileProcessor(sql_agent).convert2markdown_and_chunking()


if __name__ == "__main__":
    app()
