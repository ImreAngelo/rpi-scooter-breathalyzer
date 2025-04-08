from sense_hat import SenseHat
import time

# CONSTANT VALUES #
r = [255,0,0]
g = [0,255,0]
b = [0,0,0]

red_cross = [
	r, b, b, b, b, b, b, r,
	b, r, b, b, b, b, r, b,
	b, b, r, b, b, r, b, b,
	b, b, b, r, r, b, b, b,
	b, b, b, r, r, b, b, b,
	b, b, r, b, b, r, b, b,
	b, r, b, b, b, b, r, b,
	r, b, b, b, b, b, b, r
]

green_check = [
	b, b, b, b, b, b, b, b,
	b, b, b, b, b, b, b, b,
	b, b, b, b, b, b, b, g,
	b, b, b, b, b, b, g, b,
	b, g, b, b, b, g, b, b,
	b, b, g, b, g, b, b, b,
	b, b, b, g, b, b, b, b,
	b, b, b, b, b, b, b, b
]

class Hardware:
	'''This class contains all the hardware interactions with the Scooter'''

	def __init__(self, driver):
		self.sense = SenseHat()
		self.driver = driver

	def trigger(self, signal):
		self.driver.send(signal, "scooter")

	def unlock(self):
		self.sense.set_pixels(green_check)
		time.sleep(2)
		self.clear()
		
	def lock(self):
		self.sense.set_pixels(red_cross)
		time.sleep(2)
		self.clear()

	def clear(self):
		self.sense.clear((0, 0, 0))

	def breathalayzer(self):
		while True:
			for event in self.sense.stick.get_events():
				# Check if the joystick was pressed
				if event.direction == "up":
					self.trigger("BAC_success")
					return True
				if event.direction == "down":
					self.trigger("BAC_fail")
					self.lock() # TODO: Move
					return False

	# def unlock_scoot(self):
	# 	if self.breathalayzer() == True:
	# 		self.unlock()
	# 	else:
	# 		self.lock()