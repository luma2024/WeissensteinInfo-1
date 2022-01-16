# Abruf von Webdaten rund um den Weissenstein. Webscraping abgekupfert von StScraper.

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime
import sys
import paho.mqtt.client as mqtt

import secrets

mqtt_on = True


user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
             "Chrome/96.0.4664.45 Safari/537.36"

options = webdriver.ChromeOptions()
options.headless = True
options.add_argument(f'user-agent={user_agent}')
options.add_argument("--window-size=1024,768")
options.add_argument('--ignore-certificate-errors')
options.add_argument('--allow-running-insecure-content')
options.add_argument("--disable-extensions")
options.add_argument("--proxy-server='direct://'")
options.add_argument("--proxy-bypass-list=*")
options.add_argument("--start-maximized")
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')

abrufversuche = 0
for abrufversuche in range(1):  # Anzahl Versuche im Fehlerfall

    time.sleep(abrufversuche * 30)
    abrufversuche += 1

    try:
        driver = webdriver.Chrome(options=options)

        # The callback for when the client receives a CONNACK response from the server.
        def on_connect(client, userdata, flags, rc):
            print("MQQT connected with result code " + str(rc))

            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            client.subscribe("weissenstein/control/#")

        control = {
            'onoff': '',
            'delay': 3600  # Sekunden (Intervall Datenabruf)
        }

        if mqtt_on:
            # The callback for when a PUBLISH message is received from the server.
            def on_message(client, userdata, msg):
                received = str(msg.payload.decode("utf-8"))
                if msg.topic == "weissenstein/control/onoff":
                     control['onoff'] = received
                if msg.topic == "weissenstein/control/delay":
                     control['delay'] = received
                print(msg.topic + " " + received)

            client = mqtt.Client()
            client.on_connect = on_connect
            client.on_message = on_message
            client.username_pw_set(secrets.mqtt_user, password=secrets.mqtt_pwd)

            client.connect(secrets.mqtt_host, secrets.mqtt_port, 60)

            # Blocking call that processes network traffic, dispatches callbacks and
            # handles reconnecting.
            # Other loop*() functions are available that give a threaded interface and a
            # manual interface.
            client.loop_start()

        data = {}

        x = 0
        while x in range(1):  # Endlosschleife mit "while True" oder begrenzt mit "while x in range(n)>" oder gesteuert mit "while control['onoff'] != "stop""
            if x > 0:
                time.sleep(int(control['delay']))
            else:
                client.publish('weissenstein/status', payload='Abfrage gestartet')
            x += 1

            # Seilbahn Weissenstein
            driver.get('https://seilbahn-weissenstein.ch/')
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.header-navigation'))
            )
            time.sleep(0)

            value = driver.find_element(By.CSS_SELECTOR, 'div.centered-wrapper-inner div p')

            # print(value.get_attribute('innerHTML'))
            print(value.text)
            client.publish('weissenstein/seilbahn', payload=str(value.text))

            # Hinterweissenstein Strassensperre
            driver.get('https://www.hinterweissenstein.ch/')

            value = driver.find_element(By.CSS_SELECTOR, '#text-4')

            # print(value.get_attribute('innerHTML'))
            print(value.text)
            client.publish('weissenstein/strasse', payload=str(value.text))

            data["Timestamp"] = datetime.datetime.now()
            data["Date"] = datetime.datetime.now().strftime("%d.%m.%Y")
            data["Time"] = datetime.datetime.now().strftime("%H:%M:%S")

            # functions.printdata(data)
            # functions.writefile(data)

            abrufversuche = 0  # zurücksetzen, wenn alles ordentlich läuft

        break  # Damit nach ordentlichem Verlassen der inneren Schleife das Programm beendet wird

    except:
        print(f'Fehler beim Abruf der Weissenstein-Informationen (Versuch {abrufversuche}): ', sys.exc_info())
        client.publish('weissenstein/status', payload=f'Fehler beim Abruf der Weissenstein-Infos (Versuch {abrufversuche}): {sys.exc_info()}')

    driver.close()
    client.loop_stop()

print('Abruf Weisstenstein-Info wurde beendet.')
