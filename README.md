# FetcherRemix

Fetches and analyzes job market data from Polish job boards (NoFluffJobs, JustJoinIT).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
uv run main.py <number_of_gold_rows>
```

## Structure

- `layers/` - data processing pipeline (bronze -> silver -> gold)
- `config/` - configuration
- `data/` - output reports
