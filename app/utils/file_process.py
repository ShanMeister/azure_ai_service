import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from dotenv import load_dotenv
from app.utils.logger import logger

load_dotenv('app/conf/.env')

from src.doc2rag.config_utils import PathConfig

BUNDLE_SAVE_FILE=os.getenv("FINAL_BUNDLE_PATH")

class FileProcessClass:
    def __init__(self):
        self.path_config = PathConfig()
        pass

    async def save_upload_file(self, uploaded_file: UploadFile, save_path: str):
        """儲存上傳的檔案到指定路徑"""
        try:
            with open(save_path, "wb") as buffer:
                buffer.write(uploaded_file.file.read())
            return save_path
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    def merge_bundle(self, file_dir_name: str):
        logger.info(f"Merging markdown bundle files...")
        bundle_md_dir_path = self.path_config.get_bundle_md_dir_path(file_dir_name)

        md_files = sorted(
            [f for f in os.listdir(bundle_md_dir_path) if f.endswith(".md")]
        )

        if not md_files:
            raise FileNotFoundError("No Markdown file in target path！")

        try:
            merged_content = ""

            for file in md_files:
                file_path = os.path.join(bundle_md_dir_path, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    merged_content += f"##{content}\n\n---\n\n"

            # result_dir = r"C:\projects\NuECS\result"
            save_path = os.path.join(BUNDLE_SAVE_FILE, f"{file_dir_name}.md")
            os.makedirs(BUNDLE_SAVE_FILE, exist_ok=True)
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(merged_content)
                logger.info(f" Success to save .md at {save_path}...")
            except Exception as e:
                logger.error(f"Error saving bundle file, saving path doesn't exist.")

            return merged_content
        except Exception as e:
            logger.error(f"Error saving bundle file: {e}")
            return None
