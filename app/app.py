import json
import paho.mqtt.client as mqtt

from stmpy import Machine, Driver
from threading import Thread

##
class MQTT_Client:
	def __init__(self, id, username, password):
		self.count = 0
		self.id = id
		
		self.username = username
		self.password = password

		self.client = mqtt.Client()
		self.client.on_connect = self.on_connect
		self.client.on_message = self.on_message

		# self.client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
		self.client.username_pw_set(username, password)

	def on_connect(self, client, userdata, flags, rc):
		print("on_connect(): {}".format(mqtt.connack_string(rc)))
		client.subscribe("choose_scooter")
		client.subscribe("lock_btn")
		client.publish("debug/app", f"Connected with ID {self.id}")

	def on_message(self, client, userdata, msg):
		print("on_message(): topic: {}".format(msg.topic))
		print(msg.topic.split("/"))

		msg_type = msg.topic.split("/")[0]
		payload = json.loads(msg.payload.decode("utf-8"))
		
		kwargs = {}
		if(msg_type == "available"):
			print("payload: ", payload)
			kwargs = { 
				's_id':payload["s_id"],
				'loc':payload["loc"]
			}

		# Debug -> Move to app frontend
		if(msg_type == "choose_scooter"):
			print("Choosing scooter: ", payload)
			kwargs = { 
				's_id':payload["s_id"]
			}

		if(msg_type == "unlock"):
			status = payload["status"]
			if(status == 1):
				# success
				msg_type = "unlock_ack"
			if(status == 2):
				# fail
				msg_type = "unlock_fail"
			print("Unlocking: ", status)

		self.stm_driver.send(msg_type, "app", kwargs=kwargs)

	def start(self, broker, port):
		print("Connecting to {}:{}".format(broker, port))
		self.client.connect(broker, port)

		try:
			# line below should not have the () after the function!
			thread = Thread(target=self.client.loop_forever)
			thread.start()
		except KeyboardInterrupt:
			print("Interrupted")
			self.client.disconnect()

		# try:
		# 	self.client.loop_forever()
		# except KeyboardInterrupt:
		# 	print("Interrupted")
		# 	self.client.disconnect()


##
class App:
	def __init__(self, mqtt_client, id, pos):
		self.id = id
		self.pos = pos
		# Consider making this null to couple at same time as stm_driver
		self.mqtt_client = mqtt_client
		self.scooters = []
		self.last_test = 0
		self.checksum = 0

	################
	# MQTT Wrapper #
	################
	def publish(self, topic, payload : dict):
		self.mqtt_client.client.publish(topic, json.dumps(payload))

	def subscribe(self, topic):
		self.mqtt_client.client.subscribe(topic)
		
	def unsubscribe(self, topic):
		self.mqtt_client.client.unsubscribe(topic)

	###########
	# Helpers #
	###########
	def log(self, msg):
		'''Print debug messages'''
		print(f"[App {self.id}] {msg}")
		
	##########
	# States #
	##########
	def on_enter_list_scooters(self):
		# TODO: Clean up
		while not self.mqtt_client.client.is_connected():
			self.mqtt_client.client.loop()

		self.subscribe(f"available/{self.id}/res")
		self.publish("available", {
			"user_id": self.id,
			"loc": self.pos # TODO: custom
		})

		self.log(f"Last test from {self.last_test}")
		self.last_test = 0
		self.checksum = 0
		self.log(f"Last test to {self.last_test}")

	def on_exit_list_scooter(self):
		self.unsubscribe(f"available/{self.id}/res")

	def add_scooter(self, s_id, loc):
		# add_scooter(scooter_id, loc) to frontend
		self.scooters.append({"s_id": s_id, "loc": loc})
		self.log(f"ID: {s_id}, loc: {loc}")

	def on_enter_reserving(self):
		self.log(f"Reserving: {self.active_scooter}")
		
		self.subscribe(f"unlock/{self.active_scooter}/res")
		self.publish(f"unlock/{self.active_scooter}", {
			"user_id": self.id
		})
		
		self.log(f"Last test from {self.last_test}")
		self.last_test = -1
		self.log(f"Last test to {self.last_test}")

	def on_enter_breathalyzer(self):
		self.unsubscribe(f"unlock/{self.active_scooter}")

	def on_enter_locking(self):
		self.subscribe(f"lock/{self.active_scooter}/res")
		self.publish(f"lock/{self.active_scooter}", {})

	def on_exit_locking(self):
		self.unsubscribe(f"lock/{self.active_scooter}/res")

	def save_scooter_id(self, s_id):
		self.log(f"Saving ID: {s_id}")
		self.active_scooter = s_id

	def on_enter_riding(self):
		self.log(f"PROLBEM Last test from {self.checksum}")
		self.checksum = 10
		self.log(f"VERY IMPORTANT HERE {self.last_test} / {self.checksum}")