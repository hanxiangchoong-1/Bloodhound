from datetime import datetime
import requests
from fastapi import HTTPException
from typing import Dict, Type
from enum import Enum
import logging

from webdataprocessors import BaseProcessor, CNAProcessor

# Assuming you're using the same logger setup as in the main file
logger = logging.getLogger(__name__)

class ProcessorType(str, Enum):
    CNA = "CNA"
    # Add other processor types here as needed

# This should be imported or defined here if it's used in this file
dataprocessors: Dict[ProcessorType, Type[BaseProcessor]] = {
    ProcessorType.CNA: CNAProcessor
    # Add other processors here
}

class Webscraper:
    @staticmethod
    def fetch_html(url: str, processor: ProcessorType) -> dict:
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
            
            processor_class = dataprocessors.get(processor)
            if not processor_class:
                raise ValueError(f"Unknown processor type: {processor}")
            
            processor_instance = processor_class()
            processed_content = processor_instance.process(response.text)
            
            return {
                "content": processed_content,
                "url": url,
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            logger.error("Error fetching %s: %s", url, str(e))
            raise HTTPException(status_code=500, detail=str(e))
        except ValueError as e:
            logger.error("Processor error: %s", str(e))
            raise HTTPException(status_code=400, detail=str(e))
