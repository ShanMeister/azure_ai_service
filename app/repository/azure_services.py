import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from loguru import logger


class AzureDocumentIntelligenceRepository:
    def __init__(self):
        # 初始化 DocumentIntelligenceClient
        self.client = DocumentIntelligenceClient(
            endpoint=os.getenv("DI_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("DI_API_KEY")),
            api_version=os.getenv("DI_API_VERSION")
        )
        self.submit_interval = os.getenv("DI_SUBMIT_INTERVAL")
        self.check_period = os.getenv("DI_CHECK_PERIOD")
        self.max_wait_time = os.getenv("DI_MAX_WAIT_TIME")
        self.batch_size = os.getenv("DI_BATCH_SIZE")
        self.main_loop_wait = os.getenv("DI_MAIN_LOOP_WAIT")

    async def extract_markdown(self, file_path: str) -> str:
        """調用 Azure Document Intelligence 來處理 PDF，並返回 Markdown。"""
        try:
            # 使用 DocumentIntelligenceClient 開始識別內容
            with open(file_path, "rb") as f:
                poller = self.client.begin_recognize_content(f)
                result = await poller.result()  # 等待處理結果

                if result.status == "succeeded":
                    return self.convert_to_markdown(result)
                else:
                    logger.error(f"Processing failed: {result.status}")
                    return "Document processing failed"
        except Exception as e:
            logger.error(f"Error during Document Intelligence API call: {e}")
            raise Exception(f"Document Intelligence API call failed: {e}")

    def convert_to_markdown(self, result) -> str:
        """將提取的資料轉換為 Markdown 格式。"""
        markdown_text = """# Extracted Document Content\n\n"""

        for page in result.analyze_result.pages:
            markdown_text += f"## Page {page.page_number}\n"
            for line in page.lines:
                markdown_text += f"{line.text}\n"
            markdown_text += "\n"

        return markdown_text

# class AzureLLM:
#     async def process_text(self, text: str, action: ActionEnum) -> str:
#         api_url = os.getenv("AZURE_LLM_API_URL")
#         headers = {"Authorization": f"Bearer {os.getenv('AZURE_LLM_KEY')}"}
#         payload = {
#             "text": text,
#             "action": action.value
#         }
#
#         async with aiohttp.ClientSession() as session:
#             async with session.post(api_url, json=payload, headers=headers) as resp:
#                 if resp.status != 200:
#                     raise Exception(f"Azure LLM API failed: {await resp.text()}")
#                 return await resp.text()
