#Libraries
import random
from bs4 import BeautifulSoup
import re
import requests
from datetime import datetime as dt
import gspread
from oauth2client.service_account import ServiceAccountCredentials as SAC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager #needed to automatically download the right chromedriver, can be removed
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from time import sleep
from random import randint
from selenium.webdriver import Chrome
#Variables from settings
from settings.config import user_agents, js_dump, scope

def assign_header(user_agents):
    return {'User-Agent': random.choice(user_agents)}

def get_y_tariffs(url):
    y_data = BeautifulSoup(requests.get(url, headers = assign_header(user_agents)).text, 'html.parser')
    tariff_names = [tar['href'].split('/')[-1] for tar in y_data.find_all('a', {'href': re.compile('minsk\/tariff')})]
    return tariff_names

def get_ytr_components(city, category):
    data = BeautifulSoup(
    requests.get(
        f"https://taxi.yandex.com/en_am/{city}/tariff/{category}",
        headers = assign_header(user_agents)).text, 'html.parser')
    pricing = data.find('div', {'class': 'MainPrices__description'}).find_all('span', {'class': 'PriceValue__price'})
    base = float(re.findall('([0-9\.]+)', pricing[0].decode_contents())[0])
    per_minute = float(re.findall('([0-9\.]+)', pricing[2].decode_contents())[0])
    per_km = float(re.findall('([0-9\.]+)', pricing[3].decode_contents())[0])
    return {'base': base, 'per_minute': per_minute, 'per_km': per_km, 'tstamp': str(dt.now())}
#Functions: read / write to Gdrive
def read_sheet(sheet_url, sheet_name):
    credentials = SAC.from_json_keyfile_dict(js_dump, scope)
    client = gspread.authorize(credentials)
    spreadshet = client.open_by_url(sheet_url)
    return spreadshet.worksheet(sheet_name)
#Functions: selenium bot
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    preferences = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.geolocation" :2
    }
    options.add_experimental_option("prefs", preferences) #needed to hide geolocation & ignore save password popup
    #driver = webdriver.Chrome(service = Service(executable), options = options)
    driver = Chrome(service=Service(ChromeDriverManager().install()), options = options)
    return driver
def ya_acc(driver,login, password):
    for num, log_key in enumerate(login):
        if num % 2 == 0: sleep(randint(1,10) / 5)
        driver.find_element(By.NAME, "login").send_keys(log_key)
    driver.find_element(By.ID, "passp:sign-in").click()
    sleep(1)
    for num, pass_key in enumerate(password):
        if num % 2 == 0: sleep(randint(1,10) / 5)
        driver.find_element(By.NAME, "passwd").send_keys(pass_key)
    sleep(1)
    driver.find_element(By.ID, "passp:sign-in").click()
def input_route(driver, a, b, sleep_time):
    inputs = driver.find_elements(By.NAME, 'search')
    sleep(sleep_time)
    for inum, inp in enumerate(inputs):
        if inum > 1: break
        curr_val = inp.get_attribute('innerHTML')
        print(len(curr_val))
        if len(curr_val) > 0: [inp.send_keys(Keys.BACKSPACE) for i in range(len(curr_val))]
        if inum == 0: inp.send_keys(a)
        else: inp.send_keys(b)
        sleep(sleep_time)
        driver.find_element(By.CSS_SELECTOR, "div[role = 'listbox']").find_elements(By.TAG_NAME,"div")[0].click()
def get_travel_time(driver):
    data = driver.find_elements(By.NAME, 'search')[1].get_attribute('placeholder')
    return float(re.findall('[0-9]+', data)[0])
def get_eta(driver):
    html = BeautifulSoup(driver.page_source, 'html.parser')
    try:
        return float(html.find('ymaps', {'class': re.compile('ymaps.+marker')}).find_all('span')[0].decode_contents())
    except IndexError:
        return "No Dispatch"
def reframe(example_frame, dataframe):
    cols = [col for col in example_frame.columns if col in dataframe.columns]
    dataframe = dataframe[cols]
    dataframe = dataframe.reset_index(drop = True)
    return dataframe