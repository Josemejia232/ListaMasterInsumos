import re
import httpx
from app.scrapers.base import GenericScraper, ProductoScraped


class SodimacScraper(GenericScraper):
    DOMAINS = {
        "com.pe": ("Sodimac Perú", "https://www.falabella.com.pe/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={sku}"),
        "com.co": ("Sodimac Colombia", "https://www.homecenter.com.co/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={sku}"),
        "com.cl": ("Sodimac Chile", "https://www.falabella.com/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={sku}"),
    }

    API_FALLBACKS = [
        "https://www.falabella.com.pe/rest/model/falabella/rest/browse/BrowseActor/product-details?productId={sku}",
        "https://www.sodimac.com.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.sodimac.com.co/api/catalog_system/pub/products/search?fq=skuId:{sku}",
    ]

    def __init__(self, url: str):
        super().__init__(url, tienda="Sodimac")
        self._dominio = self._detectar_dominio()

    def detect(self) -> bool:
        return "sodimac.com" in self.url.lower()

    def _detectar_dominio(self) -> str:
        for dom in self.DOMAINS:
            if dom in self.url.lower():
                return dom
        return "com.pe"

    def scrape(self) -> ProductoScraped:
        nombre, _ = self.DOMAINS.get(self._dominio, ("Sodimac", ""))
        self.tienda = nombre
        product = super().scrape()
        if not product.tienda or product.tienda == "Sodimac":
            product.tienda = nombre
        if not product.codigo or not product.valor:
            api_data = self._try_api()
            if api_data:
                product.codigo = api_data.codigo or product.codigo
                product.descripcion = api_data.descripcion or product.descripcion
                product.valor = api_data.valor or product.valor
                if api_data.unidad != "Unidad":
                    product.unidad = api_data.unidad
        return product

    def _try_api(self) -> ProductoScraped | None:
        sku = self._extract_sku()
        if not sku:
            return None
        for api_url_template in self.API_FALLBACKS:
            try:
                resp = httpx.get(
                    api_url_template.format(sku=sku),
                    headers={**self.HEADERS, "Accept": "application/json"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return self._parse_response(data, sku)
            except Exception:
                continue
        return None

    def _parse_response(self, data, sku: str) -> ProductoScraped | None:
        try:
            product = data.get("product", data)
            if isinstance(product, list):
                product = product[0] if product else {}
            name = product.get("displayName") or product.get("name") or product.get("productName") or ""
            items = product.get("items") or [product]
            item = items[0] if isinstance(items, list) else items
            sellers = item.get("sellers") or [item]
            seller = sellers[0] if sellers else {}
            price = seller.get("salePrice") or seller.get("commertialOffer", {}).get("Price") or 0.0
            return ProductoScraped(
                codigo=str(sku), descripcion=str(name), unidad="Unidad",
                valor=float(price), tienda=self.tienda, url=self.url,
            )
        except Exception:
            return None

    def _extract_sku(self) -> str | None:
        for pat in [r"/product/(\d+)", r"/producto/(\d+)", r"skuId[=:](\d+)", r"productId[=:](\d+)"]:
            m = re.search(pat, self.url)
            if m:
                return m.group(1)
        nums = re.findall(r"/(\d{4,})", self.url)
        return nums[-1] if nums else None
