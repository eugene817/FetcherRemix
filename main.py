# class Settings:
#     llm_api_key: str = (
#         ""
#     )
#     llm_model: str = "deepseek-v4-flash"
#     llm_base_url: str = "https://opencode.ai/zen/go/v1"
#     intermediate_json: str = "data/massive_jobs_dataset.json"
#     parquet_file: str = "db/silver.parquet"
#     no_fluff_pages: int = 5
#     NFJ_API_URL = "https://nofluffjobs.com/api/posting?page=0&pageSize=1"


from layers.gold import generate_gold_report
from layers.utils import _e, _s
import httpx
from layers.transform import filter_data
from layers.extract import fetch_justjoinit_raw, extract_nofluffjobs
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


async def main():
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            fluff_table = await extract_nofluffjobs(client=client)
            justjoinit_table = await fetch_justjoinit_raw(client=client)
            _s(f"fluff_table: {fluff_table.shape[0]} rows")
            _s(f"justjoinit_table: {justjoinit_table.shape[0]} rows")
            combined_table = pa.concat_tables([justjoinit_table, fluff_table])
            _s(f"combined_table: {combined_table.shape[0]} rows")
        except Exception as e:
            _e(f"Error fetching data: {e}")
    filtered_postings = filter_data(config=FilterConfig, results=combined_table)
    # await run_gold_layer()
    await generate_gold_report(filtered_postings)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
