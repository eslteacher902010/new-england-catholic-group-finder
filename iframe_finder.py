from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")  # or omit for standalone Chrome
driver = webdriver.Chrome(options=options)

driver.get("https://www.youngcatholicprofessionals.org/events")
time.sleep(5)  # let JS load

page_source = driver.page_source
soup = BeautifulSoup(page_source, "html.parser")
iframes = soup.find_all("iframe", class_="eb-widget-event-list")

for i, iframe in enumerate(iframes):
    print(f"{i+1}. {iframe['src']}")

