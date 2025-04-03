import json
import paho.mqtt.client as mqtt

from stmpy import Machine, Driver

##
class MQTT_Client:
	'''Wrapper for MQTT'''

	def __init__(self, id, username, password):
		self.count = 0
		self.id = id

		self.username = username
		self.password = password

		self.client = mqtt.Client()
		self.client.on_connect = self.on_connect
		self.client.on_message = self.on_message

		self.client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
		self.client.username_pw_set(username, password)

	#############
	# Callbacks #
	#############
	def on_connect(self, client, userdata, flags, rc):
		print("on_connect(): {}".format(mqtt.connack_string(rc)))
		client.subscribe(f"HDSAKNJCA/unlock/{self.id}")
		client.subscribe(f"HDSAKNJCA/lock/{self.id}")
		client.subscribe("HDSAKNJCA/available")
		client.publish("HDSAKNJCA/debug", f"Connected with ID {self.id}")

	def on_message(self, client, userdata, msg):
		print("on_message(): topic: {}".format(msg.topic))
		print(msg.topic.split("/"))

		msg_type = msg.topic.split("/")[1]
		
		kwargs = {}
		if(msg_type == "available"):
			payload = json.loads(msg.payload.decode("utf-8"))
			try:
				kwargs = { 
					'user_id':payload["user_id"],
					'loc':payload["loc"]
				}
			except:
				print("Noe er feil") 

		if(msg_type == "unlock"):
			print("VI ER HER")
			payload = msg.payload.decode("utf-8")
			print("Payload A: ", payload)
			payload = json.loads(payload)
			print("Payload B: ", payload)
			kwargs = {
				'user_id':payload["user_id"]
			}

		self.stm_driver.send(msg_type, "scooter", kwargs=kwargs)

	def start(self, broker, port):
		print("Connecting to {}:{}".format(broker, port))
		self.client.connect(broker, port)

		try:
			self.client.loop_forever()
		except KeyboardInterrupt:
			print("Interrupted")
			self.client.disconnect()


##
class Scooter:
	def __init__(self, mqtt_client, id):
		self.id = id
		self.pos = [100, 200]
		# Consider making this null to couple at same time as stm_driver
		self.mqtt_client = mqtt_client 

	def on_enter_available(self):
		self.mqtt_client.client.subscribe("HDSAKNJCA/available")
		self.mqtt_client.client.publish("HDSAKNJCA/debug", f"[Scooter {self.id}] is now available")

	def on_exit_available(self):
		self.mqtt_client.client.unsubscribe("HDSAKNJCA/available")
		self.mqtt_client.client.publish("HDSAKNJCA/debug", f"[Scooter {self.id}] is no longer available")

	def on_enter_reserved(self, user_id):
		self.mqtt_client.client.publish(f"HDSAKNJCA/unlock/{self.id}/res", json.dumps({
			"user_id": user_id,
			"status": 0 # Reserved (ACK)
		}))
		self.log(f"Reserving for {user_id}")
		# bac_level = start_breathalyzer()
		
		# debug - Dette skal komme fra breathalyzer
		self.mqtt_client.client.subscribe("HDSAKNJCA/BAC_fail")
		self.mqtt_client.client.subscribe("HDSAKNJCA/BAC_success")

		
	def on_exit_reserved(self):
		# debug - Dette skal komme fra breathalyzer
		self.mqtt_client.client.unsubscribe("HDSAKNJCA/BAC_fail")
		self.mqtt_client.client.unsubscribe("HDSAKNJCA/BAC_success")

	def on_enter_riding(self):
		# unlock()
		pass

	def on_exit_riding(self):
		# lock()
		self.mqtt_client.client.publish(f"HDSAKNJCA/lock/{self.id}/res", json.dumps({"status":"gucci"}))

	def geo_check_distance(self, user_id, loc):
		x, y = loc[0], loc[1]
		self.log(f"Checking distance: {self.pos} to [{x}, {y}]")

		maxDistance = 75
		distanceSqrMag = (self.pos[0] - x)**2 + (self.pos[1] - y)**2
		self.log(f"Distance is {distanceSqrMag**(1/2)}")

		if(distanceSqrMag < maxDistance**2):
			self.log("Scooter is close enough!")
			payload = json.dumps({ "s_id":self.id, "loc":self.pos })
			self.mqtt_client.client.publish(f"HDSAKNJCA/available/{user_id}/res", payload)
		else:
			self.log("Scooter is too far away :(")

		return "available"

	def log(self, msg):
		print(f"[Scooter {self.id}] {msg}")

	def send_bac(self, success):
		self.log(f"BAC Status: {success}")
		self.mqtt_client.client.publish(f"HDSAKNJCA/unlock/{self.id}/res", json.dumps({
			# 1 = success, 2 = fail
			"status": 1 if success else 2
		}))


##### 
# broker, port = "test.mosquitto.org", 1883
broker, port = "602b94dba5e94866b68426d4ae3e72fd.s1.eu.hivemq.cloud", 8883
username, password = "Scooter", "Powerpuffs100"

id = 8080
myclient = MQTT_Client(id, username, password)
scooter = Scooter(myclient, id)

# Scooter state machine
transitions = [
	{'source':'initial', 'target':'available'},
	{'trigger':'unlock', 'source':'available', 'target':'reserved', 'effect':'on_enter_reserved(*)'},
	{'trigger':'BAC_fail', 'source':'reserved', 'target':'available', 'effect':'send_bac(False)'},
	{'trigger':'BAC_success', 'source':'reserved', 'target':'riding', 'effect':'send_bac(True)'},
	{'trigger':'lock', 'source':'riding', 'target':'available'},

	# Alt. 1 - Original state machine
	# {'trigger':'available', 'source':'available', 'target':'geo', 'effect':'log("Checking distance")'},
	# {'trigger':'success', 'source':'geo', 'target':'available', 'effect':'log("Too far")'},
	# {'trigger':'failure', 'source':'geo', 'target':'available', 'effect':'log("In range")'},

	# Alt. 2 - Still triggers onEnter/onExit
	# {'trigger':'available', 'source':'available', 'target':'available', 'effect':'log("Checking distance")', 'function':scooter.geo_check_distance },
]

states = [
	# Alt. 3 - Perfect
	{'name':'available', 'entry':'on_enter_available', 'exit':'on_exit_available', 'available':'geo_check_distance(*)'},
	# {'name':'reserved', 'entry':''},
	{'name':'riding', 'entry':'on_enter_riding', 'exit':'on_exit_riding'},
]

scooter_stm = Machine(transitions=transitions, states=states, obj=scooter, name="scooter")
scooter.stm = scooter_stm

driver = Driver()
driver.add_machine(scooter_stm)

# MQTT Client coupling
myclient.stm_driver = driver

# Start
driver.start()
myclient.start(broker, port)
driver.stop()