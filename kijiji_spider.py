import sys, os, json, requests, re, argparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

# ========== Load Known Models Dictionary ==========
with open("known_models.json", "r", encoding="utf-8") as f:
    KNOWN_MODELS = json.load(f)

# ========== Step 0: Parse command-line arguments ==========
parser = argparse.ArgumentParser(description="Crawl Kijiji car listings")
parser.add_argument("--brand", type=str, default="mini", help="Car brand (e.g., mini, toyota, honda)")
parser.add_argument("--location", type=str, default="canada", help="Location (e.g., canada, ontario, saskatchewan)")
parser.add_argument("--outfile", type=str, default="result.json", help="Output JSON file name")
args = parser.parse_args()

brand = args.brand.lower()
location = args.location.lower() or "canada"
outfile = args.outfile or "result.json"

# ========== Step 1: Use Selenium to detect the last page ==========
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--log-level=3")
options.add_experimental_option("excludeSwitches", ["enable-logging"])

service = Service("./msedgedriver.exe", log_path=os.devnull)
driver = webdriver.Edge(service=service, options=options)

url = f"https://www.kijiji.ca/b-cars-trucks/{location}/{brand}/c174l0a54?view=list"
driver.get(url)

try:
    # Wait for pagination links to appear
    page_links = WebDriverWait(driver, 5).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, 'li[data-testid="pagination-list-item"] a[data-testid="pagination-link-item"]')
        )
    )
    last_page = 1
    if page_links:
        # Extract the last page number from the last pagination link
        last_href = page_links[-1].get_attribute("href")
        match = re.search(r'/page-(\d+)/', last_href)
        if match:
            last_page = int(match.group(1))
except:
    print("No last page found, defaulting to 1 page.")
    last_page = 1

print("Last page detected:", last_page)
driver.quit()

# ========== Step 2: Requests + BeautifulSoup ==========
BASE_URL = f"https://www.kijiji.ca/b-cars-trucks/{location}/{brand}/page-{{}}/c174l0a54?view=list"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
})

def parse_title(title_text: str, brand: str):
    """Extract year and model strictly from the known_models dictionary."""
    year, model = None, None
    if not title_text:
        return year, model

    # Extract year if present at the beginning
    m = re.match(r"(\d{4})\s+(.*)", title_text)
    if m:
        year = m.group(1)
        rest = m.group(2)
    else:
        rest = title_text

    # Clean up title (remove text after '|')
    rest_clean = rest.split("|")[0].strip()

    # Strict dictionary-only matching: longest candidates first, with word boundaries
    brand_models = KNOWN_MODELS.get(brand.lower(), [])
    text_lower = rest_clean.lower()

    for candidate in sorted(brand_models, key=lambda x: -len(x)):
        pattern = r"\b" + re.escape(candidate.lower()) + r"\b"
        if re.search(pattern, text_lower):
            model = candidate
            break

    return year, model

def fetch_page(page):
    """Fetch and parse a single page of listings."""
    url = BASE_URL.format(page)
    r = session.get(url, timeout=10)
    if r.status_code != 200:
        return page, []
    soup = BeautifulSoup(r.content, "html.parser")
    cars = []
    for li in soup.select('li[data-testid^="listing-card-list-item"]'):
        title_tag = li.select_one('a[data-testid="listing-link"]')
        price_tag = li.select_one('p[data-testid="autos-listing-price"]')
        details = li.select('p.sc-991ea11d-0.epsmyv.sc-4b5a8895-2.eEvVV')
        link = title_tag['href'] if title_tag and title_tag.has_attr('href') else None
        if link and not link.startswith("http"):
            link = "https://www.kijiji.ca" + link

        title = title_tag.get_text(strip=True) if title_tag else None
        price = price_tag.get_text(strip=True) if price_tag else None

        mileage, transmission, fuel = None, None, None
        for d in details:
            text = d.get_text(strip=True).lower()
            if "km" in text:
                mileage = text
            elif "automatic" in text or "manual" in text:
                transmission = text.capitalize()
            elif any(fuel_type in text for fuel_type in ["gas", "diesel", "electric", "hybrid"]):
                fuel = text.capitalize()

        year, model = parse_title(title, brand)

        cars.append({
            "title": title,
            "price": price,
            "mileage": mileage,
            "transmission": transmission,
            "fuel": fuel,
            "year": year,
            "model": model,
            "link": link
        })
    return page, cars

# ========== Step 3: Run crawl ==========
number_of_workers = min(32, max(4, int(last_page / 4)))
all_cars = []
with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
    futures = [executor.submit(fetch_page, p) for p in range(1, last_page+1)]
    for future in as_completed(futures):
        page, cars = future.result()
        print(f"Page {page}: {len(cars)} cars")
        all_cars.extend(cars)

# ========== Step 4: Save results ==========
result_json = {
    "result": {
        "Brand": brand.upper(),
        "Total_Number": len(all_cars),
        "Location": location.capitalize(),
        "Total_Pages": last_page,
        "Listings": all_cars
    }
}

with open(outfile, "w", encoding="utf-8") as f:
    json.dump(result_json, f, indent=4, ensure_ascii=False)

print("===================================")
print(f"Total {brand.upper()} cars found:", len(all_cars))
print(f"Results saved to {outfile}")
