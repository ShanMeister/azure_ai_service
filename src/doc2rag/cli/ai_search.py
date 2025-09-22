import typer


app = typer.Typer(
    help="AI Search CLI, include the action and index name. Action can be create-index, delete-index, scan-wait-for-upload, scan-wait-for-delete"
)


@app.command("create-index")
def create_index():
    """Create an index using IndexAgent."""
    from doc2rag.ai_search import IndexAgent

    IndexAgent().create_indices()


@app.command("delete-index")
def delete_index():
    """Delete an index using IndexAgent."""
    from doc2rag.ai_search import IndexAgent

    IndexAgent().delete_index()


if __name__ == "__main__":
    app()
