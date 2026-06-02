from layers.utils import _s
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Callable
import httpx
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
import pyarrow as pa
import pyarrow.parquet as pq
from config.settings import settings

NFJ_API_URL = "https://nofluffjobs.com/api/posting?page=0&pageSize=1"

JOB_SCHEMA = pa.schema(
    [
        ("job_id", pa.string()),
        ("title", pa.string()),
        ("company", pa.string()),
        ("url", pa.string()),
        ("skills", pa.list_(pa.string())),
        ("salary_min", pa.float64()),
        ("salary_max", pa.float64()),
        ("contract", pa.string()),
        ("is_remote", pa.bool_()),
    ]
)


def parse_nfj_offer(posting: dict) -> dict:
    tiles = posting.get("tiles") or {}
    tile_values = tiles.get("values") or []

    skills = [
        str(t.get("value", "")).lower()
        for t in tile_values
        if t.get("type") in ("requirement", "technology", "language")
    ]

    salary = posting.get("salary") or {}

    return {
        "job_id": f"nfj-{posting.get('url', '')}",
        "title": str(posting.get("title") or "Unknown"),
        "company": str(posting.get("name") or "Unknown"),
        "url": f"https://nofluffjobs.com/pl/job/{posting.get('url', '')}",
        "skills": list(set(skills)),
        "salary_min": salary.get("from"),
        "salary_max": salary.get("to"),
        "contract": salary.get("type"),
        "is_remote": bool(posting.get("fullyRemote", False)),
    }


async def fetch_jobs(
    client: httpx.AsyncClient,
    url: str,
    pages: int,
    name: str,
    function_to_parse: Callable,
    parquet_file: Path,
) -> list[dict]:
    arrow_batches = []
    _s("[cyan]Fetching data from NoFluffJobs")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        transient=True,
    ) as progress:
        main_task = progress.add_task(
            "[cyan]Fetching data from NoFluffJobs", total=pages
        )

        for page in range(pages):
            progress.update(
                main_task, advance=1, description=f"[yellow]{name} page {page + 1}"
            )

            response = await client.get(f"{url}?page={page + 1}")
            response.raise_for_status()

            postings = response.json().get("postings", [])
            if not postings:
                break

            table = pa.Table.from_pylist(
                [function_to_parse(p) for p in postings], schema=JOB_SCHEMA
            )
            arrow_batches.append(table)

    table = pa.concat_tables(arrow_batches)
    pq.write_table(table, parquet_file)
    return table


async def extract_nofluffjobs(client: httpx.AsyncClient):
    result = await fetch_jobs(
        client=client,
        url=settings.nfj_api_url,
        pages=settings.nfj_pages,
        name="NoFluffJobs",
        function_to_parse=parse_nfj_offer,
        parquet_file=settings.nfj_parquet,
    )
    return result


async def fetch_justjoinit_raw(
    client: httpx.AsyncClient, category: str = "python"
) -> pa.Table:
    url = f"https://justjoin.it/job-offers/remote/{category}?orderBy=DESC&sortBy=published"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
