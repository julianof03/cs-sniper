import os
import logging
import sys
import time
import warnings

import requests
import chromedriver_autoinstaller
import math
from cachetools import cached, TTLCache
from functools import lru_cache  # Importando o lru_cache corretamente

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC  # Corrigindo a importação
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from locators import PageLocators

# Supressão de avisos de HTTPS não verificados
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Configuração do logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='market_sniper.log', filemode='w')
logger = logging.getLogger()

chromedriver_autoinstaller.install()
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(options=chrome_options)
buy_count = 0

cache = TTLCache(maxsize=100, ttl=600)

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def progress_bar(urlcount, page, buycount, message, user_balance, api_params=None):
    """Display the progress and decisions with detailed information."""
    print(f"URL: {urlcount} | P.: {page} | Oe: {buycount} | B: {user_balance} | Decision: {message}")



def check_user_balance():
    """Function that is checking user balance"""
    try:
        user_balance = WebDriverWait(driver, 60).until(EC.presence_of_element_located(PageLocators.USER_BALANCE))
        user_balance_edit = (''.join(c for c in user_balance.text if c.isdigit()))
        return user_balance_edit
    except TimeoutException:
        sys.stderr.write("Can't load user balance.")
        driver.quit()


def buy_log(item_name, item_float, item_pattern, item_price, count):
    """Function that will save information about purchase to logfile"""
    logger = logging.getLogger('BUYLOGGER')
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler("purchaseHistory.log", mode='a')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s%(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S%p %Z')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(
        f"Item name: {item_name} , Float: {item_float} , Pattern: {item_pattern} , Price: {item_price}"
    )
    count += 1
    cls()


def check_stickers(json, quantity):
    """Function that will check if skin have stickers"""
    if len(json["iteminfo"]['stickers']) != int(quantity):
        return False
    elif 'stickers' not in json["iteminfo"] or len(json["iteminfo"]['stickers']) == 0:
        return False
    else:
        return True


def buy_skin(buy_button):
    logger.debug("Attempting to buy skin.")
    try:
        driver.execute_script("arguments[0].click();", buy_button)
        check_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located(PageLocators.CHECK_BOX))
        driver.execute_script("arguments[0].click();", check_box)

        buy_button = WebDriverWait(driver, 5).until(EC.presence_of_element_located(PageLocators.BUY_BUTTON))
        driver.execute_script("arguments[0].click();", buy_button)

        close_button = WebDriverWait(driver, 5).until(EC.presence_of_element_located(PageLocators.CLOSE_BUTTON))
        driver.execute_script("arguments[0].click();", close_button)
        
        logger.debug("Purchase successful.")
        return True
    except Exception as e:
        logger.error(f"Failed to purchase skin: {e}")
        return False

def buy_log(item_name, item_float, item_pattern, item_price, count):
    logger.info(f"Item purchased: {item_name}, Float: {item_float}, Pattern: {item_pattern}, Price: {item_price}. Total purchases: {count}")

def find_next_page():
    """Function that will find next page and will go there"""
    try:
        next_page = WebDriverWait(driver, 5).until(EC.visibility_of_element_located(PageLocators.NEXT_PAGE))
        driver.execute_script("arguments[0].click();", next_page)
        time.sleep(2)
        return True
    except TimeoutException:
        sys.stderr.write("Unable to find next page button. Going to next URL...")
        return False
    except NoSuchElementException:
        sys.stderr.write("No next page, going to next URL...")
        return False


def load_purchase_buttons():
    """Function that will load purchase buttons from page"""
    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located(PageLocators.BUY_BUTTON_END))
        inspect_button = driver.find_elements(*PageLocators.INSPECT_BUTTON)
        buy_buttons = driver.find_elements(*PageLocators.BUY_BUTTON_END)
        prices_box = driver.find_elements(*PageLocators.PRICES_BOX)
        return inspect_button, buy_buttons, prices_box
    except TimeoutException:
        logger.error("Cannot find buy buttons on the page.")
        return None, None, None

