from pathlib import Path
import base64

from sqlalchemy.orm import Session, joinedload
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion
from jinja2 import Template

from .db_utils.database import BaseSQLAgent
from .db_utils.models import Page, Figure, File, SplitFile
from .page_split import get_file_path
from .logger_utils import LoggingAgent
from .config_utils import (
    PathConfig,
    ImageAOAIConfig,
)


class FigureDescriptionGenerator:
    def __init__(self, sql_agent: BaseSQLAgent):
        self.logger = LoggingAgent("FigureDescriptionGenerator").logger
        self.gpt4o_agent = GPT4oImageDigestAgent()
        self.SessionLocal = sql_agent.SessionLocal
        self.path_config = PathConfig()

    def generate(self):
        """Generate descriptions for figures using GPT-4o."""
        with self.SessionLocal() as session:
            figures, file_dir_name_lst = self._fetch_figures_to_process(session)
            n_figures = len(figures)
            self.logger.info(f"Found {n_figures} figures without descriptions.")

            for progress, (figure, file_dir_name) in enumerate(
                zip(figures, file_dir_name_lst), start=1
            ):
                try:
                    raw_md_path = self._get_raw_md_path(
                        file_dir_name, figure.page_number
                    )
                    figure_path = self._get_figure_path(file_dir_name, figure)
                    description = self._generate_description(raw_md_path, figure_path)
                    self._save_description(session, figure, description)
                except Exception as e:
                    self.logger.error(f"Error: {e}, figure_path: {figure_path}")
                    self._save_description(
                        session, figure, "Error: Failed to generate description."
                    )
                self.logger.info(f"Progress: {progress}/{n_figures} figures processed.")

            self.logger.info("Finished generating descriptions for images.")

    def _generate_description(self, raw_md_path: Path, figure_path: Path) -> str:
        """Generate a description for the given figure using GPT-4o."""
        response = self.gpt4o_agent.gen_description(raw_md_path, figure_path).to_dict(
            mode="python"
        )
        return response["choices"][0]["message"]["content"]

    def _get_raw_md_path(self, file_dir_name: str, page_number: int) -> Path:
        """Construct the raw markdown file path for a given page number."""
        raw_md_dir_path = self.path_config.get_raw_md_dir_path(file_dir_name)
        raw_md_path = get_file_path(raw_md_dir_path, page_number, extension=".md")
        if not raw_md_path.exists():
            raise FileNotFoundError(f"Raw markdown file not found at {raw_md_path}")
        return raw_md_path

    def _get_figure_path(self, file_dir_name: str, figure: Figure) -> Path:
        """Get the path to the figure image file."""
        figure_dir_path = self.path_config.get_figure_dir_path(file_dir_name)
        figure_path = get_file_path(
            figure_dir_path,
            figure.page_number,
            figure.figure_id_in_page,
            extension=".png",
        )
        if not figure_path.exists():
            raise FileNotFoundError(f"Figure image file not found at {figure_path}")
        return figure_path

    def _fetch_figures_to_process(
        self, session: Session
    ) -> tuple[list[Figure], list[str]]:
        """
        Fetch figures with no descriptions and their corresponding file directory names.
        """
        query = (
            session.query(Figure, File.file_dir_name)
            .join(Page, Figure.page_id == Page.id)
            .join(SplitFile, Page.split_file_id == SplitFile.id)
            .join(File, SplitFile.file_id == File.id)
            .filter(Figure.description.is_(None))  # Filter figures with no description
            .options(
                joinedload(Figure.page)
                .joinedload(Page.split_file)
                .joinedload(SplitFile.file)  # Optimize relationship loading
            )
        )
        results = query.all()
        figures, file_dir_name_lst = zip(*results) if results else ([], [])
        return figures, file_dir_name_lst

    def _save_description(self, session: Session, figure: Figure, description: str):
        """Save the generated description to the database."""
        figure.description = description
        session.add(figure)
        session.commit()


class GPT4oImageDigestAgent:

    def __init__(self) -> None:
        self.config = ImageAOAIConfig()
        self.client = AzureOpenAI(
            api_key=self.config.api_key,
            azure_endpoint=self.config.endpoint,
            azure_deployment=self.config.deployment,
            api_version=self.config.api_version,
        )
        self.template = Template(
            """--- Start of Provided Info ---
{{ provided_info }}
--- End of Provided Info ---
Please describe the following image according to the provided context.
"""
        )

    def gen_description(
        self, refined_md_path: Path, image_path: Path
    ) -> ChatCompletion:
        return self.client.chat.completions.create(
            model="gpt-4o",
            messages=self.get_messages(refined_md_path, image_path),
        )

    def get_messages(self, refined_md_path: Path, image_path: Path) -> list[dict]:
        prompt = self._get_prompt(refined_md_path)
        base64_image = self._encode_image(image_path)
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ]

    def _get_prompt(self, refined_md_path: Path) -> str:
        with open(refined_md_path, "r", encoding="utf-8") as f:
            provided_info = f.read()
        return self.template.render(provided_info=provided_info)

    def _encode_image(self, image_path: Path) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
