from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.doc2rag.pipeline.file_flows import file_processing_flow, di_flow, word_scan_flow
from src.doc2rag.pipeline.ais_flows import upload_flow
from app.utils.logger import logger

scheduler = AsyncIOScheduler()

async def run_ai_service_pipeline():
    merged_bundle = None
    logger.info("AI service pipeline execution started.")
    word_scan_flow()
    file_processing_flow()
    merged_bundle = await di_flow()
    upload_flow()
    logger.info("AI service pipeline execution completed.")
    return merged_bundle

async def run_delete_contract_pipeline():
    merged_bundle = None
    logger.info("Contract deletion pipeline execution started.")
    upload_flow()
    logger.info("Contract deletion pipeline execution completed.")
    return merged_bundle

# def schedule_pipeline():
#     """設定每日執行 pipeline"""
#     scheduler.add_job(run_pipeline, "cron", hour=0, minute=0)
#     scheduler.start()
#     logger.info("Scheduler started: Pipeline will run every day at 00:00.")
