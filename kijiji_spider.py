import sys, os, json, requests, re, argparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

# ========== Load Known Models Dictionary ==========
# This dictionary contains known car models for each brand.
# It helps us parse the title and correctly identify the model.
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
# We use Selenium only to detect pagination (last page number).
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
    # Wait until pagination links appear
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
# After detecting the last page, we switch to requests + BeautifulSoup
# for faster scraping of all pages.
BASE_URL = f"https://www.kijiji.ca/b-cars-trucks/{location}/{brand}/page-{{}}/c174l0a54?view=list"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
})

def parse_title(title_text: str, brand: str):
    """
    Extract year and model from the title.
    Uses the known_models dictionary for strict matching.
    """
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
    brand_models = KNOWN_MODELS.get(brand.lower(), [])
    text_lower = rest_clean.lower()

    # Match longest candidate first
    for candidate in sorted(brand_models, key=lambda x: -len(x)):
        pattern = r"\b" + re.escape(candidate.lower()) + r"\b"
        if re.search(pattern, text_lower):
            model = candidate
            break

    return year, model

def normalize_listing(listing):
    """
    Normalize raw scraped data into clean, consistent fields
    and enforce a fixed key order for JSON output.
    """
    # --- Normalize price ---
    price = listing.get("price")
    if price:
        price_num = re.sub(r"[^\d]", "", price)  # remove non-digit characters
        price_val = int(price_num) if price_num else None
    else:
        price_val = None

    # --- Normalize mileage ---
    mileage = listing.get("mileage")
    if mileage:
        mileage_num = re.sub(r"[^\d]", "", mileage)
        mileage_val = int(mileage_num) if mileage_num else None
    else:
        mileage_val = None

    # --- Normalize year ---
    year_val = int(listing["year"]) if listing.get("year") and str(listing["year"]).isdigit() else None

    # --- Transmission & fuel ---
    transmission_val = listing.get("transmission").capitalize() if listing.get("transmission") else None
    fuel_val = listing.get("fuel").capitalize() if listing.get("fuel") else None

    # --- Build dictionary in desired order ---
    ordered = {
        "title": listing.get("title"),
        "price": price_val,
        "mileage_km": mileage_val,
        "transmission": transmission_val,
        "fuel": fuel_val,
        "year": year_val,
        "model": listing.get("model"),
        "deal_tag": listing.get("deal_tag"),   # added deal tag field
        "link": listing.get("link")
    }
    return ordered


def clean_deal_tag(tag_text: str):
    """
    Normalize deal tag text like 'Great price!' or 'Good deal'
    into a clean label: 'Great', 'Good', 'Fair', 'Overpriced', or 'Unknown'.
    """
    if not tag_text:
        return "Unknown"
    text = tag_text.lower()
    if "great" in text:
        return "Great"
    elif "good" in text:
        return "Good"
    elif "fair" in text:
        return "Fair"
    elif "over" in text:  # e.g. 'Overpriced'
        return "Overpriced"
    else:
        return "Unknown"


def fetch_page(page):
    """
    Fetch and parse a single page of listings.
    Returns a list of normalized car dictionaries.
    """
    url = BASE_URL.format(page)
    r = session.get(url, timeout=10)
    if r.status_code != 200:
        return page, []
    soup = BeautifulSoup(r.content, "html.parser")
    cars = []
    for li in soup.select('li[data-testid^="listing-card-list-item"]'):
        # Extract title and price
        title_tag = li.select_one('a[data-testid="listing-link"]')
        price_tag = li.select_one('p[data-testid="autos-listing-price"]')

        # Extract deal tag (normalize it)
        deal_tag_el = li.select_one('div[class="sc-eb45309b-0 bOFieq"] span')
        deal_tag_raw = deal_tag_el.get_text(strip=True) if deal_tag_el else None
        deal_tag = clean_deal_tag(deal_tag_raw)

        # Extract details (mileage, transmission, fuel)
        details = li.select('p.sc-991ea11d-0.epsmyv.sc-4b5a8895-2.eEvVV')

        # Build link
        link = title_tag['href'] if title_tag and title_tag.has_attr('href') else None
        if link and not link.startswith("http"):
            link = "https://www.kijiji.ca" + link

        # Clean text
        title = title_tag.get_text(strip=True) if title_tag else None
        price = price_tag.get_text(strip=True) if price_tag else None

        mileage, transmission, fuel = None, None, None
        for d in details:
            text = d.get_text(strip=True).lower()
            if "km" in text:
                mileage = text
            elif "automatic" in text or "manual" in text:
                transmission = text
            elif any(fuel_type in text for fuel_type in ["gas", "diesel", "electric", "hybrid"]):
                fuel = text

        # Parse year and model from title
        year, model = parse_title(title, brand)

        # Raw listing dictionary
        raw_listing = {
            "title": title,
            "price": price,
            "mileage": mileage,
            "transmission": transmission,
            "fuel": fuel,
            "year": year,
            "model": model,
            "deal_tag": deal_tag,   # normalized deal tag
            "link": link
        }
        cars.append(normalize_listing(raw_listing))
    return page, cars

# ========== Step 3: Run crawl ==========
# Use ThreadPoolExecutor to fetch multiple pages concurrently.
number_of_workers = min(32, max(4, int(last_page / 4)))
all_cars = []
with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
    futures = [executor.submit(fetch_page, p) for p in range(1, last_page+1)]
    for future in as_completed(futures):
        page, cars = future.result()
        print(f"Page {page}: {len(cars)} cars")
        all_cars.extend(cars)

# ========== Step 4: Save results ==========
# Save the final normalized JSON with metadata.
result_json = {
    "brand": brand,
    "location": location,
    "total_number": len(all_cars),
    "total_pages": last_page,
    "scraped_at": datetime.utcnow().isoformat() + "Z",
    "source": "kijiji.ca",
    "listings": all_cars
}

with open(outfile, "w", encoding="utf-8") as f:
    json.dump(result_json, f, indent=4, ensure_ascii=False)

print("===================================")
print(f"Total {brand.upper()} cars found:", len(all_cars))
print(f"Results saved to {outfile}")
