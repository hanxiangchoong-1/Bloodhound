class BaseProcessor:
    def process(self, data):
        """
        Generic processing method to be overridden by specialized classes.
        """
        raise NotImplementedError("This method should be implemented by subclasses")

class CNAProcessor(BaseProcessor):
    def process(self, html_content):
        """
        Process HTML content.
        This method should implement your specific HTML processing logic.
        """
        # Example implementation (you should replace this with your actual processing logic)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)