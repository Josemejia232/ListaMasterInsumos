from app.scrapers.base import GenericScraper
from app.scrapers.vtex import VTEXScraper
from app.scrapers.sodimac import SodimacScraper
from app.scrapers.maestro import MaestroScraper
from app.scrapers.promart import PromartScraper
from app.scrapers.homecenter import HomecenterScraper
from app.scrapers.easy import EasyScraper

SCRAPERS = [SodimacScraper, HomecenterScraper, PromartScraper, MaestroScraper, EasyScraper]


def get_scraper(url: str) -> GenericScraper:
    for scraper_cls in SCRAPERS:
        instance = scraper_cls(url)
        if instance.detect():
            return instance
    return GenericScraper(url, tienda="Otra")
