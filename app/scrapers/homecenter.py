import re
import httpx
from app.scrapers.base import GenericScraper, ProductoScraped


class HomecenterScraper(GenericScraper):
    DOMAINS = {
        "com.co": ("Homecenter", "https://www.homecenter.com.co/api/catalog_system/pub/products/search?fq=skuId:{sku}"),
        "com.pe": ("Homecenter Perú", "https://www.homecenter.com.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}"),
    }

    API_FALLBACKS = [
        "https://www.homecenter.com.co/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.homecenter.com.co/api/catalog_system/pub/products/search?fq=productId:{sku}",
        "https://www.homecenter.com.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.homecenter.com.pe/api/catalog_system/pub/products/search?fq=productId:{sku}",
    ]

    def __init__(self, url: str):
        super().__init__(url, tienda="Homecenter")
        self._dominio = self._detectar_dominio()

    def detect(self) -> bool:
        return "homecenter" in self.url.lower()

    def _detectar_dominio(self) -> str:
        for dom in self.DOMAINS:
            if dom in self.url.lower():
                return dom
        return "com.co"

    def scrape(self) -> ProductoScraped:
        nombre, _ = self.DOMAINS.get(self._dominio, ("Homecenter", ""))
        self.tienda = nombre
        product = super().scrape()
        if not product.tienda or product.tienda == "Homecenter":
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
        for url_template in self.API_FALLBACKS:
            try:
                resp = httpx.get(
                    url_template.format(sku=sku),
                    headers={**self.HEADERS, "Accept": "application/json"},
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                items = data if isinstance(data, list) else data.get("products", [data])
                for item in items if isinstance(items, list) else [items]:
                    parsed = self._parse_item(item, sku)
                    if parsed:
                        return parsed
            except Exception:
                continue
        return None

    def _parse_item(self, item: dict, sku: str) -> ProductoScraped | None:
        try:
            name = item.get("productName") or item.get("name") or item.get("displayName") or ""
            inner = (item.get("items") or [item])[0]
            sellers = inner.get("sellers") or []
            seller = sellers[0] if sellers else {}
            co = seller.get("commertialOffer", {}) if seller else {}
            price = co.get("Price") or co.get("spotPrice") or co.get("price") or 0.0
            return ProductoScraped(
                codigo=str(sku), descripcion=str(name), unidad="Unidad",
                valor=float(price), tienda=self.tienda, url=self.url,
            )
        except Exception:
            return None

    def _extract_sku(self) -> str | None:
        for pat in [r"/p/(\d+)", r"(\d+)/?p/?$", r"-(\d+)/?$", r"/product/(\d+)"]:
            m = re.search(pat, self.url)
            if m:
                return m.group(1)
        nums = re.findall(r"/(\d{4,})", self.url)
        return nums[-1] if nums else None
