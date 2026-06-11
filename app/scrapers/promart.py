from app.scrapers.vtex import VTEXScraper


class PromartScraper(VTEXScraper):
    API_CANDIDATES = [
        "https://www.promart.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.promart.pe/api/catalog_system/pub/products/search?fq=productId:{sku}",
    ]
    DETECT_PATTERN = "promart"
    TIENDA = "Promart"

    def __init__(self, url: str):
        super().__init__(url, tienda=self.TIENDA)
