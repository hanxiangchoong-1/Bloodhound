import os 
import aiohttp
from fastapi import HTTPException
from typing import Dict, Type, List
from enum import Enum
import logging
from openai import AsyncOpenAI
import asyncio
from urllib.parse import urljoin, urlparse

from webdataprocessors import BaseProcessor, CNAProcessor

logger = logging.getLogger(__name__)

class ProcessorType(str, Enum):
    BASE = "BASE"

dataprocessors: Dict[ProcessorType, Type[BaseProcessor]] = {
    ProcessorType.BASE: BaseProcessor
}

class Webscraper:
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    @staticmethod
    async def fetch_html(url: str, processor: ProcessorType) -> dict:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/'
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=60) as response:
                    response.raise_for_status()
                    html = await response.text()

            processor_class = dataprocessors.get(processor)
            if not processor_class:
                raise ValueError(f"Unknown processor type: {processor}")
            
            processor_instance = processor_class()
            processed_content = processor_instance.extract_content(html, url)
            return processed_content
        except aiohttp.ClientError as e:
            logger.error("Error fetching %s: %s", url, str(e))
            raise HTTPException(status_code=500, detail=str(e))
        except ValueError as e:
            logger.error("Processor error: %s", str(e))
            raise HTTPException(status_code=400, detail=str(e))
        
    @staticmethod
    async def choose_urls(urls: List[str], objective: str) -> List[str]:
        system_prompt='''
        "You are a web crawler assistant. Your task is to select the most relevant URLs based on the given objective. 
        Return the chosen url only like this:

        https://example.com
        '''
        prompt = f"Given the following URLs and the objective '{objective}', the most relevant URL:\n\n"
        prompt += "\n".join(urls)

        await asyncio.sleep(0.5)
        
        response = await Webscraper.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        chosen_url = response.choices[0].message.content.strip()
        return chosen_url

    @staticmethod
    async def crawl_recursive(url: str, depth: int, max_depth: int, objective: str, processor: ProcessorType) -> List[dict]:
        if depth > max_depth:
            return []

        try:
            content = await Webscraper.fetch_html(url, processor)
        except HTTPException:
            return []

        results = [content]

        urls = [link['href'] for link in content.get('links', [])]
 
        chosen_url = await Webscraper.choose_urls(urls, objective)

        # Small delay to prevent rate limiting errors
        await asyncio.sleep(0.1)

        if chosen_url:
            child_result = await Webscraper.crawl_recursive(chosen_url, depth + 1, max_depth, objective, processor)
            results.extend(child_result)

        return results

    @staticmethod
    async def crawl(start_url: str, max_path_length: int, objective: str, processor: ProcessorType) -> List[dict]:
        return await Webscraper.crawl_recursive(start_url, 1, max_path_length, objective, processor)