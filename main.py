from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
from requests.exceptions import HTTPError, RequestException
import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime
import uvicorn
from bs4 import BeautifulSoup

def html_to_text(html_content):
    # Create a BeautifulSoup object
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Get all the text from the HTML
    text = soup.get_text(separator=' ', strip=True)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text


def send_log_to_logstash(log_data):
    try:
        requests.post(LOGSTASH_URL, json={"type": "app_log", "log": log_data})
    except Exception as e:
        print(f"Failed to send log to Logstash: {e}")

# Replace your current logging setup with this:
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LogstashHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        send_log_to_logstash(log_entry)

handler = LogstashHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

LOGSTASH_URL = "http://logstash:5044"

class Webscraper:
    @staticmethod
    def fetch_html(url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/'
        }
        session = requests.Session()
        try:
            response = session.get(url, headers=headers)
            response.raise_for_status()
            document = {
                        "content": html_to_text(response.text), 
                        "url": url,
                        "timestamp": datetime.utcnow().isoformat()
                    }
            return document

        except requests.exceptions.MissingSchema:
            logger.error(f"Invalid URL (no schema): {url}")
            raise ValueError("Invalid URL: No schema supplied. Perhaps you meant 'http://' or 'https://'.")
        except requests.exceptions.InvalidURL:
            logger.error(f"Invalid URL (malformed): {url}")
            raise ValueError("Invalid URL: The URL is malformed.")
        except HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            if response.status_code == 403:
                raise HTTPError(f"HTTP 403 Forbidden error: {http_err}. You might be blocked.")
            else:
                raise HTTPError(f"HTTP error occurred: {http_err}")
        except RequestException as req_err:
            logger.error(f"Request error occurred: {req_err}")
            raise RequestException(f"Request error occurred: {req_err}")
        except Exception as e:
            logger.error(f"Request error occurred: {e}")
            raise RequestException(f"Request error occurred: {e}")

app = FastAPI()

class URLRequest(BaseModel):
    url: str

@app.post("/fetch_html")
async def fetch_html(request: URLRequest, req: Request):
    try:
        document = Webscraper.fetch_html(request.url)
        document["ip_address"] = req.client.host
        log_data = {"type": "html_content", "document": document}
        
        # Send HTML content to Logstash
        try:
            requests.post(LOGSTASH_URL, json=log_data)
        except Exception as e:
            logger.error(f"Failed to send HTML content to Logstash: {e}")

        logger.info(f"Fetched content from URL: {request.url}")
        return document
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPError as he:
        raise HTTPException(status_code=500, detail=str(he))
    except RequestException as re:
        raise HTTPException(status_code=500, detail=str(re))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)