from app.scrapers.sodimac import SodimacScraper
from app.scrapers.maestro import MaestroScraper
from app.scrapers.promart import PromartScraper
from app.scrapers.homecenter import HomecenterScraper

SCRAPERS = [SodimacScraper, MaestroScraper, PromartScraper, HomecenterScraper]


def get_scraper(url: str):
    for scraper_cls in SCRAPERS:
        instance = scraper_cls(url)
        if instance.detect():
            return instance
    return None
