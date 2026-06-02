import re
import httpx
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ProductoScraped


class SodimacScraper(BaseScraper):
    def detect(self) -> bool:
        return "sodimac.com" in self.url.lower()

    def scrape(self) -> ProductoScraped:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = httpx.get(self.url, headers=headers, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        codigo = ""
        id_input = soup.find("input", {"name": "productId"})
        if id_input:
            codigo = id_input.get("value", "")
        if not codigo:
            match = re.search(r'"skuId"\s*:\s*"(\d+)"', resp.text)
            if match:
                codigo = match.group(1)

        descripcion = ""
        h1 = soup.find("h1", class_=re.compile(r"product.*name|title|js_product_name", re.I))
        if h1:
            descripcion = h1.get_text(strip=True)
        if not descripcion:
            meta = soup.find("meta", {"name": "description"})
            if meta:
                descripcion = meta.get("content", "")

        unidad = "Unidad"
        unit_el = soup.find("span", class_=re.compile(r"unit|js_unit", re.I))
        if unit_el:
            unidad = unit_el.get_text(strip=True)

        valor = 0.0
        price_match = re.search(r'"price"\s*:\s*([\d.]+)', resp.text)
        if price_match:
            valor = float(price_match.group(1))
        else:
            price_el = soup.find("span", class_=re.compile(r"price|js_price", re.I))
            if price_el:
                texto = price_el.get_text(strip=True).replace("$", "").replace(".", "").replace(",", ".")
                try:
                    valor = float(texto)
                except ValueError:
                    valor = 0.0

        return ProductoScraped(
            codigo=codigo,
            descripcion=descripcion,
            unidad=unidad,
            valor=valor,
            tienda="Sodimac",
            url=self.url,
        )
