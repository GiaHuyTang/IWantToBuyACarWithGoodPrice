import requests
from bs4 import BeautifulSoup
import re, json, argparse, os
from math import ceil
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========== Load Known Models Dictionary ==========
KNOWN_MODELS = {
  "acura": ["ILX", "TLX", "RLX", "MDX", "RDX", "ZDX", "Integra (2023+)"],
  "alfa romeo": ["Giulia", "Stelvio", "4C"],
  "aston martin": ["DB9", "DB11", "Vantage", "Rapide"],
  "audi": [
    "A3",
    "A4",
    "A5",
    "A6",
    "A7",
    "A8",
    "Q3",
    "Q5",
    "Q7",
    "Q8",
    "TT",
    "R8",
    "e-tron"
  ],
  "bentley": ["Continental GT", "Flying Spur", "Bentayga"],
  "bmw": [
    "1 Series",
    "2 Series",
    "3 Series",
    "4 Series",
    "5 Series",
    "6 Series",
    "7 Series",
    "8 Series",
    "X1",
    "X3",
    "X5",
    "X6",
    "X7",
    "Z4",
    "i3",
    "i4",
    "i8"
  ],
  "buick": ["Encore", "Envision", "Enclave", "Regal (2000s)", "LaCrosse"],
  "cadillac": [
    "CTS",
    "ATS",
    "CT4",
    "CT5",
    "CT6",
    "Escalade",
    "XT4",
    "XT5",
    "XT6",
    "Lyriq"
  ],
  "chevrolet": [
    "Aveo",
    "Cruze",
    "Malibu",
    "Impala (2000s)",
    "Camaro (2009+)",
    "Corvette C6/C7/C8",
    "Equinox",
    "Traverse",
    "Tahoe",
    "Suburban",
    "Silverado",
    "Bolt EV"
  ],
  "chrysler": ["300", "Pacifica", "Voyager (2019+)"],
  "dodge": [
    "Charger",
    "Challenger",
    "Durango",
    "Journey",
    "Grand Caravan (2000s)",
    "Ram 1500"
  ],
  "ferrari": [
    "458 Italia",
    "488",
    "F8 Tributo",
    "Roma",
    "Portofino",
    "California",
    "LaFerrari"
  ],
  "fiat": ["500", "500X", "500L", "124 Spider"],
  "ford": [
    "Focus (2000s)",
    "Fusion",
    "Taurus (2000s)",
    "Mustang (2005+)",
    "Escape",
    "Edge",
    "Explorer",
    "Expedition",
    "F-150",
    "Ranger (2019+)",
    "Bronco (2021+)"
  ],
  "genesis": ["G70", "G80", "G90", "GV70", "GV80"],
  "gmc": ["Terrain", "Acadia", "Yukon", "Sierra 1500", "Canyon"],
  "honda": [
    "Civic (2000+)",
    "Accord (2000+)",
    "Fit",
    "HR-V",
    "CR-V",
    "Pilot",
    "Odyssey",
    "Ridgeline"
  ],
  "hyundai": [
    "Elantra",
    "Sonata",
    "Accent",
    "Kona",
    "Tucson",
    "Santa Fe",
    "Palisade",
    "Veloster",
    "Ioniq",
    "Ioniq 5"
  ],
  "infiniti": ["G35/G37", "Q50", "Q60", "QX50", "QX60", "QX80"],
  "jaguar": ["XE", "XF", "XJ (2000s)", "F-Pace", "E-Pace", "I-Pace", "F-Type"],
  "jeep": [
    "Wrangler",
    "Cherokee",
    "Grand Cherokee",
    "Compass",
    "Renegade",
    "Gladiator"
  ],
  "kia": [
    "Rio",
    "Forte",
    "Soul",
    "Seltos",
    "Sportage",
    "Sorento",
    "Telluride",
    "Stinger",
    "EV6"
  ],
  "land rover": [
    "Range Rover",
    "Range Rover Sport",
    "Range Rover Evoque",
    "Discovery",
    "Defender (2020+)"
  ],
  "lexus": ["IS", "ES", "GS", "LS", "NX", "RX", "GX", "LX", "UX"],
  "lincoln": [
    "MKZ",
    "Continental (2000s)",
    "Corsair",
    "Nautilus",
    "Aviator",
    "Navigator"
  ],
  "mazda": ["Mazda3", "Mazda6", "CX-3", "CX-5", "CX-9", "CX-30", "MX-5"],
  "mercedes-benz": [
    "A-Class",
    "B-Class",
    "C-Class",
    "E-Class",
    "S-Class",
    "CLA",
    "CLS",
    "GLA",
    "GLC",
    "GLE",
    "GLS",
    "G-Class",
    "EQC",
    "EQE",
    "EQS"
  ],
  "mini": [
    "John Cooper Works",
    "Cooper Hardtop S",
    "Cooper Hardtop",
    "3 Door Cooper S",
    "3 Door Cooper",
    "5 Door Cooper S",
    "5 Door Cooper",
    "Countryman Cooper S",
    "Countryman",
    "Clubman Cooper S",
    "Clubman",
    "Convertible Cooper S",
    "Convertible",
    "Paceman",
    "Roadster",
    "Coupe",
    "Cooper SE",
    "Cooper S",
    "Cooper"
  ],
  "mitsubishi": ["Lancer (2000s)", "Outlander", "Eclipse Cross", "RVR"],
  "nissan": [
    "Versa",
    "Sentra",
    "Altima",
    "Maxima",
    "370Z",
    "GT-R",
    "Kicks",
    "Rogue",
    "Murano",
    "Pathfinder",
    "Armada",
    "Frontier",
    "Titan",
    "Leaf"
  ],
  "porsche": [
    "911 (996+)",
    "Boxster (986+)",
    "Cayman",
    "Panamera",
    "Macan",
    "Cayenne",
    "Taycan"
  ],
  "ram": ["1500", "2500", "3500", "ProMaster"],
  "subaru": [
    "Impreza",
    "Legacy",
    "WRX",
    "BRZ",
    "Crosstrek",
    "Forester",
    "Outback",
    "Ascent"
  ],
  "tesla": ["Model S", "Model 3", "Model X", "Model Y", "Cybertruck"],
  "toyota": [
    "Yaris",
    "Corolla",
    "Camry",
    "Avalon",
    "Prius",
    "C-HR",
    "RAV4",
    "Venza",
    "Highlander",
    "4Runner",
    "Sequoia",
    "Tacoma",
    "Tundra",
    "Sienna"
  ],
  "volkswagen": [
    "Golf",
    "Jetta",
    "Passat",
    "Arteon",
    "Beetle (2000s)",
    "Tiguan",
    "Atlas",
    "Touareg",
    "ID.4"
  ],
  "volvo": [
    "S40 (2000s)",
    "S60",
    "S80 (2000s)",
    "S90",
    "V60",
    "V90",
    "XC40",
    "XC60",
    "XC90"
  ]
}

