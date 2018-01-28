from os import environ
import requests
from datetime import datetime
import hmac
from base64 import b64encode
from hashlib import sha256
from xmltodict import parse
from urllib.parse import quote, urlencode
from urllib.request import urlretrieve
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from pyvirtualdisplay import Display
from sqlalchemy.exc import SQLAlchemyError
from importlib import reload
import sys

from os.path import join, dirname
from dotenv import load_dotenv
from os import environ, remove

import json

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

from db import session
from db.models import Product, ProductPriceHistory

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), sha256).digest()

def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'aws4_request')
    return kSigning

def amazon_top_sellers_page(page, search_index, browse_node):
    payload = {
        'AWSAccessKeyId': environ['AWSAccessKeyId'],
        'AssociateTag': environ['AssociateTag'],
        'Service': 'AWSECommericeService',
        'Operation': 'ItemSearch',
        'SearchIndex': search_index,
        'BrowseNode': browse_node,
        'ResponseGroup': 'Small,ItemAttributes',
        'ItemPage': page,
        'Version': '2013-08-01',
        'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    secret = environ['AWSSecretKey']
    keys = sorted(payload.keys())
    args = '&'.join('%s=%s' % (
        key, quote(str(payload[key]).encode('utf-8'))) for key in keys)
    msg = ('GET\n'
        'webservices.amazon.com\n'
        '/onca/xml\n' + args)
    hashed = hmac.new(secret.encode(), msg.encode(), sha256).digest()
    payload['Signature'] = b64encode(hashed)
    params = urlencode(sorted(payload.items()))
    url = 'http://webservices.amazon.com/onca/xml?{}'.format(params)
    res = requests.get(url)
    res_json = parse(res.text, xml_attribs=True)
    best_seller_products = []
    for item in res_json['ItemSearchResponse']['Items']['Item']:
        try:
            asin = item['ASIN']
            name = item['ItemAttributes']['Title']
            upc = item['ItemAttributes']['UPC']
            best_seller_products.append({'asin': asin, 'name': name, 'upc': upc})
        except:
            pass
    return best_seller_products, res_json

def amazon_top_sellers_100(search_index, browse_node):
    products = []
    for i in range(1, 11):
        products += amazon_top_sellers_page(i, search_index, browse_node)[0]
    return products
import json

def download_file(url):
    res = requests.get(url, stream=TActionsrue)
    if res.status_code == 200:
        with open('./test.png', 'wb') as f:
            for chunk in f:
                f.write(chunk)
    else:
        raise Exception('Failed downloading file')

def upload_to_db(upc, name):
    price_history = []
    with open('chart.csv') as csv:
        curr_price = -1
        for line in csv:
            cols = line.split(',')
            if abs(float(cols[1]) - curr_price) > 0.15:
                curr_price = float(cols[1])
                date = datetime.strptime(cols[0], "%Y-%m-%d %H:%M:%S")
                price_history.append({'date': cols[0], 'price': curr_price})
    product = Product(upc=upc, name=name)
    try:
        session.add(product)
        session.commit()
    except SQLAlchemyError as e:
        print(e)

    for point in price_history:
        pph = ProductPriceHistory(item_upc=upc, price=point['price'], date=point['date'])
        session.add(pph)
    session.commit()
import time
def scrape_camel_chart(driver, name, asin, quit=False):
    try:
        driver.get("https://camelcamelcamel.com/{}/product/{}".format(name, asin))
    except Exception as e:
        print(e)
        return
    try:
        elem = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="summary_chart"]')))
        src = elem.get_attribute('src')
        print(src)
        with open('chart.png', 'wb') as img:
            img.write(requests.get(src, verify=False).content)
        parse_camel_chart()
    finally:
        if quit:
            driver.quit()


def clean_up():
    files = ['bgr.png', 'black.png', 'detected bgr.jpg', 'chart.csv', 'chart.png',
        'error1.jpg', 'error2.jpg', 'error3.jpg', 'ocr.jpg']
    for f in files:
        try:
            remove(f)
        except Exception as e:
            print(e)


top = amazon_top_sellers_100('Electronics', 172282)

if '-v' in sys.argv:
    display = Display(visible=0, size=(800, 600))
    display.start()
driver = webdriver.Firefox()

loaded = False

for product in top:
    try:
        global loaded
        scrape_camel_chart(driver, product['name'], product['asin'], False)
        if loaded:
            reload(read_camel)
        else:
            from . import read_camel
            loaded = True
    except Exception as e:
        print(e)
        continue
    upload_to_db(product['upc'], product['name'])

clean_up()
driver.quit()
