from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import logging
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_driver():
    chrome_options = Options()
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_college_names(driver):
    url = 'https://www.collegevine.com/schools/hub/all'
    driver.get(url)
    last_height = driver.execute_script("return document.body.scrollHeight")
    start_time = time.time()

    while time.time() - start_time < 30:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    anchors = soup.find_all('a', class_='h2 text-body flex-grow-1')

    college_names = [anchor.text.strip() for anchor in anchors]
    return college_names

def fetch_essay_prompts(driver, college_name):
    url = 'https://www.collegevine.com/college-essay-prompts#search-results'
    driver.get(url)
    time.sleep(5)

    try:
        input_group = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.input-group.input-group-lg"))
        )
        search_box = input_group.find_element(By.CSS_SELECTOR, "input[aria-label='Search for a school...']")
        search_box.clear()
        search_box.send_keys(college_name)

        search_button = input_group.find_element(By.CSS_SELECTOR, "a.btn.btn-sm.btn-primary")
        search_button.click()

        time.sleep(5)

        view_prompts_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'View Essay Prompts')]"))
        )
        view_prompts_button.click()
        time.sleep(5)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        prompts = []

        cards = soup.find_all('div', class_='card')
        for card in cards:
            try:
                title = card.find('h3', class_='mt-2').text.strip() if card.find('h3', class_='mt-2') else "No title"
                required = card.find('div', class_='badge badge-pill rounded-pill badge-warning bg-warning text-dark badge-float badge-float-inside mr-2').find('div', class_='h6 mb-0').text.strip() if card.find('div', class_='badge badge-pill rounded-pill badge-warning bg-warning text-dark badge-float badge-float-inside mr-2') else "No requirement"
                word_count = card.find('span', class_='text-secondary ml-2').text.strip() if card.find('span', class_='text-secondary ml-2') else "No word count"
                description = card.find('div', class_='card-body p-5').find_all('p')[1].text.strip() if len(card.find('div', class_='card-body p-5').find_all('p')) > 1 else "No description"
                prompts.append({'title': title, 'required': required, 'word_count': word_count, 'description': description})
            except AttributeError as e:
                logging.error(f"Error parsing prompt for {college_name}: {e}")

        return prompts
    except Exception as e:
        logging.error(f'Error fetching prompts for {college_name}: {e}')
        return []

options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
driver = setup_driver()

try:
    logging.info("Scraping college names from CollegeVine")
    college_names = get_college_names(driver)
    logging.info(f"Found {len(college_names)} colleges")

    with open('college_essay_prompts.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['College Name', 'Title', 'Required', 'Word Count', 'Description'])

        for college_name in college_names:
            logging.info(f"Fetching essay prompts for {college_name}")
            essay_prompts = fetch_essay_prompts(driver, college_name)
            for prompt in essay_prompts:
                writer.writerow([college_name, prompt['title'], prompt['required'], prompt['word_count'], prompt['description']])
            logging.info(f"Completed fetching prompts for {college_name}")
            logging.info('-' * 70)
except Exception as e:
    logging.error(f'An error occurred: {e}')
finally:
    driver.quit()
