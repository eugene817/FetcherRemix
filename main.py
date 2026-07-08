from layers.extract.extract_pracuj import fetch_pracuj
from layers.gold import generate_gold_report
from layers.utils import _e, _p
import httpx
from layers.transform import filter_data
from layers.extract.extract_jj import fetch_justjoinit_raw
from layers.extract.extract_nofluff import extract_nofluffjobs
import pyarrow as pa


class FilterConfig:
    CORE_SKILLS = {"python", "go", "golang"}

    CV_INFRA = {
        "sql",
        "postgresql",
        "docker",
        "kubernetes",
        "k8s",
        "ci/cd",
        "linux",
        "bash",
        "fastapi",
        "redis",
    }

    TRANSITION_TARGETS = {
        "pyspark",
        "spark",
        "databricks",
        "airflow",
        "etl",
        "llm",
        "mlops",
        "machine learning",
        "duckdb",
        "polars",
    }

    ANTI_TITLES = "(?i)senior|lead|architect|manager|head|principal|director"


async def main(number_of_rows=None):
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            fluff_table = await extract_nofluffjobs(client=client)
            _p(f"fluff_table: {fluff_table.shape[0]} rows")
            justjoinit_table = await fetch_justjoinit_raw(client=client)
            _p(f"justjoinit_table: {justjoinit_table.shape[0]} rows")
            pracuj_table = fetch_pracuj()
            _p(f"pracuj_table: {pracuj_table.shape[0]} rows")
            combined_table = pa.concat_tables(
                [justjoinit_table, fluff_table, pracuj_table]
            )
            _p(f"combined_table: {combined_table.shape[0]} rows")
        except Exception as e:
            _e(f"Error fetching data: {e}")
    filtered_postings = filter_data(config=FilterConfig, results=combined_table)
    await generate_gold_report(filtered_postings, number_of_rows)


if __name__ == "__main__":
    import asyncio
    import sys

    if len(sys.argv) > 1:
        number_of_rows = int(sys.argv[1])
    else:
        number_of_rows = None

    asyncio.run(main(number_of_rows))
