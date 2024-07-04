import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
from pythonjsonlogger import jsonlogger
import uvicorn
from webcrawler import Webscraper, ProcessorType

LOGSTASH_URL = "http://logstash:5044"

class URLRequest(BaseModel):
    url: str
    processor: ProcessorType

class CrawlRequest(BaseModel):
    start_url: str
    max_path_length: int
    objective: str
    processor: ProcessorType

class LogstashHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        try:
            requests.post(LOGSTASH_URL, json={"type": "app_log", "message": log_entry}, timeout=60)
        except Exception as e:
            logger.error("Error posting log to Logstash: %s", str(e))

app = FastAPI()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(console_handler)

# Logstash handler
logstash_handler = LogstashHandler()
logstash_handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(logstash_handler)

@app.post("/fetch_html")
async def fetch_html(request: URLRequest, req: Request):
    """
    Fetch HTML from url and send to Logstash.
    """
    document = await Webscraper.fetch_html(request.url, request.processor)
    document["ip_address"] = req.client.host
    try:
        requests.post(LOGSTASH_URL, json={"type": "html_content", "document": document}, timeout=60)
    except Exception as e:
        logger.error("Error posting to Logstash: %s", str(e))
    logger.info("Fetched content from URL: %s", request.url)
    return document

@app.post("/crawl")
async def crawl(request: CrawlRequest, req: Request):
    """
    Crawl websites starting from url, uses scrape to get content.
    """
    results = await Webscraper.crawl(
        request.start_url,
        request.max_path_length,
        request.objective,
        request.processor
    )
    
    # Create a single object with numbered documents
    crawl_result = {
        "ip_address": req.client.host,
        "start_url": request.start_url,
        "objective": request.objective,
        "max_path_length": request.max_path_length,
        "documents": {f"doc_{i}": doc for i, doc in enumerate(results, 1)},
        "total_documents": len(results)
    }
    
    try:
        requests.post(LOGSTASH_URL, json={"type": "html_content", "document": crawl_result}, timeout=60)
        # requests.post(LOGSTASH_URL, json={"type": "content_path", "document": crawl_result}, timeout=60)
    except Exception as e:
        logger.error("Error posting to Logstash: %s", str(e))
    
    logger.info("Crawled %d pages starting from URL: %s", len(results), request.start_url)
    return crawl_result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)