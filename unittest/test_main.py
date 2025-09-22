import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from enum import Enum

class ActionEnum(str, Enum):
    summarize = "summarize"
    translate = "translate"
    qna = "qna"

class RealTimeActionEnum(str, Enum):
    summarize = "summarize"
    translate = "translate"
    chat = "chat"

def test_health_check(client):
    """
    測試 /health_check 是否正常回應
    """
    response = client.get("/health_check")
    assert response.status_code == 200
    assert response.json() == {"status": "Alive"}

@patch("main.handle_action", new_callable=AsyncMock)                # patch 1
@patch("main.DocumentRepository.create_document", new_callable=AsyncMock)  # patch 2
@patch("main.DocumentRepository.update_document", new_callable=AsyncMock)  # patch 3
@patch("main.DocumentRepository.get_document", new_callable=AsyncMock)     # patch 4
@patch("main.prompt_use_case.run_prompt", new_callable=AsyncMock)          # patch 5
def test_ai_service_valid_pdf(
    mock_run_prompt,           # patch 5
    mock_get_document,         # patch 4
    mock_update_document,      # patch 3
    mock_create_document,      # patch 2
    mock_handle_action,        # patch 1
    client):
    """
    測試 /ai_service 上傳正確 pdf 且 mock 資料庫與 AOAI 呼叫
    """
    mock_get_document.return_value = None
    mock_run_prompt.return_value = "mocked-aoai-response"
    mock_handle_action.return_value = "mocked-content"

    fake_session = MagicMock()
    fake_db = MagicMock()
    fake_db.get_session.return_value.__enter__.return_value = fake_session
    client.app.state.db = fake_db

    files = {'file': ('test.pdf', b'%PDF-1.4 dummy')}
    data = {
        'system_name': 'nuecs',
        'account_id': 'test-account',
        'document_id': 'doc-123',
        'response_language': 'en_US'
    }
    response = client.post("/ai_service", data=data, files=files)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "success"
    assert res_json["account_id"] == "test-account"
    assert res_json["document_id"] == "doc-123"
    assert res_json["message_response"]["summarize"] == "mocked-aoai-response"

    # mock_get_document.assert_awaited_once()
    # mock_create_document.assert_awaited_once()
    # # 確認 AOAI 有被呼叫兩次（summarize + qna）
    # assert mock_run_prompt.await_count >= 2

def test_ai_service_invalid_file(client):
    """
    測試 /ai_service 上傳錯誤副檔名
    """
    files = {'file': ('test.txt', b'this is dummy data')}
    data = {
        'system_name': 'nuecs',
        'account_id': 'test-account',
        'document_id': 'doc-123',
        'response_language': 'en_US'
    }
    response = client.post("/ai_service", data=data, files=files)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "error"
    assert "Invalid file format" in res_json["error_message"]

# def test_ai_service(client):
#     with open("unittest/test_data/sample_file.pdf", "rb") as f:
#         pdf_bytes = f.read()
#
#     files = {'file': ('sample_file.pdf', pdf_bytes)}
#     data = {
#         'system_name': 'nuecs',
#         'account_id': 'test-account',
#         'document_id': 'pdf-123',
#         'response_language': 'en_US'
#     }
#     response = client.post("/ai_service", data=data, files=files)
#     assert response.status_code == 200
#     res_json = response.json()
#     assert res_json["status"] == "success"
#     assert res_json["account_id"] == "test-account"
#     assert res_json["document_id"] == "pdf-123"
#     assert res_json["message_response"]["summarize"] is not None and res_json["message_response"][
#         "summarize"] != "", "Summarize should not be None or empty string"
#     assert res_json["message_response"]["qna"] is not None and res_json["message_response"][
#         "qna"] != "", "Qna should not be None or empty string"
#     assert res_json["message_response"]["processed_content"] is not None and res_json["message_response"][
#         "processed_content"] != "", "Processed_content should not be None or empty string"

def test_contract_search(client):
    data = {
        'system_name': 'nuecs',
        'message_request': 'test-winbond-contract',
        'document_count': 5
    }
    response = client.post("/contract_search", data=data)
    assert response.status_code == 200

def test_real_time_ai_service_summarize_with_file(client):
    with open("unittest/test_data/sample_file.pdf", "rb") as f:
        pdf_bytes = f.read()

    files = {'file': ('sample_file.pdf', pdf_bytes)}
    data = {
        'system_name': 'nuecs',
        'action': 'summarize',
        'account_id': 'test-account',
        'document_id': 'pdf-123',
        'response_language': 'en_US',
        'file_name': 'sample_file.pdf'
    }
    response = client.post("/real_time_ai_service", data=data, files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "success"
    assert res_json["action"] == RealTimeActionEnum.summarize
    assert res_json["account_id"] == "test-account"
    assert res_json["message_response"] is not None and res_json["message_response"] != "", "Summarize response should not be None or empty string"