def check_whole_page(count, url_info):
    buy_count = 0
    skin_count = 0
    items = items_on_page()
    pages = int(page_count())
    max_pages = url_info[count][3]  # Número máximo de páginas a verificar
    page = 0

    while page < pages:
        page += 1
        buttons, buy_now, prices = load_purchase_buttons()
        if not buttons:
            decision_message = "No purchase buttons found. Skipping to next page."
            user_balance = check_user_balance()
            progress_bar(count+1, page, buy_count, decision_message, user_balance)
            continue

        price_text_num = []
        for price in prices:
            try:
                numeric_price = float(''.join(c for c in price.text if c.isdigit() or c == '.'))
                logger.debug(f"Price found: {numeric_price}")
                price_text_num.append(numeric_price / 100)
            except StaleElementReferenceException:
                logger.warning("StaleElementReferenceException encountered. Retrying...")
                # Tentativa de obter o elemento novamente
                buttons, buy_now, prices = load_purchase_buttons()
                try:
                    numeric_price = float(''.join(c for c in prices[buttons.index(price)].text if c.isdigit() or c == '.'))
                    logger.debug(f"Price found on retry: {numeric_price}")
                    price_text_num.append(numeric_price / 100)
                except Exception as e:
                    logger.error(f"Failed to parse price on retry: {e}")
                    price_text_num.append(float('inf'))
            except ValueError:
                logger.error(f"Failed to parse price text into a float: {price.text}")
                price_text_num.append(float('inf'))

        for idx, btn in enumerate(buttons):
            if idx >= len(price_text_num):
                decision_message = f"No price available for button at index {idx}."
                user_balance = check_user_balance()
                progress_bar(count+1, page, buy_count, decision_message, user_balance)
                continue

            if not check_max_price(idx, price_text_num, count, url_info):
                decision_message = f"Price too high: {price_text_num[idx]}"
                user_balance = check_user_balance()
                progress_bar(count+1, page, buy_count, decision_message, user_balance)
                continue

            response = save_json_response(btn)
            if response is None:
                decision_message = "Failed to get JSON response."
                user_balance = check_user_balance()
                progress_bar(count+1, page, buy_count, decision_message, user_balance)
                continue

            item_name, item_float, whole_json = response
            user_bal_num = float(check_user_balance()) / 100

            if user_bal_num < price_text_num[idx]:
                decision_message = f"Not enough balance for buying item {item_name}. Needed: {price_text_num[idx]}, Available: {user_bal_num}"
                user_balance = check_user_balance()
                progress_bar(count+1, page, buy_count, decision_message, user_balance)
                continue

            item_matches, api_params, mismatches = check_item_parameters(item_float, whole_json, count, url_info)
            if not item_matches:
                decision_message = f"Item parameters do not match: {', '.join(mismatches)}"
                user_balance = check_user_balance()
                progress_bar(count+1, page, buy_count, decision_message, user_balance, api_params)
                continue

            if buy_skin(buy_now[idx]):
                buy_count += 1
                decision_message = f"Item purchased: {item_name}"
                user_balance = check_user_balance()
                progress_bar(count+1, page, buy_count, decision_message, user_balance)
                time.sleep(10)  # Delay de 10 segundos após a compra
            else:
                decision_message = f"Failed to buy skin {item_name}"
                user_balance = check_user_balance()
                progress_bar(count+1, page, buy_count, decision_message, user_balance)

        # Verificar se atingiu o número máximo de páginas configurado
        if max_pages is not None and page >= max_pages:
            decision_message = f"Reached max pages ({max_pages}) for current item."
            user_balance = check_user_balance()
            progress_bar(count+1, page, buy_count, decision_message, user_balance)
            break

        # Verificar se atingiu o número total de páginas disponíveis
        if page >= pages:
            break

        # Ir para a próxima página
        if not find_next_page():
            break


