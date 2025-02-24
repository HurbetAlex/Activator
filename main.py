from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
import os
import logging
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

MONGO_URI = os.environ.get('MONGO_URI')
DB_NAME = "activation"
COLLECTION_NAME = "keys"
SCRIPT_PATH = "activation_script.ps1"

app = FastAPI()

logging.info("Connecting to MongoDB ...")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
logging.info("Connected to MongoDB successfully")


def get_activation_script():
    logging.info("Getting activation script ...")
    if os.path.exists(SCRIPT_PATH):
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            logging.info("Activation script file found")
            return f.read()
    logging.info("Activation script file not found")
    return None


@app.get("/get-script", response_model=str)
def get_script(key: str = Query(..., title="Activation key")):
    logging.info(f"Received get request for key: {key}")
    logging.info("Checking key in MongoDB ...")
    result = collection.find_one({"key": key})

    if result:
        max_uses = result.get("max_uses", 3)
        current_uses = result.get("uses", 0)

        if current_uses >= max_uses:
            logging.warning("Key has reached maximum usage limit")
            raise HTTPException(status_code=403, detail="Key has reached maximum usage limit")

        logging.info("Found key in MongoDB, incrementing usage count")
        collection.update_one({"key": key}, {"$set": {"uses": current_uses + 1}})

        script_result = get_activation_script()
        if script_result:
            logging.info("Returning activation script")
            return script_result
        logging.error("Activation script could not be retrieved")
        raise HTTPException(status_code=500, detail="Activation script not found")
    else:
        logging.warning("Key not in MongoDB")
        raise HTTPException(status_code=404, detail="Key not in MongoDB")


if __name__ == "__main__":
    logging.info("Starting server ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
