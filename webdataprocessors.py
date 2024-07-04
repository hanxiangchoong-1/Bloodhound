from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime

class BaseProcessor:
    def extract_content(self, html_content, base_url):
        soup = BeautifulSoup(html_content, 'html.parser')
        root_base_url = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"

        content = {
            "title": "",
            "h1": [],
            "h2": [],
            "h3": [],
            "h4": [],
            "h5": [],
            "h6": [],
            "paragraphs": [],
            "links": [],
            # "images": [],
            "lists": {
                "ul": [],
                "ol": []
            },
            "tables": [],
            "metadata": {},
            "timestamp": datetime.utcnow().isoformat(),
            "url":base_url,
            "root_base_url":root_base_url,
        }


        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            content["title"] = title_tag.get_text(strip=True)

        # Extract headings
        for i in range(1, 7):
            heading_tags = soup.find_all(f'h{i}')
            content[f"h{i}"] = [tag.get_text(strip=True) for tag in heading_tags]

        # Extract paragraphs
        paragraphs = soup.find_all('p')
        content["paragraphs"] = [p.get_text(strip=True) for p in paragraphs]

        # Extract links
        links = soup.find_all('a')
        content["links"] = [{"text": a.get_text(strip=True), "href": urljoin(root_base_url, a.get('href'))} for a in links]

        # Extract images
        # images = soup.find_all('img')
        # content["images"] = [{"src": img.get('src'), "alt": img.get('alt')} for img in images]

        # Extract lists
        for list_type in ['ul', 'ol']:
            lists = soup.find_all(list_type)
            content["lists"][list_type] = [
                [li.get_text(strip=True) for li in lst.find_all('li')]
                for lst in lists
            ]

        # Extract tables
        tables = soup.find_all('table')
        for table in tables:
            table_data = []
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                table_data.append([cell.get_text(strip=True) for cell in cells])
            content["tables"].append(table_data)

        # Extract metadata
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            if name:
                content["metadata"][name] = tag.get('content')

        return content

class CNAProcessor(BaseProcessor):
    pass
    
    # def process(self, html_content, base_url):
    #     """
    #     Process HTML content.
    #     Extracts text content and all URLs from the page.
    #     """
        
    #     # Extract text content
    #     # text_content = soup.get_text(separator=' ', strip=True)
    #     page_content=self.extract_content(soup, base_url)
    #     return page_content