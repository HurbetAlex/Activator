from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
import os
import random
import string
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

def generate_key():
    parts = ["".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
    return "-".join(parts)

def get_activation_script():
    logging.info("Getting activation script ...")
    if os.path.exists(SCRIPT_PATH):
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            logging.info("Activation script file found")
            return f.read()
    logging.info("Activation script file not found")
    return None

@app.get("/activation", response_model=str)
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

@app.post("/create-key")
def create_key(comment: str = Query(..., title="Comment for the key")):
    new_key = generate_key()
    collection.insert_one({"key": new_key, "uses": 0, "max_uses": 3, "comment": comment})
    logging.info(f"New key created: {new_key} with comment: {comment}")
    return {"key": new_key, "comment": comment}

if __name__ == "__main__":
    logging.info("Starting server ...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=443,
        ssl_keyfile="/etc/letsencrypt/live/msactivation.cloud/privkey.pem",
        ssl_certfile="/etc/letsencrypt/live/msactivation.cloud/fullchain.pem"
    )
