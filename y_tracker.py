#Libraries
import pandas as pd
from datetime import datetime as dt
from time import sleep
from selenium.webdriver.common.by import By
import re
#Variables
from settings.config import gsheet, ya_pass, ya_login, yatax_web, ya_log_url, executable
#Functions
from utils.helpers import read_sheet, get_y_tariffs, get_eta, get_travel_time, get_ytr_components, ya_acc
from utils.helpers import init_driver, input_route, reframe
#all main code
#step0: read data from gsheet
df_routes = pd.DataFrame(read_sheet(sheet_url = gsheet['url'], sheet_name = 'routes').get_all_records())
#step1: collect data on pricing components
tariffs = get_y_tariffs('https://taxi.yandex.com/en_am/minsk/tariff/econom')
city_data = {t: get_ytr_components(city = 'minsk', category = t) for t in tariffs}
run_status = 'pricing data collected with BS4'
ts = str(dt.now())
#step2: selenium bot rides pricing data collectiong
driver = init_driver()
run_status = 'driver initiated'
ts = str(dt.now())
print(run_status, ts)
driver.get(ya_log_url)
ya_acc(driver, ya_login, ya_pass)
sleep(2)
driver.get(yatax_web)
driver.implicitly_wait(10)
run_status = 'logged in'
ts = str(dt.now())
print(run_status, ts)
#step3: collect data and store in a dictionary
intel = pd.DataFrame()
for i in range(len(df_routes)):
    route_id = df_routes.loc[i, 'route_id']
    point_a = str(df_routes.loc[i, 'point_a'])
    point_b = str(df_routes.loc[i, 'point_b'])
    trip_km = df_routes.loc[i, 'trip_km']
    input_route(driver = driver, a = point_a, b = point_b, sleep_time = 4)
    #Prices Extraction
    buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-testid *= 'TariffButton']")
    sleep(2)
    for bt_num, bt in enumerate(buttons):
        if not re.search('active',bt.get_attribute('data-testid')): bt.click()
        html = bt.get_attribute('innerHTML')
        t_name = re.findall('img alt="([^"]+)"', html)[0] # tarriff name
        if t_name in ['Эконом']: continue # optional, add t_names if needed
        price_actual = re.findall('>([^<]+)</span></span></span>', html)[0]
        price_actual = float(price_actual[:price_actual.find("р")-1].replace(",",".")) #price
        sleep(2)
        eta = get_eta(driver) # eta
        trip_time = get_travel_time(driver = driver) #travel time
        intel = intel.append({
        'route_id': route_id,
        'point_a': point_a,
        'point_b': point_b,
        'price_actual': price_actual,
        'eta': eta,
        'trip_time': trip_time,
        'trip_km': trip_km,
        't_name': t_name,
        'run_status': run_status,
        'ts': ts,
        'error': ''}, ignore_index = True)
    run_status = f'Collected data for route_id {route_id}'
    if i == len(df_routes) - 1: run_status = 'All Data Collected'
    ts = str(dt.now())
    print(run_status, ts)
#Step 4: Connect to Gsheet and paste extracted data there
outsheet = read_sheet(sheet_url = gsheet['url'], sheet_name = 'minsk_output')
out_data = pd.DataFrame(outsheet.get_all_records())
intel = reframe(example_frame = out_data, dataframe = intel)
outsheet.append_rows(intel.values.tolist())
print('Run Finished', str(dt.now()))