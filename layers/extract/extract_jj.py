from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.parquet as pq
from bs4 import BeautifulSoup

from config.settings import settings
from layers.schema import JOB_SCHEMA
from layers.utils import _s

if TYPE_CHECKING:
    import httpx


async def fetch_justjoinit_raw(
    client: httpx.AsyncClient, category: str = "python"
) -> pa.Table:
    url = f"https://justjoin.it/job-offers/remote/{category}?orderBy=DESC&sortBy=published"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    _s("[cyan]Fetching data from JustJoinIt")

    response = await client.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("a", class_="offer-card")

    parsed_data = []
    for card in cards:
        href = card.get("href", "")
        if not href:
            continue

        slug = href.split("/")[-1]

        title_tag = card.find("h3")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        img_tag = card.find("img")
        company = img_tag.get("alt", "Unknown") if img_tag else "Unknown"

        skills = []
        skills_container = card.find("div", class_="mui-lo8b6p")
        if skills_container:
            skills = [
                div.get_text(strip=True).lower()
                for div in skills_container.find_all("div")
            ]

        salary_min = None
        salary_max = None
        salary_span = card.find("span", class_="mui-1cks7or")
        if salary_span:
            raw_salary = salary_span.get_text(strip=True).replace(" ", "")
            if "-" in raw_salary:
                parts = raw_salary.split("-")
                try:
                    salary_min = float(parts[0])
                    salary_max = float(parts[1])
                except ValueError:
                    pass

        contract = "Unknown"
        contract_span = card.find("span", class_="mui-kehbhk")
        if contract_span:
            contract = contract_span.get_text(strip=True)

        is_remote = False
        loc_tag = card.find("p", class_="mui-p7a8ow")
        if loc_tag and "remote" in loc_tag.get_text(strip=True).lower():
            is_remote = True

        job_post = {
            "job_id": f"jji-{slug}",
            "title": title,
            "company": company,
            "url": f"https://justjoin.it{href}",
            "skills": list(set(skills)),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "contract": contract,
            "is_remote": is_remote,
        }
        parsed_data.append(job_post)

    table = pa.Table.from_pylist(parsed_data, schema=JOB_SCHEMA)
    pq.write_table(table, settings.justjoinit_parquet)
    return table
