from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProductoScraped:
    codigo: str
    descripcion: str
    unidad: str
    valor: float
    tienda: str
    url: str


class BaseScraper(ABC):
    def __init__(self, url: str):
        self.url = url

    @abstractmethod
    def detect(self) -> bool:
        pass

    @abstractmethod
    def scrape(self) -> ProductoScraped:
        pass
