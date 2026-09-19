import logging
import re
from pathlib import Path
from time import sleep
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

START_URL = "https://books.toscrape.com/catalogue/page-1.html"
MAX_PAGES = 5          
DELAY = 1.0             
HEADERS = {"User-Agent": "AdvancedPython-HW1/1.0"}

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "logs" / "crawl.log"
CSV_PATH = BASE_DIR / "data" / "result.csv"

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def fetch(url):
    try:
        response = requests.get(url, timeout=(5, 20), headers=HEADERS)
        if response.status_code in (403, 429):
            logger.error("차단성 응답(%s) 수신 - %s. 크롤링을 중단합니다.", response.status_code, url)
            return None
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.Timeout:
        logger.warning("타임아웃 발생, 건너뜀: %s", url)
        return None
    except requests.exceptions.RequestException as e:
        logger.warning("요청 실패(%s), 건너뜀: %s", e, url)
        return None


def parse_price(text):
    match = re.search(r"[\d.]+", text)
    return float(match.group()) if match else None


def parse_page(soup, page_url):
    rows = []

    for item in soup.select("article.product_pod"):
        try:
            title = item.select_one("h3 a")["title"]
            price = parse_price(item.select_one(".price_color").get_text(strip=True))

            rating_classes = item.select_one("p.star-rating")["class"]
            rating = rating_classes[1] if len(rating_classes) > 1 else None

            availability = item.select_one(".instock.availability").get_text(strip=True)

            rows.append({
                "제목": title,
                "가격": price,
                "평점": rating,
                "재고여부": availability,
                "출처페이지": page_url,
                "수집시각": pd.Timestamp.now(tz="UTC").isoformat(),
            })
        except (AttributeError, TypeError, KeyError) as e:
            logger.warning("행 파싱 실패(%s), 해당 항목 건너뜀 (page=%s)", e, page_url)
            continue

    next_link = soup.select_one("li.next a")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None

    return rows, next_url


def crawl():
    records, url, visited_pages = [], START_URL, 0

    for _ in range(MAX_PAGES):
        if not url:
            break

        soup = fetch(url)
        if soup is None:
            break 

        visited_pages += 1
        page_rows, url = parse_page(soup, url)
        records.extend(page_rows)
        logger.info("페이지 %d 수집 완료 (누적 %d건)", visited_pages, len(records))
        sleep(DELAY)

    return records, visited_pages


def clean(records):
    if not records:
        raise RuntimeError("수집된 레코드가 없습니다. 네트워크 상태나 선택자를 확인하세요.")

    df = pd.DataFrame(records).drop_duplicates()

    before = len(df)
    df = df.dropna(subset=["제목", "가격", "평점"])  
    dropped = before - len(df)
    if dropped:
        logger.info("결측치로 인해 %d개 행 제거", dropped)

    return df


def analyze(df):
    """질문: 5점 만점(별 5개) 책의 비율은?"""
    counts = df["평점"].value_counts()
    five_star_ratio = counts.get("Five", 0) / len(df) * 100
    logger.info("평점별 분포:\n%s", counts.to_string())
    logger.info("5점 만점 책 비율: %.2f%%", five_star_ratio)
    return five_star_ratio, counts


if __name__ == "__main__":
    logger.info("크롤링 시작: %s", START_URL)
    records, visited_pages = crawl()

    df = clean(records)
    assert visited_pages >= 3, "3페이지 이상 방문 요구사항 미충족"
    assert len(df) >= 50, "최소 50건 요구사항 미충족"
    assert df.isna().mean().max() < 0.20, "결측 비율 20% 초과"

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    logger.info("저장 완료: %s (총 %d행, %d페이지 방문)", CSV_PATH, len(df), visited_pages)

    ratio, counts = analyze(df)
    print(f"\n[분석 결과] 5점 만점 책 비율: {ratio:.2f}%")
    print(counts)