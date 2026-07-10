# 🚀 FetcherRemix

**FetcherRemix** is a high-performance, asynchronous ETL pipeline designed to aggregate, clean, and analyze job postings from the Polish IT market. The system fetches data from major job boards (**JustJoinIT**, **NoFluffJobs**, **Pracuj.pl**), standardizes it, and filters relevant offers based on custom metrics.

Built around the modern Python ecosystem: **`uv`**, **`Polars`**, **`Playwright`**, and **`Ruff`**.

---

## ⚡ Key Features

* **Asynchronous High-Speed Ingestion:** Parallel data fetching via `asyncio` (combining `httpx` for API sources and `Playwright` for web scraping).
* **Medallion (ETL) Architecture:** Multi-layered data processing:
  * 🥉 **Bronze:** Raw data from sources.
  * 🥈 **Silver:** Cleaning, deduplication, currency normalization, and `match_score` calculation using **Polars & PyArrow**.
  * 🥇 **Gold:** Filtering by stop-words, salary thresholds, and generation of the final analytical report.
* **Modern Tooling:** Dependency management and package building powered by `uv`. Code is validated against strict `Ruff (ALL)` rules.
* **Beautiful CLI & Output:** Interactive terminal interface built with `Typer` and `Rich`.

---

## 🏗 Architecture & Data Structure

The project strictly follows the separation of concerns principle:

* `layers/` — Core data processing pipeline.
  * `layers/extract/` — Data extraction modules (Playwright / HTTP Clients).
  * `layers/transform.py` — Business logic and data normalization layer (Silver).
  * `layers/gold.py` — Final data mart generation and CLI visualization.
* `config/` — Centralized project settings (Pydantic / Settings).
* `data/` & `db/` — Local artifact storage (`.parquet` for analytics, `.json` for reports).

---

## 🚀 Quick Start

You can run the project directly from GitHub without manually cloning the repository, thanks to `uvx`:

```bash
uvx --from git+https://github.com/eugene817/FetcherRemix.git fetcher --rows 5
```

## Local Development

To set up a local development environment, follow these steps:

0. Clone the repository:
```bash
git clone https://github.com/eugene817/FetcherRemix.git
```

1. Setup local env:
```bash
uv sync
uv run playwright install chromium
```
or

```bash
make install
```


2. Run the pipeline:
```bash
make run
```
or 

```bash
uv run main.py --rows 5
```

