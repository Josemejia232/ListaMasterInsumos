from app.scrapers.vtex import VTEXScraper


class MaestroScraper(VTEXScraper):
    API_CANDIDATES = [
        "https://www.maestro.com.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.maestro.com.pe/api/catalog_system/pub/products/search?fq=productId:{sku}",
    ]
    DETECT_PATTERN = "maestro.com"

    def __init__(self, url: str):
        super().__init__(url, tienda="Maestro")
