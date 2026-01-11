import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
from io import BytesIO
from dataclasses import dataclass, asdict
from typing import List
import json

BASE = "https://www.fylladiomat.gr"
BASE_URL_JSON = "https://feizidischristos.github.io/super/flyers/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = "flyers"

@dataclass
class Retailer:
    name: str
    logo: str
    catalog: str

    def to_dict(self):
        return asdict(self)

@dataclass
class CatalogIndex:
    base_url: str
    retailers: List[Retailer]

    def save(self, path: str):
        payload = {
            "base_url": self.base_url,
            "retailers": [r.to_dict() for r in self.retailers]
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)


BROCHURES_NAME_DIC = {"Bazaar": "bazaar",
             "Discount Markt": "discount_markt",
             "ENA Cash & Carry": "ena_cash_&_carry",
             "Express Market": "express_market",
             "Lidl": "lidl",
             "Market in": "market_in",
             "METRO Cash & Carry": "metro_cash_&_carry",
             "My market": "my_market",
             "Synka": "synka",
             "The Mart": "the_mart",
             "ΑΒ Βασιλόπουλος": "ab_vasilopoulos",
             "Ανδρικοπουλος": "adrikopoulos",
             "Αριάδνη": "ariadni",
             "Γαλαξίας": "galaxias",
             "Ελληνικά market": "ellinika_market",
             "ΕΛΟΜΑΣ": "elomas",
             "Θανόπουλος": "thanopoulos",
             "ΚΡΗΤΙΚΟΣ": "kritikos",
             "Μασούτης": "masoutis",
             "ΣΚΛΑΒΕΝΙΤΗΣ": "sklavenitis",
             "Χαλκιαδάκης": "chalkiadakis"
             }

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_brands():
    soup = BeautifulSoup(
        requests.get(f"{BASE}/souper-market/", headers=HEADERS).text,
        "html.parser"
    )

    brands = {}
    for a in soup.nav.find("li", class_="has_child active"):
            for cat in a.find_all("li"):
                name = cat.get_text(strip=True)
                href = cat.find("a").get("href")

                if name:
                    brands[name] = urljoin(BASE, href)


    return brands

def get_brochures(brand_url):
    soup = BeautifulSoup(
        requests.get(brand_url, headers=HEADERS).text,
        "html.parser"
    )

    brochures = []


    for g in soup.body.main.find("div", class_="container shop-page"):
#        print("\n\n")
        i = g.find("div", class_="row").find("div", class_="row").find("div", class_="brochure-thumb").find("a").get("href")
        brochures.append(urljoin(BASE, i))
#        print(brochures)
#        print("\n")

    return list(dict.fromkeys(brochures))

def get_logo(brand_url):
    soup = BeautifulSoup(
        requests.get(brand_url, headers=HEADERS).text,
        "html.parser"
    )

    for g in soup.body.main.find("div", class_="frame"):
        i = g.get("src").split(".png?",1)[0] + (".png")

    return i

def get_brochure_images(brochure_url):

    soup = BeautifulSoup(
        requests.get(brochure_url, headers=HEADERS).text,
        "html.parser"
    )

    images = []
    totalNumPages = 0
    for nu in soup.find_all("a", class_ = "btn btn-default page-num btn-sm navigate-brochure"):
        totalNumPages = nu.string
#    print("\n")
#    print(totalNumPages)
    brochure_url = urljoin(brochure_url, "?page=")
#    print(brochure_url)
#    print("\n")

    for p in range(1,int(totalNumPages)):
        soup = BeautifulSoup(
            requests.get(brochure_url + str(p), headers=HEADERS).text,
            "html.parser"
        )

        for pic in soup.find_all("img", id = "pageImage"):
            img = pic.get("src")
#            print(img)
            images.append(img)


#    # Remove duplicates, keep order
    seen = set()
    ordered = []
    for img in images:
        if img not in seen:
            seen.add(img)
            ordered.append(img)

    return ordered


def create_brand_pdf(brand_name, image_urls):
    images = []

    for url in image_urls:
        r = requests.get(url, headers=HEADERS)
        img = Image.open(BytesIO(r.content)).convert("RGB")
        images.append(img)

    if images:
        pdf_path = os.path.join(
            OUTPUT_DIR,
            f"{brand_name}.pdf"
        )
        images[0].save(
            pdf_path,
            save_all=True,
            append_images=images[1:]
        )
        print(f" Saved {pdf_path}")

def main():
    brands = get_brands()

    retailers = []

    for brand, brand_url in brands.items():
        print(f"\n Processing brand: {brand}, {brand_url}")

        all_images = []

        brochures = get_brochures(brand_url)

        print(f" Found {len(brochures)} brochures")

        brochureName  = BROCHURES_NAME_DIC[brand]

        logoUrl = get_logo(brand_url)

        retailers.append(
            Retailer(
                name=brand,
                logo=logoUrl,
                catalog=f"{brochureName}.pdf"
            )
        )

        for brochure in brochures:
            imgs = get_brochure_images(brochure)
            print(f"{len(imgs)} pages")
            all_images.extend(imgs)

        if all_images:
            create_brand_pdf(brochureName, all_images)
        else:
            print("No images found")

    print("🧾 Generating index.json")

    index = CatalogIndex(
        base_url=BASE_URL_JSON,
        retailers=retailers
    )

    index.save("flyers/index.json")


if __name__ == "__main__":
    main()

