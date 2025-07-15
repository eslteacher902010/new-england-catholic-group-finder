import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv
from opencage.geocoder import OpenCageGeocode

# Load API key
load_dotenv()
geocoder = OpenCageGeocode(os.getenv("API_KEY"))

# Set up Chrome debugger connection
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

print("👉 Go to this URL and click a city tab: https://www.youngcatholicprofessionals.org/events")
input("🔁 After you see the event list appear, press ENTER...")

# Scroll a bit in case the iframe is lazy-loaded
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(2)

# Wait for iframe to load and switch to it
try:
    iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.eb-widget-event-list")))
    print("✅ Iframe found!")
    driver.switch_to.frame(iframe)
except TimeoutException:
    print("❌ Timed out waiting for iframe — it might not have loaded.")
    driver.quit()
    exit()

# Wait for event cards
try:
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".event-card")))
except TimeoutException:
    print("❌ Timed out waiting for event cards.")
    driver.quit()
    exit()

# Extract event data
scraped_data = []
events = driver.find_elements(By.CSS_SELECTOR, "li")

for event in events:
    try:
        title = event.find_element(By.CSS_SELECTOR, "h2 a").text.strip()
        link = event.find_element(By.CSS_SELECTOR, "h2 a").get_attribute("href")
        date = event.find_element(By.CSS_SELECTOR, "time").text.strip()
        location = event.find_element(By.CSS_SELECTOR, ".area.content").text.strip()

        geo_data = geocoder.geocode(location)
        lat, lon = (geo_data[0]['geometry']['lat'], geo_data[0]['geometry']['lng']) if geo_data else (None, None)

        scraped_data.append({
            "title": title,
            "date": date,
            "location": location,
            "link": link,
            "lat": lat,
            "lon": lon
        })
    except Exception as e:
        print(f"⚠️ Error parsing event: {e}")

driver.quit()

# Save to CSV
csv_path = "ycp_events.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["title", "date", "location", "link", "lat", "lon"])
    writer.writeheader()
    writer.writerows(scraped_data)

print(f"✅ CSV saved as `{csv_path}` with {len(scraped_data)} events.")
