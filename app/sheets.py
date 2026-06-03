import re
import csv
import io
from urllib.parse import urlparse, parse_qs
import httpx


def extract_sheet_id(url: str) -> str | None:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


def _extract_gid(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    gid = params.get("gid", [None])[0]
    return f"&gid={gid}" if gid else ""


async def read_urls_from_sheet(sheet_url: str) -> list[dict]:
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        raise ValueError("No se pudo extraer el ID de la hoja de cálculo")

    gid_param = _extract_gid(sheet_url)
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_param}"
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
    n01_col = next((i for i, h in enumerate(headers) if h in ("n01", "n1", "nivel1")), None)
    n02_col = next((i for i, h in enumerate(headers) if h in ("n02", "n2", "nivel2")), None)
    n03_col = next((i for i, h in enumerate(headers) if h in ("n03", "n3", "nivel3")), None)
    prov_col = next((i for i, h in enumerate(headers) if "proveedor" in h or "prov" in h), None)

    results = []
    for row in rows[1:]:
        if url_col is not None and url_col < len(row) and row[url_col].strip().startswith("http"):
            entry = {"url": row[url_col].strip()}
            if cat_col is not None and cat_col < len(row):
                entry["categoria"] = row[cat_col].strip()
            else:
                entry["categoria"] = ""
            if n01_col is not None and n01_col < len(row):
                entry["n01"] = row[n01_col].strip()
            else:
                entry["n01"] = ""
            if n02_col is not None and n02_col < len(row):
                entry["n02"] = row[n02_col].strip()
            else:
                entry["n02"] = ""
            if n03_col is not None and n03_col < len(row):
                entry["n03"] = row[n03_col].strip()
            else:
                entry["n03"] = ""
            if prov_col is not None and prov_col < len(row):
                entry["proveedor"] = row[prov_col].strip()
            else:
                entry["proveedor"] = ""
            results.append(entry)
    return results
