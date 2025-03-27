import typer

from doc2rag.db_utils.models import File, Figure, Chunk
from db_utils.sqlite.database import SQliteAgent


app = typer.Typer(help="SQL Database CLI")

file_app = typer.Typer(help="File (files) Table CLI")
app.add_typer(file_app, name="file")

chunk_app = typer.Typer(help="Chunk (chunks) Table CLI")
app.add_typer(chunk_app, name="chunk")

figure_app = typer.Typer(help="Figure (figures) Table CLI")
app.add_typer(figure_app, name="figure")


@file_app.command("list")
def list_files():
    """
    List all files in the database.

    Example usage:
    sqldb-cli file list
    """
    with SQliteAgent().SessionLocal() as session:
        files = session.query(File).all()
        print("id | filename")
        for file in files:
            print(f"{file.id} | {file.file_name}")


@chunk_app.command("change-status")
def chunk_change_status(file_id: int, status: str):
    """
    Change the status of chunks with the given file_id.
    There are four possible statuses: "wait-for-upload", "uploaded", "wait-for-delete", "deleted".

    Example usage:
    sqldb-cli chunk change-status 1 "wait-for-upload"
    """
    print(f"Start performing change-status for file_id: {file_id} to {status}")
    with SQliteAgent().SessionLocal() as session:
        chunks = session.query(Chunk).filter_by(file_id=file_id).all()
        for chunk in chunks:
            chunk.status = status
        session.commit()
    print("Done.")


@figure_app.command("change-status")
def figure_change_status(file_id: int, status: str):
    """
    Change the status of figures with the given file_id.
    There are four possible statuses: "wait-for-upload", "uploaded", "wait-for-delete", "deleted".

    Example usage:
    sqldb-cli figure change-status 1 "wait-for-upload"
    """
    print(f"Start performing change-status for file_id: {file_id} to {status}")
    with SQliteAgent().SessionLocal() as session:
        figures = session.query(Figure).filter_by(file_id=file_id).all()
        for figure in figures:
            figure.status = status
        session.commit()
    print("Done.")
