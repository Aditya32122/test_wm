from fastapi import FastAPI,HTTPException, Depends, Request, status
import subprocess
from pydantic import BaseModel
import requests
import base64
import dotenv
import os
import secrets
from fastapi.security import HTTPBasic, HTTPBasicCredentials



dotenv.load_dotenv()

app = FastAPI()
security = HTTPBasic()

# Hardcoded credentials
USERNAME = "admin"
PASSWORD = "secret123"


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



def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.post("/process")
async def process_data(
    request: Request,
    dir: str,  # query param: ?dir=I
    username: str = Depends(get_current_user),
):
    # Read raw plain text from body
    body_text = await request.body()
    body_text = body_text.decode("utf-8")

    return {
        "authenticated_user": username,
        "dir_param": dir,
        "received_text": body_text,
    }