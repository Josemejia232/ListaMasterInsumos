import re
import json
import httpx
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from typing import Optional


@dataclass
class ProductoScraped:
    codigo: str
    descripcion: str
    unidad: str
    valor: float
    tienda: str
    url: str


class GenericScraper:
    """Scraper genérico multi-estrategia que funciona con la mayoría de tiendas."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-419,es;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(self, url: str, tienda: str = ""):
        self.url = url
        self.tienda = tienda
        self._html: str = ""
        self._soup: Optional[BeautifulSoup] = None

    def detect(self) -> bool:
        return True  # genérico siempre aplica como fallback

    UNIT_PATTERNS = [
        (r"(\d+[\.,]?\d*)\s*(kg|kilogramo|g|gramo|mg|tonelada|tn|t)\b", "kg"),
        (r"(\d+[\.,]?\d*)\s*(mts?|metros?|m)\b", "m"),
        (r"(\d+[\.,]?\d*)\s*(cms?|cent[íi]metros?|cm)\b", "cm"),
        (r"(\d+[\.,]?\d*)\s*(mms?|mil[íi]metros?|mm)\b", "mm"),
        (r"(\d+[\.,]?\d*)\s*(m2|m²|metros?\s*cuadrados?)\b", "m²"),
        (r"(\d+[\.,]?\d*)\s*(m3|m³|metros?\s*c[úu]bicos?)\b", "m³"),
        (r"(\d+[\.,]?\d*)\s*(lts?|litros?|l)\b", "L"),
        (r"(\d+[\.,]?\d*)\s*(ml|mililitros?)\b", "mL"),
        (r"(\d+[\.,]?\d*)\s*(galones?|gal|gl)\b", "gal"),
        (r"(\d+[\.,]?\d*)\s*(pulgadas?|pulg|in|inch)\b", "in"),
        (r"(\d+[\.,]?\d*)\s*(pies?|ft|foot)\b", "ft"),
        (r"(\d+[\.,]?\d*)\s*(unidades?|und|unid|pza|pieza)\b", "Unidad"),
        (r"(\d+[\.,]?\d*)\s*(plg|plg\.)\b", "plg"),
    ]

    def scrape(self) -> ProductoScraped:
        self._fetch()
        self._soup = BeautifulSoup(self._html, "lxml")

        product = self._empty_result()

        # Estrategia 1: HTML patterns (fallback, menos confiable)
        product = self._merge(product, self._try_html_patterns())

        # Estrategia 2: Meta tags
        product = self._merge(product, self._try_meta_tags())

        # Estrategia 3: Microdata (itemprop)
        product = self._merge(product, self._try_microdata())

        # Estrategia 4: Embedded JS state (SPA state objects)
        product = self._merge(product, self._try_embedded_state())

        # Estrategia 5: Extraer ID de la URL
        product = self._merge(product, self._try_url_id())

        # Estrategia 6: JSON-LD Structured Data (más confiable, aplica al final)
        jsonld = self._try_jsonld()
        if jsonld.codigo or jsonld.valor or jsonld.descripcion:
            product = jsonld
        else:
            product = self._merge(product, jsonld)

        # Unidad desde el nombre (solo si no hay datos estructurados)
        if product.descripcion and product.unidad == "Unidad" and not product.codigo:
            product.unidad = self._extract_unit_from_name(product.descripcion)

        return product

    def _extract_unit_from_name(self, name: str) -> str:
        name_lower = " " + name.lower() + " "
        for pattern, unit_label in self.UNIT_PATTERNS:
            match = re.search(pattern, name_lower, re.IGNORECASE)
            if match:
                return unit_label
        return "Unidad"

    def _fetch(self):
        try:
            resp = httpx.get(self.url, headers=self.HEADERS, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            self._html = resp.text
        except Exception:
            self._html = ""

    def _empty_result(self) -> ProductoScraped:
        return ProductoScraped(codigo="", descripcion="", unidad="Unidad", valor=0.0, tienda=self.tienda, url=self.url)

    @staticmethod
    def _merge(current: ProductoScraped, partial: ProductoScraped) -> ProductoScraped:
        return ProductoScraped(
            codigo=partial.codigo or current.codigo,
            descripcion=partial.descripcion or current.descripcion,
            unidad=partial.unidad if partial.unidad != "Unidad" else current.unidad,
            valor=partial.valor or current.valor,
            tienda=partial.tienda or current.tienda,
            url=partial.url or current.url,
        )

    def _try_jsonld(self) -> ProductoScraped:
        result = self._empty_result()
        if not self._soup:
            return result
        scripts = self._soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0] if data else {}
                if isinstance(data, dict):
                    type_val = data.get("@type", "")
                    if type_val and type_val.lower() == "product":
                        result.codigo = str(data.get("sku", "") or data.get("productID", ""))
                        result.descripcion = str(data.get("name", ""))
                        offers = data.get("offers", {})
                        if isinstance(offers, list) and len(offers) > 0:
                            offers = offers[0]
                        if isinstance(offers, dict):
                            price = offers.get("price", "")
                            if price:
                                result.valor = float(price)
                        return result
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        return result

    def _try_embedded_state(self) -> ProductoScraped:
        """Busca product data en objetos JS embebidos (SPA state objects)."""
        result = self._empty_result()
        if not self._html:
            return result

        state_patterns = [
            r'window\.__STATE__\s*=\s*({.*?});',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__NUXT__\s*=\s*({.*?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
            r'window\.__APP_STATE__\s*=\s*({.*?});',
            r'window\.digitalData\s*=\s*({.*?});',
            r'__NEXT_DATA__"\s*type="application/json">({.*?})</script>',
            r'window\.product\s*=\s*({.*?});',
            r'var\s+skuJson[_\d]*\s*=\s*({.*?});',
            r'productData\s*=\s*({.*?});',
            r'product\s*:\s*({.*?})',
        ]

        for pattern in state_patterns:
            match = re.search(pattern, self._html, re.DOTALL)
            if not match:
                continue
            try:
                data = json.loads(match.group(1))
                result = self._extract_from_dict(result, data)
                if result.codigo and result.descripcion:
                    return result
            except (json.JSONDecodeError, ValueError):
                continue

        # Buscar datos de producto en cualquier JSON grande en script tags
        if not result.codigo:
            for script in (self._soup.find_all("script", type="application/json") if self._soup else []):
                try:
                    data = json.loads(script.string or "")
                    result = self._extract_from_dict(result, data)
                    if result.codigo and result.descripcion:
                        return result
                except (json.JSONDecodeError, ValueError):
                    continue

        return result

    def _extract_from_dict(self, result, data, prefix="") -> ProductoScraped:
        if not isinstance(data, dict):
            return result

        key_map = {
            "sku": "codigo",
            "productId": "codigo",
            "id": None,
            "name": "descripcion",
            "productName": "descripcion",
            "displayName": "descripcion",
            "title": "descripcion",
            "price": "valor",
            "salePrice": "valor",
            "listPrice": "valor",
            "unitMultiplier": "unidad_multiplier",
            "measurementUnit": "unidad_measure",
            "description": "descripcion",
        }

        raw_prices = {}  # precio sin formato (entero) vs formateado

        for key, value in data.items():
            key_lower = key.lower()
            for map_key, field in key_map.items():
                if map_key in key_lower:
                    if field == "codigo" and isinstance(value, (str, int)):
                        if not result.codigo:
                            result.codigo = str(value)
                    elif field == "descripcion" and isinstance(value, str):
                        if not result.descripcion:
                            result.descripcion = value
                    elif field == "valor" and isinstance(value, (int, float)):
                        if float(value) > 0:
                            raw_prices["numeric"] = float(value)
                    elif field == "unidad_multiplier":
                        result.unidad = f"{value}"
                    elif field == "unidad_measure" and isinstance(value, str):
                        if value.strip():
                            result.unidad = value.strip()

            # Detecta precios formateados (ej: "S/ 8.50")
            if isinstance(value, str) and ("price" in key_lower or "selling" in key_lower):
                nums = re.findall(r"[\d.,]+", value)
                if nums:
                    try:
                        clean = nums[0].replace(",", ".")
                        raw_prices["formatted"] = float(clean)
                    except ValueError:
                        pass

            if isinstance(value, dict):
                result = self._extract_from_dict(result, value, f"{prefix}.{key}")
            elif isinstance(value, list):
                for item in value[:3]:
                    if isinstance(item, dict):
                        result = self._extract_from_dict(result, item, f"{prefix}.{key}")

        # Si tenemos precio formateado y numérico, detectar si el numérico está en centavos
        if not result.valor:
            fmt = raw_prices.get("formatted")
            num = raw_prices.get("numeric")
            if fmt and num and num > fmt * 10:
                result.valor = num / 100
            elif fmt:
                result.valor = fmt
            elif num:
                result.valor = num

        return result

    def _try_meta_tags(self) -> ProductoScraped:
        result = self._empty_result()
        if not self._soup:
            return result

        meta_map = {
            "og:title": "descripcion",
            "twitter:title": "descripcion",
            "description": "descripcion",
            "product:retailer_item_id": "codigo",
            "product:price:amount": "valor",
            "product:original_price:amount": "valor",
        }
        for meta in self._soup.find_all("meta"):
            prop = (meta.get("property") or meta.get("name") or "").lower()
            content = meta.get("content", "")
            if not content:
                continue
            field = meta_map.get(prop)
            if field == "descripcion":
                result.descripcion = content
            elif field == "codigo":
                result.codigo = content
            elif field == "valor":
                try:
                    result.valor = float(content)
                except ValueError:
                    pass
        return result

    def _try_microdata(self) -> ProductoScraped:
        result = self._empty_result()
        if not self._soup:
            return result

        name_el = self._soup.find(attrs={"itemprop": "name"})
        if name_el:
            result.descripcion = name_el.get_text(strip=True)

        sku_el = self._soup.find(attrs={"itemprop": "sku"})
        if sku_el:
            result.codigo = sku_el.get("content", sku_el.get_text(strip=True))

        price_el = self._soup.find(attrs={"itemprop": "price"})
        if price_el:
            content = price_el.get("content", price_el.get_text(strip=True))
            try:
                result.valor = float(content)
            except ValueError:
                pass

        return result

    def _try_html_patterns(self) -> ProductoScraped:
        result = self._empty_result()
        if not self._soup:
            return result

        if not result.descripcion:
            h1 = self._soup.find("h1")
            if h1:
                result.descripcion = h1.get_text(strip=True)

        if not result.codigo:
            patterns = [
                ({"id": re.compile(r"sku|product-id|codigo|code", re.I)}, None),
                ({"class_": re.compile(r"sku|product-id|codigo|code", re.I)}, None),
            ]
            for attrs, _ in patterns:
                el = self._soup.find(["span", "div", "p", "dd"], attrs)
                if el:
                    text = el.get_text(strip=True)
                    numbers = re.findall(r"\d+", text)
                    if numbers:
                        result.codigo = numbers[0]
                    break

        if not result.valor:
            price_patterns = [
                {"class_": re.compile(r"price|precio|amount", re.I)},
                {"itemprop": "price"},
            ]
            for attrs in price_patterns:
                el = self._soup.find(["span", "div", "p", "strong", "meta"], attrs)
                if el:
                    content = el.get("content", el.get_text(strip=True))
                    cleaned = re.sub(r"[^\d.,]", "", content)
                    cleaned = cleaned.replace(",", ".").replace(" ", "")
                    try:
                        result.valor = float(cleaned)
                    except ValueError:
                        pass
                    break

        return result

    def _try_url_id(self) -> ProductoScraped:
        result = self._empty_result()
        patterns = [
            r"/product/(\d+)",
            r"/producto/(\d+)",
            r"/(\d+)[xp]",
            r"/p/(\d+)",
            r"sku[=_](\d+)",
            r"productId[=_](\d+)",
            r"/p-(\d+)",
            r"/(\d+)/?$",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.url)
            if match:
                result.codigo = match.group(1)
                break
        return result
