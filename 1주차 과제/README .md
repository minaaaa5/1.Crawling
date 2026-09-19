# requests와 BeautifulSoup으로 books.toscrape.com 크롤링하기

## 과제 목표

[#과제-목표](#과제-목표)

**"5점 만점(별 5개) 책의 비율은 얼마나 되는가?"** 라는 질문에 답하기 위해,
책 목록 페이지를 순회하며 제목·가격·평점·재고 정보를 수집하고 CSV로 정리했다.

## 대상 사이트: books.toscrape.com

[#대상-사이트-bookstoscrapecom](#대상-사이트-bookstoscrapecom)

![여기에 books.toscrape.com 목록 페이지 스크린샷 삽입](스크린샷_경로.png)

- 웹 크롤링 연습을 위해 공식적으로 운영되는 목(mock) 온라인 서점.
- 로그인·결제 등 민감한 기능이 없고 페이지 구조가 단순해 수업에서 배운
  requests + BeautifulSoup 조합으로 접근하기에 적합하다고 판단했다.
- robots.txt(<https://books.toscrape.com/robots.txt>) 확인 결과 수집을 막는
  Disallow 규칙이 없고, 사이트 자체가 "크롤링 연습용"임을 명시하고 있다.

## 목록 페이지 파싱 구현

[#목록-페이지-파싱-구현](#목록-페이지-파싱-구현)

책 1권은 `article.product_pod` 태그 하나에 대응된다. 개발자 도구(F12)로 확인한
선택자들로 제목·가격·평점·재고 여부를 뽑아냈다.

```python
title = item.select_one("h3 a")["title"]
price = parse_price(item.select_one(".price_color").get_text(strip=True))
rating = item.select_one("p.star-rating")["class"][1]
availability = item.select_one(".instock.availability").get_text(strip=True)
```

- 제목은 `.text` 대신 `title` 속성에서 가져왔다. 화면에는 말줄임표(`...`)로
  잘려 보이지만, `title` 속성에는 전체 문장이 그대로 들어있기 때문이다.
- 평점은 `class="star-rating Three"`처럼 class 속성 두 번째 값으로 표현되어
  있어, 리스트 인덱스 `[1]`로 꺼냈다.

## 페이지 이동(pagination) 구현

[#페이지-이동pagination-구현](#페이지-이동pagination-구현)

`li.next a` 태그가 "다음 페이지" 링크다. 마지막 페이지에는 이 태그 자체가
사라지므로, 이를 반복문 종료 조건으로 사용했다.

```python
next_link = soup.select_one("li.next a")
next_url = urljoin(page_url, next_link["href"]) if next_link else None
```

페이지당 20권씩, 최대 5페이지(100권)까지 수집하도록 해 요구사항인
"3페이지 이상·50건 이상"을 여유 있게 충족했다.

## 예외 처리 및 로깅

[#예외-처리-및-로깅](#예외-처리-및-로깅)

![여기에 logs/crawl.log 실행 로그 스크린샷 삽입](스크린샷_경로.png)

- 요청마다 timeout(연결 5초/응답 20초)을 걸고, 403·429 응답이 오면 즉시
  크롤링을 중단하도록 했다 (과제 원칙 준수).
- 그 외 네트워크 오류는 `try/except`로 잡아 해당 페이지만 건너뛰고 로그로 남긴다.
- 요청 사이마다 1초 지연(`sleep(1.0)`)을 두어 서버 부담을 줄였다.
- 모든 진행 상황과 오류는 `logs/crawl.log`에 기록된다.

## 데이터 정제

[#데이터-정제](#데이터-정제)

- 중복 행: `drop_duplicates()`로 완전히 동일한 행 제거
- 결측치: title / price_gbp / rating 중 하나라도 비어 있으면 해당 행 제거
  (선택자가 예상과 다르게 매칭되지 않은 경우로 판단)
- 자료형: 가격을 `"£51.77"` 문자열에서 `51.77` 숫자(float)로 변환해
  이후 통계 계산이 가능하도록 함

## 실행 방법

[#실행-방법](#실행-방법)

```bash
pip install -r requirements.txt
python crawler.py
```

실행하면 `data/result.csv`와 `logs/crawl.log`가 자동으로 생성된다.

## 실행화면

[#실행화면](#실행화면)

![여기에 터미널 실행 결과(5점 만점 책 비율 출력) 스크린샷 삽입](스크린샷_경로.png)

![여기에 data/result.csv를 엑셀로 연 화면 스크린샷 삽입](스크린샷_경로.png)

## 결과 및 해석

[#결과-및-해석](#결과-및-해석)

- **5점 만점 책 비율: 19%**
- 5권 중 약 1권꼴로 만점 평가를 받았고, 나머지 81%는 1~4점에 분산되어 있었다.

## 한계

[#한계](#한계)

- 수집 범위를 5페이지(약 100건)로 제한해 전체 1,000권 중 일부만 반영함
- 평점은 별 개수 텍스트(One~Five)로만 표현되어 있어 세부 리뷰 점수는 알 수 없음

## AI 활용 내역

[#ai-활용-내역](#ai-활용-내역)

- Claude(Anthropic)를 활용해 requests/BeautifulSoup 기반 크롤링 코드 초안 작성,
  예외 처리·로깅·자료형 변환 로직 보완, 선택자 확인(실제 웹페이지 구조 조사)에 도움을 받음
- 최종 코드 실행과 결과 확인은 직접 수행함
