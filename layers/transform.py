from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from config.settings import filter_config, settings
from layers.utils import _p, _s, _v

SALARY_SANITY_THRESHOLD = 14000

if TYPE_CHECKING:
    import pyarrow as pa


def count_matches(skill_set: set) -> pl.Expr:
    return (
        pl.col("skills")
        .list.eval(pl.element().str.to_lowercase().is_in(skill_set))
        .list.sum()
    )


def calculate_match_score() -> pl.Expr:
    is_target_contract = (
        pl.col("contract").str.to_lowercase().str.contains("b2b|mandate|zlecenie")
    )
    is_target_salary = (pl.col("salary_max") >= SALARY_SANITY_THRESHOLD) | (
        pl.col("salary_min") >= SALARY_SANITY_THRESHOLD
    )

    infra_score = pl.col("infra_count") * 10
    transition_score = pl.col("transition_count") * 35

    contract_bonus = (
        pl.when(pl.col("contract").is_null())
        .then(7)
        .when(is_target_contract)
        .then(10)
        .otherwise(0)
    )

    salary_bonus = (
        pl.when(pl.col("salary_min").is_null() & pl.col("salary_max").is_null())
        .then(10)
        .when(is_target_salary)
        .then(15)
        .otherwise(0)
    )

    raw_score = infra_score + transition_score + contract_bonus + salary_bonus

    return (
        pl.when(pl.col("transition_count") > 0)
        .then(raw_score + 15)
        .otherwise(raw_score.clip(upper_bound=55))
        .clip(lower_bound=0, upper_bound=100)
        .alias("match_score")
    )


def filter_data(results: pa.Table) -> pl.DataFrame:
    job_postings = pl.from_arrow(results)

    if (parquet_path := Path(settings.parquet_file)) and parquet_path.exists():
        silver_df = pl.read_parquet(parquet_path)
        existing_ids = pl.read_parquet(parquet_path).select("job_id")
    else:
        silver_df = pl.DataFrame(schema={"job_id": pl.Utf8})
        existing_ids = pl.DataFrame(schema={"job_id": pl.Utf8})

    postings_filtered = (
        job_postings.unique(subset=["title", "company"], keep="first")
        .filter(~pl.col("title").str.contains(filter_config.ANTI_TITLES))
        .with_columns(
            core_count=count_matches(filter_config.CORE_SKILLS),
            infra_count=count_matches(filter_config.CV_INFRA),
            transition_count=count_matches(filter_config.TRANSITION_TARGETS),
        )
        .filter(
            (pl.col("core_count") > 0)
            & ((pl.col("infra_count") > 0) | (pl.col("transition_count") > 0))
        )
        .with_columns(calculate_match_score())
        .join(existing_ids, on="job_id", how="anti")
        .sort(by="match_score", descending=True)
    )

    if postings_filtered.is_empty():
        _v("No new recruitment postings found.")
        return pl.DataFrame()

    updated_silver = pl.concat([silver_df, postings_filtered], how="diagonal")
    updated_silver.write_parquet(settings.parquet_file)

    _p(f"Found {postings_filtered.shape[0]} new recruitment postings:")
    _s(f"State updated: {settings.parquet_file}")
    return postings_filtered
