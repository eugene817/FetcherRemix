import polars as pl
from pathlib import Path


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


def build_silver_layer(input_json: str, parquet_file: str, output_json: str):
    print("[*] Запуск Polars трансформации...")

    try:
        df = pl.read_json(input_json)
        if df.is_empty():
            print("[-] Входной JSON пуст.")
            return
    except Exception as e:
        print(f"[!] Ошибка чтения {input_json}: {e}")
        return

    parquet_path = Path(parquet_file)
    if parquet_path.exists():
        existing_ids = pl.read_parquet(parquet_path).select("job_id")
    else:
        existing_ids = pl.DataFrame(schema={"job_id": pl.Utf8})

    def count_matches(skill_set: set) -> pl.Expr:
        return (
            pl.col("skills")
            .list.eval(pl.element().str.to_lowercase().is_in(skill_set))
            .list.sum()
        )

    df_filtered = (
        df.unique(subset=["title", "company"], keep="first")
        .filter(~pl.col("title").str.contains(FilterConfig.ANTI_TITLES))
        .with_columns(
            core_count=count_matches(FilterConfig.CORE_SKILLS),
            infra_count=count_matches(FilterConfig.CV_INFRA),
            transition_count=count_matches(FilterConfig.TRANSITION_TARGETS),
        )
        .filter(
            (pl.col("core_count") > 0)
            & ((pl.col("infra_count") > 0) | (pl.col("transition_count") > 0))
        )
        .with_columns(
            match_score=(
                40 + pl.col("infra_count") * 10 + pl.col("transition_count") * 20
            ).clip(upper_bound=100)
        )
        .join(existing_ids, on="job_id", how="anti")
        .sort(by="match_score", descending=True)
    )

    if df_filtered.is_empty():
        print("[-] Новых релевантных вакансий не найдено.")
        return

    print(f"\n[+] Найдено {df_filtered.shape[0]} новых матчей:")

    display_df = df_filtered.select(["title", "company", "skills", "match_score"])
    print(display_df)

    df_filtered.write_json(output_json)

    if parquet_path.exists():
        silver_df = pl.read_parquet(parquet_path)
        updated_silver = pl.concat([silver_df, df_filtered], how="diagonal")
    else:
        updated_silver = df_filtered

    updated_silver.write_parquet(parquet_path)
    updated_silver.write_json(output_json)
    print(f"[*] Стейт обновлен: {parquet_file}")
    print(f"[*] Результаты выгружены в: {output_json}")

