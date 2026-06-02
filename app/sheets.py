import re
import csv
import io
import httpx


def extract_sheet_id(url: str) -> str | None:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


async def read_urls_from_sheet(sheet_url: str) -> list[dict]:
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        raise ValueError("No se pudo extraer el ID de la hoja de cálculo")

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(csv_url)
        resp.raise_for_status()
        text = resp.text

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []

    headers = [h.strip().lower() for h in rows[0]]
    url_col = next((i for i, h in enumerate(headers) if h in ("url", "insumo")), None)
    cat_col = next((i for i, h in enumerate(headers) if "categ" in h), None)

    results = []
    for row in rows[1:]:
        if url_col is not None and url_col < len(row) and row[url_col].strip().startswith("http"):
            entry = {"url": row[url_col].strip()}
            if cat_col is not None and cat_col < len(row):
                entry["categoria"] = row[cat_col].strip()
            else:
                entry["categoria"] = ""
            results.append(entry)
    return results
