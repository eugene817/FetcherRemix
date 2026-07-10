import asyncio
import re
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.parquet as pq
from fake_useragent import UserAgent
from playwright.async_api import Browser, Locator, Page, Playwright, async_playwright

from config.settings import settings
from layers.schema import JOB_SCHEMA
from layers.utils import _s

if TYPE_CHECKING:
    from collections.abc import Iterable

NONE_VALUE = "Not shown"
HOURLY_RATE_SANITY_THRESHOLD = 1000
HOURS_PER_MONTH = 160
ua = UserAgent(os=["Windows", "Mac OS X"])


async def get_text(locator: Locator) -> str:
    if await locator.count() > 0:
        text = await locator.first.text_content()
        return text.strip() if text else NONE_VALUE
    return NONE_VALUE


async def create_driver(p: Playwright) -> tuple[Page, Browser]:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=ua.random,
    )
    return await context.new_page(), browser


def parse_salary_range(salary_text: str) -> tuple[int | None, int | None]:
    if not salary_text or salary_text == NONE_VALUE:
        return None, None

    is_hourly = any(x in salary_text.lower() for x in ["godz", "hour"])

    normalized_text = salary_text.replace(",", "").replace(" ", "").replace("\xa0", "")

    pattern = r"(\d+)[\s\xa0]*-[\s\xa0]*(\d+)"
    match = re.search(pattern, normalized_text)

    if match:
        min_val = int(match.group(1))
        max_val = int(match.group(2))
    else:
        only_digits = re.findall(r"\d+", normalized_text)
        if only_digits:
            min_val = int(only_digits[0])
            max_val = min_val
        else:
            return None, None

    if min_val < HOURLY_RATE_SANITY_THRESHOLD and not is_hourly:
        min_val *= HOURLY_RATE_SANITY_THRESHOLD
        max_val *= HOURLY_RATE_SANITY_THRESHOLD

    if is_hourly:
        min_val *= HOURS_PER_MONTH
        max_val *= HOURS_PER_MONTH

    return min_val, max_val


async def parse_info(info_locs: Iterable[Locator]) -> tuple[str, bool]:
    for info_loc in info_locs:
        info_text = await info_loc.text_content()
        if not info_text:
            continue
        info_text = info_text.lower()
        if "b2b" in info_text:
            contract_type = "B2B"
        elif "pracę" in info_text or "uop" in info_text:
            contract_type = "UoP"
        elif "zlecenie" in info_text:
            contract_type = "Uz"

        if "zdalna" in info_text or "hybrydowa" in info_text:
            is_remote = True

    return contract_type, is_remote


async def parse_card(card: Locator) -> pa.Table | None:
    technologies = []
    link_loc = card.locator('[data-test="link-offer"]')
    if await link_loc.count() == 0:
        return None

    link = await link_loc.first.get_attribute("href")

    salary = await get_text(card.locator('[data-test="offer-salary"]'))
    title = await get_text(card.locator('[data-test="offer-title"]'))

    min_salary, max_salary = parse_salary_range(salary)
    company = await get_text(card.locator('[data-test="text-company-name"]'))

    tech_locs = await card.locator('[data-test="technologies-item"]').all()
    for tech_loc in tech_locs:
        tech_text = await tech_loc.text_content()
        if tech_text and tech_text.strip() != NONE_VALUE:
            technologies.append(tech_text.strip())

    info_locs = await card.locator('[data-test^="offer-additional-info-"]').all()
    contract_type, is_remote = await parse_info(info_locs)

    return pa.Table.from_pylist(
        [
            {
                "title": title,
                "company": company,
                "url": link,
                "skills": technologies,
                "salary_min": min_salary,
                "salary_max": max_salary,
                "contract_type": contract_type,
                "is_remote": is_remote,
            },
        ],
        schema=JOB_SCHEMA,
    )


async def extract_job_links(page: Page) -> list[pa.Table]:
    await page.wait_for_selector('[data-test="section-offers"]', timeout=10000)
    cards = await page.locator('[data-test="default-offer"]').all()
    return [
        job_post for card in cards if (job_post := await parse_card(card)) is not None
    ]


async def go_to_next_page(page: Page) -> bool:
    try:
        next_button = page.locator('[data-test="button-next-page"]')

        if await next_button.count() == 0:
            return False

        if not await next_button.is_enabled():
            return False

        await next_button.click()

        await page.wait_for_load_state("networkidle")
    except Exception:
        return False
    else:
        return True


async def fetch_pracuj() -> pa.Table:
    _s("[cyan]Fetching data from Pracuj.pl")
    async with async_playwright() as p:
        page, browser = await create_driver(p)
        all_data = []
        try:
            await page.goto(settings.pracuj_pl_url)
            while True:
                links = await extract_job_links(page)
                all_data.extend(links)

                if not await go_to_next_page(page):
                    break

                await asyncio.sleep(1.5)

            table = pa.concat_tables(all_data)
            pq.write_table(table, settings.pracuj_pl_parquet)

            return table

        finally:
            await browser.close()