# ========== Parse title to extract year + model ==========
def parse_title(title, brand):
    year, model = None, None
    if not title:
        return year, model
    m = re.match(r"^(\d{4})", title)
    if m:
        year = int(m.group(1))
    brand_models = KNOWN_MODELS.get(brand.lower(), [])
    title_lower = title.lower()
    for m in brand_models:
        if m.lower() in title_lower:
            model = m
            break
    return year, model

# ========== Normalize listing ==========
def normalize_listing(listing):
    price = listing.get("price")
    if price:
        price_num = re.sub(r"[^\d]", "", price)
        price_val = int(price_num) if price_num else None
    else:
        price_val = None

    mileage = listing.get("mileage")
    if mileage:
        mileage_num = re.sub(r"[^\d]", "", mileage)
        mileage_val = int(mileage_num) if mileage_num else None
    else:
        mileage_val = None

    year_val = int(listing["year"]) if listing.get("year") and str(listing["year"]).isdigit() else None

    ordered = {
        "title": listing.get("title"),
        "price": price_val,
        "mileage_km": mileage_val,
        "year": year_val,
        "model": listing.get("model"),
        "province_city": listing.get("province_city"),
        "link": listing.get("link")
    }
    return ordered

# ========== Step 0: Parse command-line arguments ==========
parser = argparse.ArgumentParser(description="Crawl AutoTrader car listings")
parser.add_argument("--brand", type=str, default="mini", help="Car brand (e.g., mini, toyota, honda)")
parser.add_argument("--location", type=str, default="canada", help="Location (not really used in AutoTrader URL)")
parser.add_argument("--outfile", type=str, default="autotrader_result.json", help="Output JSON file name")
args = parser.parse_args()

