from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict
import time

from stmpy import Machine, Driver
from app import MQTT_Client, App

import logging
import sys

logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.DEBUG)

# App
app = FastAPI()

# Logging
logger = logging.getLogger(__name__)

#### handler ####
console_handler = logging.StreamHandler()
# we need addHandler to combine handler with logger
logger.addHandler(console_handler)

#### formatter ####
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
 )
# we need setFormatter to combine handler with handler
console_handler.setFormatter(formatter)


# Disable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)



# TODO: Move

knjgds = None
driver = None
broker, port = "localhost", 8883
# broker, port = "602b94dba5e94866b68426d4ae3e72fd.s1.eu.hivemq.cloud", 8883
username, password = "scooter_app", "Powerpuffs100"


############# API
@app.post("/available")
async def get_available_scooters(data: Dict):
    global knjgds, driver

    # logger.debug(data)

    if(knjgds):
        return knjgds.scooters
    
    ##### 
    id = data["user_id"]
    loc = data["location"]

    myclient = MQTT_Client(id, username, password)
    knjgds = App(myclient, id, loc)

    # Scooter state machine
    transitions = [
        {'source':'initial', 'target':'list scooters', 'effect':'log("A")'},
        {'trigger':'choose_scooter', 'source':'list scooters', 'target':'reserving', 'effect':'save_scooter_id(*)'},
        {'trigger':'unlock', 'source':'reserving', 'target':'breathalyzer', 'effect':'log("Confirmed scooter reservation")'},
        {'trigger':'unlock_ack', 'source':'breathalyzer', 'target':'riding', 'effect':'log("Unlocked scooter!")'},
        {'trigger':'unlock_fail', 'source':'breathalyzer', 'target':'list scooters', 'effect':'log("Failed bac test!")'},
        {'trigger':'lock_btn', 'source':'riding', 'target':'locking', 'effect':'log("Locking scooter")'},
        {'trigger':'lock', 'source':'locking', 'target':'list scooters', 'effect':'log("Locked scooter")'}
    ]

    states = [
        # Alt. 3 - Perfect
        {'name':'list scooters', 'entry':'on_enter_list_scooters', 'exit':'on_exit_list_scooter', 'available':'add_scooter(*)'},
        {'name':'reserving', 'entry':'on_enter_reserving'},
        {'name':'locking', 'entry':'on_enter_locking', 'exit':'on_exit_locking'},
        {'name':'riding', 'entry':'on_enter_riding'},
    ]

    app_stm = Machine(transitions=transitions, states=states, obj=knjgds, name="app")
    knjgds.stm = app_stm

    driver = Driver()
    driver.add_machine(app_stm)

    # MQTT Client coupling
    myclient.stm_driver = driver

    # Start
    driver.start()
    myclient.start(broker, port)
    # driver.stop()

    time.sleep(2)
        
    hasDriver = True
    return knjgds.scooters

    
@app.post("/choose_scooter")
async def choose_scooter(data: Dict):
    driver.send("choose_scooter", "app", kwargs=data)
    return {"ACK":"ACK"}

    
@app.get("/bac")
async def choose_scooter():
    if(knjgds.checksum == 10):
        return {"status": 1}
    if(knjgds.last_test == 0):
        return {"status": 0}
    return {"status": -1}


@app.get("/lock")
async def choose_scooter():
    driver.send("lock_btn", "app")
    return {"ACK": "ok"}