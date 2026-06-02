import json
import polars as pl
from rich.text import Text
from openai import AsyncOpenAI
from config.settings import settings
from layers.utils import _s, _e
from rich.console import Console
from rich.panel import Panel
from layers.utils import _p


async def run_gold_layer() -> None:
    if not settings.parquet_file.exists():
        _e(
            f"Analysis artifact missing at {settings.parquet_file}. Execute the transformation layer first."
        )
        return

    df = pl.read_parquet(settings.parquet_file)
    if df.is_empty():
        _e("The source dataset is empty. Nothing to process for the Gold layer.")
        return

    top_jobs = (
        df.sort("match_score", descending=True)
        .select(["title", "company", "salary_min", "salary_max", "skills"])
        .head(15)
        .to_dicts()
    )

    context_entries = []
    for job in top_jobs:
        sal_min = job.get("salary_min") or "N/A"
        sal_max = job.get("salary_max") or "N/A"
        skills = ", ".join(job.get("skills") or [])
        entry = f"- {job['title']} | {job['company']} | ЗП: {sal_min}-{sal_max} PLN | Стек: {skills}"
        context_entries.append(entry)

    context = "\n".join(context_entries)
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    prompt = f"""
Ты — Senior Technical Recruiter. Выбери 3 лучшие вакансии для Python Backend инженера, переходящего в Data Engineering.
Критерии: Python + Инфраструктура (Docker, K8s, Cloud, Data pipelines). 
Бюджет 14k-16k PLN. 
Выведи результат в Markdown:
### 1. [Название] @ [Компания]
- Почему это мэтч: [1 предложение]
- Что продать из опыта: [1 предложение]

Вакансии:
{context}
"""

    _s(f"Dispatching top 15 qualified allocations to {settings.llm_model}...")

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        output = response.choices[0].message.content.strip()

        print("\n" + "=" * 60)
        print("🏆 Final Top for Recruitment 🏆")
        print("=" * 60)
        print(output)
        print("=" * 60)

    except Exception as error:
        _e(f"Failed to synthesize Gold layer report via LLM execution engine: {error}")


async def generate_gold_report(filtered_postings) -> None:
    if filtered_postings.is_empty():
        _s(
            "No new high-confidence matches found today. Skipping dashboard compilation."
        )
        return

    report_df = filtered_postings.sort("match_score", descending=True).head(3)

    if report_df.is_empty():
        _s("No high-confidence matches found today.")
        return

    console = Console()
    console.print("\n🏆 [bold magenta]Final Top for Recruitment[/bold magenta] 🏆\n")

    for rank, job in enumerate(report_df.to_dicts(), 1):
        sal_min = job.get("salary_min")
        sal_max = job.get("salary_max")

        if sal_min is not None and sal_max is not None:
            salary_str = f"{int(sal_min):,} - {int(sal_max):,} PLN"
        elif sal_min is not None:
            salary_str = f">= {int(sal_min):,} PLN"
        else:
            salary_str = "Undisclosed"

        skills_str = ", ".join(job.get("skills") or [])

        card_content = Text()
        card_content.append("Company: ", style="bold cyan")
        card_content.append(f"{job['company']}\n", style="yellow")
        card_content.append("Salary:  ", style="bold cyan")
        card_content.append(f"{salary_str}\n", style="bold blue")
        card_content.append("Skills:  ", style="bold cyan")
        card_content.append(f"{skills_str}\n\n", style="dim")
        card_content.append("Link:    ", style="bold cyan")
        card_content.append(job["url"], style="white")

        console.print(
            Panel(
                card_content,
                title=f"[bold green][{int(job['match_score'])}%][/bold green] {rank}. {job['title']}",
                border_style="bold green",
                expand=False,
            )
        )

    settings.gold_report_json.parent.mkdir(parents=True, exist_ok=True)

    with open(settings.gold_report_json, "w", encoding="utf-8") as f:
        json.dump(report_df.to_dicts(), f, ensure_ascii=False, indent=4)

    _p(f"Gold report artifact compiled and persisted to: {settings.gold_report_json}")
