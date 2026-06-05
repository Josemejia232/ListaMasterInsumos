import re
import httpx
from app.scrapers.base import GenericScraper, ProductoScraped


class PromartScraper(GenericScraper):
    API_CANDIDATES = [
        "https://www.promart.pe/api/catalog_system/pub/products/search?fq=skuId:{sku}",
        "https://www.promart.pe/api/catalog_system/pub/products/search?fq=productId:{sku}",
    ]

    def __init__(self, url: str):
        super().__init__(url, tienda="Promart")

    def detect(self) -> bool:
        return "promart" in self.url.lower()

    def scrape(self) -> ProductoScraped:
        api_data = self._try_api()
        if api_data:
            return api_data
        product = super().scrape()
        return product

    def _try_api(self) -> ProductoScraped | None:
        sku = self._extract_sku()
        if not sku:
            return None
        for url_template in self.API_CANDIDATES:
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
            co = seller.get("commertialOffer", {})
            price = co.get("Price") or co.get("spotPrice") or 0.0
            return ProductoScraped(
                codigo=str(sku), descripcion=str(name), unidad="Unidad",
                valor=float(price), tienda="Promart", url=self.url,
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
