from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    llm_base_url: str = "https://opencode.ai/zen/go/v1"

    parquet_file: Path = Path("db/silver.parquet")
    gold_report_json: Path = Path("data/gold_report.json")

    nfj_parquet: Path = Path("db/fluff.parquet")
    nfj_pages: int = 1
    nfj_api_url: str = "https://nofluffjobs.com/api/posting"

    justjoinit_parquet: Path = Path("db/justjoinit.parquet")
    justjoinit_api_url: str = "https://justjoin.it/api/v2/offers"
    justjoinit_pages: int = 1

    pracuj_pl_url: str = (
        "https://it.pracuj.pl/praca/data%20engineer;kw/praca%20zdalna;wm,home-office"
    )
    pracuj_pl_parquet: Path = Path("db/pracuj.parquet")


class FilterConfig(BaseSettings):
    CORE_SKILLS: set[str] = {"python", "go", "golang"}

    CV_INFRA: set[str] = {
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

    TRANSITION_TARGETS: set[str] = {
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

    ANTI_TITLES: str = "(?i)senior|lead|architect|manager|head|principal|director"


settings = AppSettings()
filter_config = FilterConfig()
