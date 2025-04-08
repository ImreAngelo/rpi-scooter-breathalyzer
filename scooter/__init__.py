import os
from dotenv import load_dotenv
from mqtt_client import MQTT_Client
from scooter import Scooter

# 
load_dotenv()

broker = os.getenv('MQTT_BROKER')
port = int(os.getenv('MQTT_PORT'))
username = os.getenv('MQTT_USER')
password = os.getenv('MQTT_PASS')
scoot_id = os.getenv('SCOOTER_ID')

# Set up MQTT client
mqtt = MQTT_Client(scoot_id, username, password)

# Set up scooter
scooter = Scooter(mqtt, scoot_id)
# mqtt.stm_driver = scooter.get_driver() # TODO: Clean up dependencies

# Execute
mqtt.stm_driver.start()
mqtt.start(broker, port)
mqtt.stm_driver.stop()