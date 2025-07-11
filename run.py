import os
import multiprocessing
import uvicorn
from dotenv import load_dotenv

load_dotenv('app/conf/.env')

if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)

    uvicorn.run(
        "main:app",
        host=os.getenv("APP_SERVER_HOST"),
        port=int(os.getenv("APP_SERVER_PORT")),
        workers=int(os.getenv("APP_SERVER_WORKER")),
        reload=False
    )