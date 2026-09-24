import json
import os
import re
from bs4 import BeautifulSoup
import requests

# CONFIGURATION
NTFY_TOPIC = (
    "my-sgcarmart-tracker-xyz987"  # Replace with your unique ntfy topic name
)
SEARCH_URLS = [
    "https://www.sgcarmart.com/used-cars/listing?q=Toyota+Roomy",
    "https://www.sgcarmart.com/used-cars/listing?q=Toyota+Tank",
]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
SEEN_FILE = "seen.json"


def load_seen():
  if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
      return set(json.load(f))
  return set()


def save_seen(seen_set):
  with open(SEEN_FILE, "w") as f:
    json.dump(list(seen_set), f)


def send_ntfy(title, message, click_url):
  # Sends a rich notification to your ntfy app with a clickable link
  requests.post(
      f"https://ntfy.sh/{NTFY_TOPIC}",
      data=message.encode("utf-8"),
      headers={
          "Title": title,
          "Priority": "high",
          "Tags": "car",
          "Click": click_url,
      },
  )


def run_tracker():
  seen_links = load_seen()
  new_listings_found = False

  for url in SEARCH_URLS:
    try:
      response = requests.get(url, headers=HEADERS, timeout=10)
      if response.status_code != 200:
        continue

      soup = BeautifulSoup(response.text, "html.parser")
      item_cards = soup.select(".box_sub, .row")

      for card in item_cards:
        title_elem = card.select_one("a.element_title, .listing-title, h3 a, a")
        if not title_elem:
          continue

        title_text = title_elem.get_text(strip=True)

        # Match name strictly
        if not (
            re.search(r"\btoyota\s+roomy\b", title_text, re.IGNORECASE)
            or re.search(r"\btoyota\s+tank\b", title_text, re.IGNORECASE)
        ):
          continue

        link = title_elem.get("href", "")
        if link and not link.startswith("http"):
          link = "https://www.sgcarmart.com/used-cars/" + link.lstrip("/")

        # Skip if we already alerted you about this link
        if link in seen_links:
          continue

        # Extract Price & Year/Reg
        price_elem = card.select_one(".price, .element_price, span[style*='red']")
        price = (
            price_elem.get_text(strip=True) if price_elem else "Price on Ask"
        )

        desc_text = card.get_text()
        year_match = re.search(
            r"(\d{2}-[A-Za-z]{3}-\d{4}|\b20\d{2}\b)", desc_text
        )
        reg_info = year_match.group(1) if year_match else "N/A"

        # Format message content
        msg = f"Reg/Year: {reg_info}\nPrice: {price}\nSource: SGCarMart"
        send_ntfy(f"New! {title_text}", msg, link)

        seen_links.add(link)
        new_listings_found = True

    except Exception as e:
      print(f"Error: {e}")

  save_seen(seen_links)


if __name__ == "__main__":
  run_tracker()
