from app.scrapers.vtex import VTEXScraper


class HomecenterScraper(VTEXScraper):
    DOMAINS = {
        "com.co": ("Homecenter", "https://www.homecenter.com.co/api/catalog_system/pub/products/search?fq=skuId:{sku}"),
        "com.pe": ("Homecenter Perú", "https://www.homecenter.com.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}"),
    }

    API_CANDIDATES = [
        "https://www.homecenter.com.co/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.homecenter.com.co/api/catalog_system/pub/products/search?fq=productId:{sku}",
        "https://www.homecenter.com.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.homecenter.com.pe/api/catalog_system/pub/products/search?fq=productId:{sku}",
    ]

    DETECT_PATTERN = "homecenter"
    TIENDA = "Homecenter"

    def __init__(self, url: str):
        super().__init__(url, tienda=self.TIENDA)
        self._dominio = self._detectar_dominio()

    def _detectar_dominio(self) -> str:
        for dom in self.DOMAINS:
            if dom in self.url.lower():
                return dom
        return "com.co"

    def scrape(self):
        nombre, _ = self.DOMAINS.get(self._dominio, ("Homecenter", ""))
        self.tienda = nombre
        api_data = self._try_api()
        if api_data:
            return api_data
        product = super().scrape()
        if not product.tienda or product.tienda == self.TIENDA:
            product.tienda = nombre
        return product
