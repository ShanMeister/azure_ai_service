from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from src.doc2rag.pipeline.file_flows import file_processing_flow, di_flow, word_scan_flow

scheduler = AsyncIOScheduler()


async def run_ai_service_pipeline():
    merged_bundle = None
    logger.info("AI service pipeline execution started.")
    word_scan_flow()
    file_processing_flow()
    merged_bundle = await di_flow()
    logger.info("AI service pipeline execution completed.")
    return merged_bundle

# def schedule_pipeline():
#     """設定每日執行 pipeline"""
#     scheduler.add_job(run_pipeline, "cron", hour=0, minute=0)
#     scheduler.start()
#     logger.info("Scheduler started: Pipeline will run every day at 00:00.")
