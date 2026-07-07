import json
from rich.text import Text
from config.settings import settings
import polars as pl
from layers.utils import _s
from rich.console import Console
from rich.panel import Panel
from layers.utils import _p


async def generate_gold_report(filtered_postings) -> None:
    if filtered_postings.is_empty():
        _s(
            "No new high-confidence matches found today. Skipping dashboard compilation."
        )
        return

    senior_keywords = r"(?i)(senior|lead|principal|architect|manager|head|director)"
    report_df = filtered_postings.filter(~pl.col("title").str.contains(senior_keywords))
    irrelevant_keywords = r"(?i)(c\+\+|embedded|frontend|react|angular|migration|support|helpdesk|android|ios|flutter)"
    report_df = report_df.filter(~pl.col("title").str.contains(irrelevant_keywords))
    MAX_MIN_SALARY = 18000
    report_df = report_df.filter(
        pl.col("salary_min").is_null() | (pl.col("salary_min") <= MAX_MIN_SALARY)
    )

    if report_df.is_empty():
        _s("No high-confidence matches found today.")
        return

    report_df = report_df.sort("match_score", descending=True).head(3)

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
