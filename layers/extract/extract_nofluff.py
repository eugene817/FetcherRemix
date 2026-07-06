from layers.utils import _s
from pathlib import Path
from typing import Callable
import httpx
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
import pyarrow as pa
import pyarrow.parquet as pq
from config.settings import settings
from layers.schema import JOB_SCHEMA


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
    return await fetch_jobs(
        client=client,
        url=settings.nfj_api_url,
        pages=settings.nfj_pages,
        name="NoFluffJobs",
        function_to_parse=parse_nfj_offer,
        parquet_file=settings.nfj_parquet,
    )
