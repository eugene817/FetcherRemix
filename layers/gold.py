from dataclasses import dataclass
import json
from openai import AsyncOpenAI
from pathlib import Path


# Конфиг тянем из твоих настроек (через объект settings)
async def run_gold_layer(settings):
    input_file = Path("data/filtered_data_polars.json")
    if not input_file.exists():
        print("[-] Нет файла для анализа. Запусти transform.py")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    # Берем топ-15
    top_jobs = sorted(jobs, key=lambda x: x.get("match_score", 0), reverse=True)[:15]

    context = "\n".join(
        [
            f"- {j['title']} | {j['company']} | ЗП: {j.get('salary_min', 'N/A')} | Стек: {', '.join(j['skills'])}"
            for j in top_jobs
        ]
    )

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

    print(f"[*] Отправляем вакансии в {settings.llm_model}...")

    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    print("\n" + "=" * 60)
    print("🏆 ФИНАЛЬНЫЙ ТОП ДЛЯ ОТКЛИКА 🏆")
    print("=" * 60)
    print(response.choices[0].message.content.strip())
    print("=" * 60)

