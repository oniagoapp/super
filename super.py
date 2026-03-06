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
             "ΑΦΡΟΔΙΤΗ": "afroditi",
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

def getBrands():
    soup = BeautifulSoup(
        requests.get(f"{BASE}/souper-market/", headers=HEADERS).text,
        "html.parser"
    )

    brands = {}

    for brandsContainer in soup.main.find("div", class_="the-page").find("div", id="sidebar").find("div", class_="box"):
        for brandItem in brandsContainer.find_all("li"):
            name = brandItem.get_text(strip=True)
            href = brandItem.find("a").get("href")

            if name:
                brands[name] = urljoin(BASE, href)

    return brands

def getBrandBrochuresUrl(brand_url):
    soup = BeautifulSoup(
        requests.get(brand_url, headers=HEADERS).text,
        "html.parser"
    )

    brochures = []

    for brandContainer in soup.body.main.find("div", class_="container shop-page"):
        if brandContainer.find("div", class_="row").find("div", class_="row").find("div", class_="brochure-thumb") != None:
            urlBrandAppending = brandContainer.find("div", class_="row").find("div", class_="row").find("div", class_="brochure-thumb").find("a").get("href")
            brochures.append(urljoin(BASE, urlBrandAppending))

    return list(dict.fromkeys(brochures))

def getLogo(brand_url):
    soup = BeautifulSoup(
        requests.get(brand_url, headers=HEADERS).text,
        "html.parser"
    )

    for logoContainer in soup.body.main.find("div", class_="frame"):
        logoUrl = logoContainer.get("src").split(".png?",1)[0] + (".png")

    return logoUrl

def downloadLogo(logoUrl, brand):

    imgData = requests.get(logoUrl).content
    with open(f"flyers/logo/{brand}.jpg", "wb") as handler:
        handler.write(imgData)

def getBrochureImages(brochure_url):

    soup = BeautifulSoup(
        requests.get(brochure_url, headers=HEADERS).text,
        "html.parser"
    )

    images = []
    totalNumPages = 0
    for totalPageNumber in soup.find_all("a", class_ = "btn btn-default page-num btn-sm navigate-brochure"):
        totalNumPages = totalPageNumber.string
    brochure_url = urljoin(brochure_url, "?page=")

    for p in range(1,int(totalNumPages)):
        brochureUrlWithPage = brochure_url + str(p)
        soup = BeautifulSoup(
            requests.get(brochureUrlWithPage, headers=HEADERS).text,
            "html.parser"
        )

        for brochurePageElement in soup.find_all("img", id = "pageImage"):
            img = brochurePageElement.get("src")
            images.append(img)

#    # Remove duplicates, keep order
    seen = set()
    ordered = []
    for img in images:
        if img not in seen:
            seen.add(img)
            ordered.append(img)

    return ordered


def createBrandPdf(brand_name, image_urls):
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
    brands = getBrands()

    retailers = []

    for brand, brand_url in brands.items():
        print(f"\n Processing brand: {brand}, {brand_url}")

        all_images = []

        brochures = getBrandBrochuresUrl(brand_url)

        brochureName  = BROCHURES_NAME_DIC[brand]
        logoName  = BROCHURES_NAME_DIC[brand]

        logoUrl = getLogo(brand_url)

        downloadLogo(logoUrl, logoName)

        if brochures:
            print(f" Found {len(brochures)} brochures")
            retailers.append(
                Retailer(
                    name=brand,
                    logo=f"logo/{logoName}.jpg",
                    catalog=f"{brochureName}.pdf"
                )
        )
        else:
            print(f" Found {len(brochures)} brochures")
            retailers.append(
                Retailer(
                    name=brand,
                    logo=f"logo/{logoName}.jpg",
                    catalog= None
                )

        )

        for brochure in brochures:
            imgs = getBrochureImages(brochure)
            print(f"{len(imgs)} pages")
            all_images.extend(imgs)

        if all_images:
            createBrandPdf(brochureName, all_images)
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