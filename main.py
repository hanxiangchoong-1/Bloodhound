import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
from pythonjsonlogger import jsonlogger
import uvicorn
from webcrawler import Webscraper, ProcessorType

LOGSTASH_URL = "http://logstash:5044"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.handlers[0].setFormatter(jsonlogger.JsonFormatter())

class URLRequest(BaseModel):
    """Pydantic model for URL request."""
    url: str
    processor: ProcessorType

app = FastAPI()

@app.post("/fetch_html")
async def fetch_html(request: URLRequest, req: Request):
    """
    Fetch HTML content from the provided URL and send to Logstash.
    Returns the fetched document with added IP address.
    """
    document = Webscraper.fetch_html(request.url, request.processor)
    document["ip_address"] = req.client.host
    try:
        requests.post(LOGSTASH_URL, json={"type": "html_content", "document": document}, timeout=60)
    except Exception as e:
        logger.error("Error posting to Logstash: %s", str(e))
    logger.info("Fetched content from URL: %s", request.url)
    return document

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)