def save_json_response(button):
    """Function that will save JSON into variables"""
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            driver.execute_script("arguments[0].click();", button)
            popup = WebDriverWait(driver, 5).until(EC.presence_of_element_located(PageLocators.POPUP))
            href = popup.get_attribute('href')
            request_url = f"http://127.0.0.1:80/?url={href}"
            logger.debug(f"Request URL: {request_url}")

            response = requests.get(request_url)
            logger.debug(f"Response Status Code: {response.status_code}")
            response.raise_for_status()  # Pode lançar um HTTPError se o status não for 200

            json_response = response.json()
            json_response_name = str(json_response["iteminfo"]["full_item_name"])
            json_response_float = float(json_response["iteminfo"]["floatvalue"])
            return json_response_name, json_response_float, json_response
        except TimeoutException:
            logger.error("Waiting too long to open item link.")
            if retry_count == max_retries - 1:
                return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e} for URL: {request_url}")
            if e.response.status_code == 429:
                time.sleep(0.1)  # Espera 0.1 segundos antes de tentar novamente
                retry_count += 1
                continue
            else:
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Exception: {e} for URL: {request_url}")
            return None
        except NoSuchElementException:
            logger.error("Can't open item link")
            return None
        except StaleElementReferenceException:
            logger.warning("StaleElementReferenceException encountered. Retrying...")
            retry_count += 1
            time.sleep(0.1)  # Pequeno delay antes de tentar novamente
    return None

def check_item_parameters(item_float, whole, count, url_info):
    """Function that will compare user set parameters with skin"""
    match = True
    mismatches = []
    api_params = {
        "float": item_float,
        "stickers": len(whole["iteminfo"].get('stickers', []))
    }

    if url_info[count][0] is not None:
        if item_float > float(url_info[count][0]):
            match = False
            mismatches.append("float")

    if url_info[count][1] is not None:
        if not check_stickers(whole, url_info[count][1]):
            match = False
            mismatches.append("stickers")
            
    return match, api_params, mismatches


def check_max_price(order, price, count, url_info):
    if url_info[count][3] is not None:
        try:
            max_price = float(url_info[count][3])
            current_price = price[order]
            logger.debug(f"Max price: {max_price}, Current price: {current_price}")
            if max_price <= current_price:
                return False
        except IndexError:
            logger.error(f"Price index {order} is out of range.")
            return True  # Considerando verdadeiro se o índice estiver fora do alcance para evitar falhas
    return True


def page_count():
    try:
        WebDriverWait(driver, 2).until(EC.presence_of_element_located(PageLocators.LAST_PAGE))
        last_page = driver.find_elements(*PageLocators.LAST_PAGE)
        return last_page[-1].text
    except TimeoutException:
        return 1

def actual_page_number():
    try:
        actual = WebDriverWait(driver, 2).until(ec.presence_of_element_located(PageLocators.PAGE_NUMBER)).text
        return int(actual)
    except TimeoutException:
        return 1

@cached(cache)
def fetch_json_response(url):
    try:
        response = requests.get(url, verify=False)  # Desabilitando a verificação SSL
        response.raise_for_status()  # Levanta um erro para respostas de falha (4xx, 5xx etc.)
        data = response.json()  # Tenta analisar a resposta como JSON
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
    except ValueError as e:
        logger.error(f"Failed to parse JSON: {e}")
    return None

# Exemplo de uso
url = "https://api.exemplo.com/dados"
json_data = fetch_json_response(url)
if json_data:
    print(json_data)

def items_on_page():
    return int(page_count())*10

@lru_cache(maxsize=32)
def get_page_elements():
    return driver.find_elements(By.CSS_SELECTOR, "your_css_selector")

# Cache de respostas HTTP com TTL de 10 minutos
cache = TTLCache(maxsize=100, ttl=600)

@cached(cache)
def fetch_json_response(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Levanta um erro para respostas de falha (4xx, 5xx etc.)
        data = response.json()  # Tenta analisar a resposta como JSON
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
    except ValueError as e:
        logger.error(f"Failed to parse JSON: {e}")
    return None

# Use get_page_elements() wherever necessary to reuse cached elements
