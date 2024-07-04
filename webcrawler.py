import os 
import aiohttp
from fastapi import HTTPException
from typing import Dict, Type, List
from enum import Enum
import logging
from openai import AsyncOpenAI
import asyncio
from urllib.parse import urljoin, urlparse
import re

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
    async def filter_urls(urls: List[str]) -> List[str]:
        system_prompt = '''
        You are a URL filter. Your task is to analyze a list of URLs and remove any that are unlikely to lead to articles or sources of information.
        Remove URLs that lead to:
        1. User pages
        2. Edit pages
        3. Discussion or talk pages
        4. Special pages (e.g., search, recent changes)
        5. File uploads
        6. Language selection pages
        7. Login/logout pages
        8. Any other non-content pages

        Return only the filtered list of URLs, each on a new line.
        '''
        prompt = "Filter the following URLs, keeping only those likely to lead to articles or information sources:\n\n"
        prompt += "\n".join(urls)

        await asyncio.sleep(0.5)

        response = await Webscraper.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        filtered_urls = response.choices[0].message.content.strip().split('\n')
        return filtered_urls
    
    @staticmethod
    async def choose_urls(urls: List[str], objective: str, visited: List[str]) -> List[str]:
        system_prompt='''
        "You are an investigator. Your objective is provided. Your task is to find out as much information as possible about it. 
        To do this, you will be given a set of urls. You must choose the URL that you judge most likely to lead to the information you seek, eventually.
        None of the links may be directly relevant. The challenge is to choose the link likeliest to lead to future relevant links.
        The url you choose will be followed, and another set of urls presented to a future version of you.
        Find the truth. Godspeed.
 
        Return the chosen url only, like this:

        https://example.com

        If there are no relevant URLs, then return this token:
        TERMINATE
        '''
        if len(visited)>0:
            visited_string=', '.join(visited)
        else:
            visited_string='NONE'
        prompt = f'''
        These are the links you have visited already: {visited_string}. Progress meaningfully from here. 
        Given the following URLs and the objective '{objective}', return the most relevant URL:\n\n
        '''
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
    def filter_urls_programmatically(base_url: str, urls: List[str]) -> List[str]:
        filtered_urls = []
        base_domain = urlparse(base_url).netloc

        for url in urls:
            # Ensure the URL is absolute
            absolute_url = urljoin(base_url, url)
            parsed_url = urlparse(absolute_url)
            
            # Skip URLs that are not on the same domain
            if parsed_url.netloc != base_domain:
                continue

            # Skip URLs with common non-content indicators
            if any(indicator in parsed_url.path.lower() for indicator in [
                'user:', 'talk:', 'special:', 'file:', 'category:', 'template:',
                'help:', 'portal:', '/w/', 'index.php', 'main_page'
            ]):
                continue

            # Skip URLs that likely lead to utility pages
            if re.search(r'(edit|history|action=|oldid=|printable=|user:|search)', parsed_url.path.lower()):
                continue

            # Skip anchor links within the same page
            if parsed_url.path == urlparse(base_url).path and parsed_url.fragment:
                continue

            filtered_urls.append(absolute_url)

        return filtered_urls

    @staticmethod
    async def crawl(start_url: str, max_path_length: int, objective: str, processor: ProcessorType) -> List[dict]:
        results = []
        current_url = start_url
        visited=[]
        
        for depth in range(1, max_path_length + 1):
            try:
                content = await Webscraper.fetch_html(current_url, processor)
            except HTTPException:
                break

            results.append(content)
            visited.append(current_url)
            urls = [link['href'] for link in content.get('links', []) if link['href'] not in visited]
            
            # Filter URLs programmatically first
            filtered_urls = Webscraper.filter_urls_programmatically(current_url, urls)
            
            # Then use GPT-4o to choose from the filtered URLs
            chosen_url = await Webscraper.choose_urls(filtered_urls, objective, visited)
            
            if chosen_url == 'TERMINATE':
                break

            # Small delay to prevent rate limiting errors
            await asyncio.sleep(0.1)

            if not chosen_url:
                break

            current_url = chosen_url

        return results