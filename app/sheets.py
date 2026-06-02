import re
import httpx


def extract_sheet_id(url: str) -> str | None:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


async def read_urls_from_sheet(sheet_url: str) -> list[str]:
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        raise ValueError("No se pudo extraer el ID de la hoja de cálculo")

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(csv_url)
        resp.raise_for_status()
        text = resp.text

    urls = []
    for line in text.splitlines():
        line = line.strip().strip('"')
        if line and line.startswith("http"):
            urls.append(line)
    return urls
