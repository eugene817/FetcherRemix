from layers.utils import _s
from selenium.webdriver.remote.webelement import WebElement
import re
import time
import pyarrow as pa
import pyarrow.parquet as pq
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from layers.schema import JOB_SCHEMA
from webdriver_manager.chrome import ChromeDriverManager
from config.settings import settings

NONE_VALUE = "Not shown"


def create_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def parse_salary_range(salary_text: str) -> tuple[int | None, int | None]:
    if not salary_text or salary_text == NONE_VALUE:
        return None, None

    is_hourly = any(x in salary_text.lower() for x in ["godz", "hour"])

    normalized_text = salary_text.replace(",", "").replace(" ", "").replace("\xa0", "")

    pattern = r"(\d+)[\s\xa0]*[–—-][\s\xa0]*(\d+)"
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

    if min_val < 1000 and not is_hourly:
        min_val *= 1000
        max_val *= 1000

    if is_hourly:
        min_val *= 168
        max_val *= 168

    return min_val, max_val


def accept_cookies(driver: webdriver.Chrome) -> None:
    try:
        wait = WebDriverWait(driver, 7)
        cookie_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-test="button-acceptAll"]')
            )
        )
        cookie_button.click()
    except Exception:
        pass


def get_text(element: WebElement) -> str:
    return element.get_attribute("textContent").strip() if element else NONE_VALUE


def extract_job_links(driver: webdriver.Chrome):
    wait = WebDriverWait(driver, 10)
    wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, '[data-test="section-offers"]')
        )
    )

    cards = driver.find_elements(By.CSS_SELECTOR, '[data-test="default-offer"]')
    data = []

    for card in cards:
        technologies = []
        contract_type = NONE_VALUE
        is_remote = False

        link_elements = card.find_elements(By.CSS_SELECTOR, '[data-test="link-offer"]')

        if not link_elements:
            continue

        url = link_elements[0].get_attribute("href")

        salary_elements = card.find_elements(
            By.CSS_SELECTOR, '[data-test="offer-salary"]'
        )
        title_elements = card.find_elements(
            By.CSS_SELECTOR, '[data-test="offer-title"]'
        )
        company_elements = card.find_elements(
            By.CSS_SELECTOR, '[data-test="text-company-name"]'
        )
        additional_info_elements = card.find_elements(
            By.CSS_SELECTOR, '[data-test^="offer-additional-info-"]'
        )
        texnologies_elements = card.find_elements(
            By.CSS_SELECTOR, '[data-test="technologies-item"]'
        )

        salary = get_text(salary_elements[0] if salary_elements else None)
        title = get_text(title_elements[0] if title_elements else None)
        min_salary, max_salary = parse_salary_range(salary)
        copmany = get_text(company_elements[0])

        for texnology_element in texnologies_elements:
            if (texnology := get_text(texnology_element)) != NONE_VALUE:
                technologies.append(texnology)

        for additional_info_element in additional_info_elements:
            info_text = get_text(additional_info_element).lower()
            if not info_text:
                continue
            if "b2b" in info_text:
                contract_type = "B2B"
            elif "pracę" in info_text or "uop" in info_text:
                contract_type = "UoP"
            elif "zlecenie" in info_text:
                contract_type = "Uz"
            if "zdalna" in info_text or "hybrydowa" in info_text:
                is_remote = True

        data.append(
            pa.Table.from_pylist(
                [
                    {
                        "title": title,
                        "company": copmany,
                        "url": url,
                        "skills": technologies,
                        "salary_min": min_salary,
                        "salary_max": max_salary,
                        "contract_type": contract_type,
                        "is_remote": is_remote,
                    },
                ],
                schema=JOB_SCHEMA,
            )
        )

    return data


def go_to_next_page(driver: webdriver.Chrome) -> bool:
    try:
        next_button = driver.find_element(
            By.CSS_SELECTOR, '[data-test="button-next-page"]'
        )

        if not next_button.is_enabled():
            return False

        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
        time.sleep(1)

        next_button.click()
        return True
    except Exception:
        return False


def fetch_pracuj() -> pa.Table:
    driver = create_driver()
    all_data = []

    _s("[cyan]Fetching data from Pracuj.pl")

    try:
        driver.get(settings.pracuj_pl_url)
        accept_cookies(driver)

        while True:
            page_data = extract_job_links(driver)
            all_data.extend(page_data)

            if not go_to_next_page(driver):
                break

            time.sleep(2)
        table = pa.concat_tables(all_data)
        pq.write_table(table, settings.pracuj_pl_parquet)

    finally:
        driver.quit()

    return table
