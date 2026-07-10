.PHONY: lint run gold

install:
	uv sync
	uv run playwright install chromium

lint:
	uv run ruff check --fix .
	uv run ruff format .

run:
	uv run main.py --rows 5

cat-gold:
	cat data/gold_report.json | jq .
