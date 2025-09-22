from pathlib import Path
import typer
from doc2rag.rag import RAGAgent

app = typer.Typer()


@app.command("simple-aoai")
def simple_aoai(question: str):
    """Perform simple-aoai action.

    Arguments:
    - question: The question to ask the RAGAgent.

    Example usage:
    - rag-cli simple-aoai "What is the capital of France?"
    """
    print(f"Question: {question}")
    print("LLM is generating the answer...")
    RAGAgent().simple_aoai(question)


@app.command()
def retrieve(
    index_name: str,
    question: str,
    doc_type: str = "Chunk",
    output_txt: Path = Path("retrieve_output.txt"),
):
    """
    Perform the retrieve action.

    This command retrieves an answer from the RAGAgent based on the provided index and question.

    Arguments:
    - index_name: The name of the index to search in.
    - question: The question to ask the RAGAgent.
    - doc_type: 'Chunk' or 'Figure'. Defaults to 'Chunk'.
    - output_txt: (Optional) A file path where the result will be saved.
                  This can be an absolute or relative path. Defaults to 'retrieve_output.txt'.

    Example usage:
    - rag-cli retrieve "index_name" "What is the capital of France?" --doc-type "Chunk" --output-txt "./output.txt"

    Note: The file will be saved using UTF-8 encoding, and if no file path is specified,
    it defaults to 'retrieve_output.txt' in the current directory.
    """

    # Display the question being processed
    print(
        f"Processing question: {question}, using index: {index_name}, document type: {doc_type}"
    )

    # Retrieve the result from the RAGAgent
    result = RAGAgent(index_name=index_name, document_type=doc_type).retrieve(question)

    # Ensure the provided path is correctly formatted for the OS
    output_path = output_txt.resolve()

    # Write the result to the output file in UTF-8 encoding
    output_path.write_text(result, encoding="utf-8")

    # Inform the user where the result has been written
    print(f"Output written to {output_path}")


@app.command()
def single_rag(
    index_name: str, question: str, output_txt: Path = Path("single_rag_output.txt")
):
    """
    Perform the single-rag action.

    This command retrieves a response from the RAGAgent using the single-rag method
    based on the provided index and question.

    Arguments:
    - index_name: The name of the index to search in.
    - question: The question to ask the RAGAgent.
    - output_txt: (Optional) A file path where the result will be saved.
                  This can be an absolute or relative path. Defaults to 'single_rag_output.txt'.

    Example usage:
    - rag-cli single-rag "index_name" "What is the capital of France?" --output-txt "./output.txt"

    Note: The file will be saved using UTF-8 encoding, and if no file path is specified,
    it defaults to 'single_rag_output.txt' in the current directory.
    """

    # Display the question being processed
    print(f"Processing question: {question}, using index: {index_name}")

    # Retrieve the result from the RAGAgent using the single_rag method
    result = RAGAgent(index_name=index_name).single_rag(question)

    # Ensure the provided path is correctly formatted for the OS
    output_path = output_txt.resolve()

    # Write the result to the output file in UTF-8 encoding
    output_path.write_text(result, encoding="utf-8")

    # Inform the user where the result has been written
    print(f"Output written to {output_path}")


if __name__ == "__main__":
    app()
