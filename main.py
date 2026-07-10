import asyncio

import httpx
import pyarrow as pa
import typer

from layers.extract.extract_jj import fetch_justjoinit_raw
from layers.extract.extract_nofluff import extract_nofluffjobs
from layers.extract.extract_pracuj import fetch_pracuj
from layers.gold import generate_gold_report
from layers.transform import filter_data
from layers.utils import _e, _p

app = typer.Typer()


async def main(number_of_rows: int = 3) -> None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            task_fluff = extract_nofluffjobs(client=client)
            task_justjoinit = fetch_justjoinit_raw(client=client)
            task_pracuj = fetch_pracuj()

            fluff_table, justjoinit_table, pracuj_table = await asyncio.gather(
                task_fluff, task_justjoinit, task_pracuj
            )

            _p(f"justjoinit_table: {justjoinit_table.shape[0]} rows")
            _p(f"fluff_table: {fluff_table.shape[0]} rows")
            _p(f"pracuj_table: {pracuj_table.shape[0]} rows")
            combined_table = pa.concat_tables(
                [justjoinit_table, fluff_table, pracuj_table]
            )
            _p(f"combined_table: {combined_table.shape[0]} rows")
        except Exception as e:
            _e(f"Error fetching data: {e}")
            raise
    filtered_postings = filter_data(results=combined_table)
    await generate_gold_report(filtered_postings, number_of_rows)


@app.command()
def fetch(
    days: int = typer.Option(3, help="Amount of gold report rows"),
) -> None:
    asyncio.run(main(days))


if __name__ == "__main__":
    app()
