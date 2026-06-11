from app.scrapers.vtex import VTEXScraper


class SodimacScraper(VTEXScraper):
    DOMAINS = {
        "com.pe": ("Sodimac Perú", "https://www.falabella.com.pe/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={sku}"),
        "com.co": ("Sodimac Colombia", "https://www.homecenter.com.co/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={sku}"),
        "com.cl": ("Sodimac Chile", "https://www.falabella.com/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={sku}"),
    }

    API_CANDIDATES = [
        "https://www.falabella.com.pe/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={sku}",
        "https://www.sodimac.com.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.sodimac.com.co/api/catalog_system/pub/products/search?fq=skuId:{sku}",
    ]

    SKU_PATTERNS = [
        r"/product/(\d+)",
        r"/producto/(\d+)",
        r"skuId[=:](\d+)",
        r"productId[=:](\d+)",
    ]

    DETECT_PATTERN = "sodimac.com"
    TIENDA = "Sodimac"

    def __init__(self, url: str):
        super().__init__(url, tienda=self.TIENDA)
        self._dominio = self._detectar_dominio()

    def _detectar_dominio(self) -> str:
        for dom in self.DOMAINS:
            if dom in self.url.lower():
                return dom
        return "com.pe"

    def scrape(self):
        nombre, _ = self.DOMAINS.get(self._dominio, ("Sodimac", ""))
        self.tienda = nombre
        api_data = self._try_api()
        if api_data:
            api_data.tienda = nombre
            return api_data
        product = super().scrape()
        if not product.tienda or product.tienda == self.TIENDA:
            product.tienda = nombre
        return product
