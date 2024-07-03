from datetime import datetime
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from pythonjsonlogger import jsonlogger
import uvicorn

LOGSTASH_URL = "http://logstash:5044"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.handlers[0].setFormatter(jsonlogger.JsonFormatter())

class URLRequest(BaseModel):
    """Pydantic model for URL request."""
    url: str

class Webscraper:
    @staticmethod
    def fetch_html(url):
        """
        Fetch and parse HTML content from a given URL.
        Returns a dict with content, URL, and timestamp.
        Raises HTTPException on request errors.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/'
        }
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            return {
                "content": BeautifulSoup(response.text, 'html.parser').get_text(separator=' ', strip=True),
                "url": url,
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching %s: %s", url, str(e))
            raise HTTPException(status_code=500, detail=str(e))

app = FastAPI()
@app.post("/fetch_html")
async def fetch_html(request: URLRequest, req: Request):
    """
    Fetch HTML content from the provided URL and send to Logstash.
    Returns the fetched document with added IP address.
    """
    document = Webscraper.fetch_html(request.url)
    document["ip_address"] = req.client.host
    try:
        requests.post(LOGSTASH_URL, json={"type": "html_content", "document": document}, timeout=60)
    except Exception as e:
        logger.error("Error posting to Logstash: %s", str(e))
    logger.info("Fetched content from URL: %s", request.url)
    return document

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)