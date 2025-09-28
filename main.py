from fastapi import FastAPI,HTTPException
import subprocess
from pydantic import BaseModel
import requests
import base64
import dotenv
import os

dotenv.load_dotenv()

app = FastAPI()

FLOW_SERVICE_URL = os.getenv("FLOW_SERVICE_URL")
USERNAME = os.getenv("USERNAME") 
PASSWORD = os.getenv("PASSWORD")


class CommandReq(BaseModel):
    command: str

class SalesOrderRequest(BaseModel):
    metadata: dict
    request: dict
    

@app.post("/run")
def CommandRequest(req:CommandReq):
    try:
        result = subprocess.run(req.command, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=result.stderr)
        return {"output": result.stdout}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@app.post("/create-sales-order")
def create_sales_order(order: SalesOrderRequest):
    try:
        auth = (USERNAME, PASSWORD)

        response = requests.post(
            FLOW_SERVICE_URL,
            json=order.dict(),
            auth=auth, 
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        data = response.json()

        if "response" in data and "content" in data["response"]:
            try:
                # Add logging to see what we're trying to decode
                content = data["response"]["content"]
                data["response"]["rawContent"] = content  # Store original content for debugging
                
                # Fix padding issues before decoding
                missing_padding = len(content) % 4
                if missing_padding:
                    content += '=' * (4 - missing_padding)
                
                decoded_content = base64.b64decode(content).decode("utf-8")
                data["response"]["decodedContent"] = decoded_content
            except Exception as decode_error:
                # More detailed error message
                data["response"]["decodedContent"] = f"Could not decode content: {str(decode_error)}"

        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))