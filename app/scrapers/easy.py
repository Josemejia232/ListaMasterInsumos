from app.scrapers.vtex import VTEXScraper


class EasyScraper(VTEXScraper):
    API_CANDIDATES = [
        "https://www.easy.com.co/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.easy.com.co/api/catalog_system/pub/products/search?fq=productId:{sku}",
        "https://www.easy.com.co/api/catalog_system/pub/products/search?fq=sku:{sku}",
        "https://www.easy.com.ar/api/catalog_system/pub/products/search?fq=skuId:{sku}",
    ]
    DETECT_PATTERN = "easy.com"
    TIENDA = "Easy"

    def __init__(self, url: str):
        super().__init__(url, tienda=self.TIENDA)
