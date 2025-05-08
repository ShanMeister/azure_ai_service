from typing import List
from app.repository.ai_search_repository import AISearchRepository


class AISearchUseCase:
    def __init__(self):
        pass

    async def upload_single_document(
        self,
        id: str,
        file_id: str,
        file_name: str,
        content: str,
    ):
        doc = {
            "id": id,
            "file_id": int(file_id),
            "file_name": file_name,
            "content": content
        }

        """上傳單筆文件至 Azure Search"""
        async with AISearchRepository() as ai_search_repo:
            return await ai_search_repo.upload_document(doc)

    async def upload_bulk_documents(self, documents: List[dict]):
        """批次上傳文件至 Azure Search"""
        async with AISearchRepository() as ai_search_repo:
            return await ai_search_repo.upload_documents_bulk(documents)

    async def delete_document(self, id: str):
        """刪除單筆文件"""
        async with AISearchRepository() as ai_search_repo:
            return await ai_search_repo.delete_document(id)