.PHONY: lint run gold

lint:
	uv run ruff check --fix .
	uv run ruff format .

run:
	uv run main.py 5

cat-gold:
	cat data/gold_report.json | jq .
