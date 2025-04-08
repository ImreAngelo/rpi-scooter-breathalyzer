import json
import paho.mqtt.client as mqtt

from stmpy import Machine, Driver
from mqtt_client import MQTT_Client
from hardware import Hardware

##
class Scooter:
	def __init__(self, mqtt_client, id, pos = [50, 50]):
		self.driver = None
		self.id = id
		self.pos = pos

		# TODO: Make static
		self.hardware = Hardware(self.get_driver())

		# Consider making this null to couple at same time as stm_driver
		self.mqtt_client = mqtt_client
		self.mqtt_client.stm_driver = self.get_driver() # TODO: Clean up circular dependencies

	def on_enter_available(self):
		self.mqtt_client.client.subscribe("available")
		self.mqtt_client.client.publish("debug", f"[Scooter {self.id}] is now available")

	def on_exit_available(self):
		self.mqtt_client.client.unsubscribe("available")
		self.mqtt_client.client.publish("debug", f"[Scooter {self.id}] is no longer available")

	def on_enter_reserved(self, user_id):
		self.mqtt_client.client.publish(f"unlock/{self.id}/res", json.dumps({
			"user_id": user_id,
			"status": 0 # Reserved (ACK)
		}))
		self.log(f"Reserving for {user_id}")
		bac_level = self.hardware.breathalayzer()
		print("BAC Reading: ", bac_level)
		
	def on_exit_reserved(self):
		# debug - Dette skal komme fra breathalyzer
		# self.mqtt_client.client.unsubscribe("BAC_fail")
		# self.mqtt_client.client.unsubscribe("BAC_success")
		pass

	def on_enter_riding(self):
		self.hardware.unlock() # TODO: Fix name/role

	def on_exit_riding(self):
		self.hardware.lock()
		self.mqtt_client.client.publish(f"lock/{self.id}/res", json.dumps({"status":"gucci"}))

	def geo_check_distance(self, user_id, loc):
		x, y = loc[0], loc[1]
		self.log(f"Checking distance: {self.pos} to [{x}, {y}]")

		maxDistance = 75
		distanceSqrMag = (self.pos[0] - x)**2 + (self.pos[1] - y)**2
		self.log(f"Distance is {distanceSqrMag**(1/2)}")

		if(distanceSqrMag < maxDistance**2):
			self.log("Scooter is close enough!")
			payload = json.dumps({ "s_id":self.id, "loc":self.pos })
			self.mqtt_client.client.publish(f"available/{user_id}/res", payload)
		else:
			self.log("Scooter is too far away :(")

		return "available"

	def log(self, msg):
		print(f"[Scooter {self.id}] {msg}")

	def send_bac(self, success):
		self.log(f"BAC Status: {success}")
		self.mqtt_client.client.publish(f"unlock/{self.id}/res", json.dumps({
			# 1 = success, 2 = fail
			"status": 1 if success else 2
		}))

	#######
	# API #
	#######
	def get_driver(self):
		if self.driver:
			return self.driver

		transitions = [
			{'source':'initial', 'target':'available'},
			{'trigger':'unlock', 'source':'available', 'target':'reserved', 'effect':'on_enter_reserved(*)'},
			{'trigger':'BAC_fail', 'source':'reserved', 'target':'available', 'effect':'send_bac(False)'},
			{'trigger':'BAC_success', 'source':'reserved', 'target':'riding', 'effect':'send_bac(True)'},
			{'trigger':'lock', 'source':'riding', 'target':'available'},
		]

		states = [
			{'name':'available', 'entry':'on_enter_available', 'exit':'on_exit_available', 'available':'geo_check_distance(*)'},
			{'name':'riding', 'entry':'on_enter_riding', 'exit':'on_exit_riding'},
		]

		stm = Machine(transitions=transitions, states=states, obj=self, name="scooter")

		driver = Driver()
		driver.add_machine(stm)
		self.driver = driver

		return self.driver