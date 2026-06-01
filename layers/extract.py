import asyncio
import json
import httpx

# API NoFluffJobs (POST-запрос для поиска)
NFJ_API_URL = "https://nofluffjobs.com/api/posting?page=0&pageSize=5"


def parse_nfj_offer(p: dict) -> dict:
    """Маппинг сырого ответа API в плоский словарь для Polars."""
    tiles = p.get("tiles") or {}
    tile_values = tiles.get("values") or []

    # Собираем только хард-скиллы
    skills = [
        str(t.get("value", "")).lower()
        for t in tile_values
        if t.get("type") in ("requirement", "technology", "language")
    ]

    salary = p.get("salary") or {}

    return {
        "job_id": f"nfj-{p.get('url', '')}",
        "title": str(p.get("title") or "Unknown"),
        "company": str(p.get("name") or "Unknown"),
        "url": f"https://nofluffjobs.com/pl/job/{p.get('url', '')}",
        "skills": list(set(skills)),
        "salary_min": salary.get("from"),
        "salary_max": salary.get("to"),
        "contract": salary.get("type"),
        "is_remote": bool(p.get("fullyRemote", False)),
    }


async def fetch_nofluffjobs(pages: int = 1) -> list[dict]:
    """Асинхронный сбор вакансий."""
    jobs = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Идем по страницам
        for page in range(pages):
            payload = {
                "criteriaSearch": {
                    "requirement": [
                        "python",
                        "data",
                        "fastapi",
                        "databricks",
                        "django",
                        "spark",
                    ],
                },
                "page": page,
                "pageSize": 50,
            }

            try:
                print(f"[*] Fetching NFJ page {page + 1}...")
                resp = await client.get(NFJ_API_URL, params=payload)
                resp.raise_for_status()

                postings = resp.json().get("postings", [])
                if not postings:
                    break

                for p in postings:
                    jobs.append(parse_nfj_offer(p))

            except Exception as e:
                print(f"[!] Ошибка парсинга страницы {page}: {e}")
                break

    return jobs


async def main():
    print("Запуск экстрактора...")
    # Собираем первые 3 страницы для MVP
    raw_jobs = await fetch_nofluffjobs(pages=3)

    output_file = "data/massive_jobs_dataset.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(raw_jobs, f, ensure_ascii=False, indent=2)

    print(f"Успешно. Сохранено {len(raw_jobs)} вакансий в {output_file}")

