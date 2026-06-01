from pydantic.dataclasses import dataclass

@dataclass
class Settings:
    llm_api_key: str = (
        ""
    )
    llm_model: str = "deepseek-v4-flash"
    llm_base_url: str = "https://opencode.ai/zen/go/v1"


if __name__ == "__main__":
    import asyncio
    from layers.extract import main as extract_main
    from layers.transform import build_silver_layer
    from layers.gold import run_gold_layer
    asyncio.run(extract_main())
    build_silver_layer(
        input_json="data/massive_jobs_dataset.json",
        parquet_file="db/silver.parquet",
        output_json="data/filtered_data_polars.json",
    )
    asyncio.run(run_gold_layer(Settings()))