brand = args.brand.lower()
location = args.location.lower()
outfile = args.outfile

# Save results into ../results/ folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

outfile = os.path.join(RESULTS_DIR, args.outfile)

# ========== Step 1: Setup session ==========
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
})

# ========== Step 2: Detect total results ==========
offset = 0
url = f"https://www.autotrader.ca/cars/{brand}/?rcp=100&rcs={offset}"
resp = session.get(url)
soup = BeautifulSoup(resp.text, "html.parser")

total_results = 0
total_tag = soup.find("span", class_="title-count")
if total_tag:
    total_results = int(total_tag.get_text(strip=True).replace(",", ""))
print("Total results detected:", total_results)

rcp = 100
num_pages = ceil(total_results / rcp) if total_results else 1
print("Total pages:", num_pages)

# ========== Step 3: Define fetch_page function ==========
def fetch_page(page):
    offset = (page - 1) * rcp
    url = f"https://www.autotrader.ca/cars/{brand}/?rcp={rcp}&rcs={offset}"
    print(f"Fetching page {page}: {url}")
    r = session.get(url)
    cars = []
    if r.status_code != 200:
        return page, cars
    soup = BeautifulSoup(r.text, "html.parser")

    for li in soup.select('div.result-item'):
        title_tag = li.select_one('.title-with-trim')
        price_tag = li.select_one('.price-amount')
        mileage_tag = li.select_one('.kms')
        province_city = None

        # Try proximity box first
        loc_box = li.select_one("div.proximity")
        if loc_box:
            span = loc_box.find("span", class_="proximity-text")
            if span:
                province_city = span.get_text(strip=True)

        # Fallback: parse from href
        if not province_city:
            link_tag = li.select_one("a.inner-link")
            if link_tag and link_tag.has_attr("href"):
                parts = link_tag["href"].split("/")
                if len(parts) >= 6:
                    city = unquote(parts[-4])
                    province = unquote(parts[-3])
                    province_city = f"{city}, {province}"

        link_tag = li.select_one('a.inner-link')
        title = title_tag.get_text(strip=True) if title_tag else None
        link = "https://www.autotrader.ca" + link_tag['href'] if link_tag and link_tag.has_attr('href') else None
        price = price_tag.get_text(strip=True) if price_tag else None
        mileage = mileage_tag.get_text(strip=True) if mileage_tag else None

        year, model = parse_title(title, brand)

        raw_car = {
            "title": title,
            "price": price,
            "mileage": mileage,
            "year": year,
            "model": model,
            "province_city": province_city,
            "link": link
        }
        cars.append(normalize_listing(raw_car))
    return page, cars

# ========== Step 4: Fetch pages concurrently ==========
from concurrent.futures import ThreadPoolExecutor, as_completed

number_of_workers = min(32, max(4, int(num_pages / 4)))
all_cars = []
with ThreadPoolExecutor(max_workers=number_of_workers) as executor:
    futures = [executor.submit(fetch_page, p) for p in range(1, num_pages + 1)]
    for future in as_completed(futures):
        page, cars = future.result()
        all_cars.extend(cars)

# ========== Step 5: Save results ==========
result_json = {
    "brand": brand,
    "location": location,
    "total_number": len(all_cars),
    "total_pages": num_pages,
    "source": "autotrader.ca",
    "listings": all_cars
}

with open(outfile, "w", encoding="utf-8") as f:
    json.dump(result_json, f, indent=4, ensure_ascii=False)

print("===================================")
print(f"Total {brand.upper()} cars found:", len(all_cars))
print(f"Results saved to {outfile}")