import RPi.GPIO as GPIO
from time import sleep

# set up pins
GPIO.setmode(GPIO.BCM)

GPIO.setup(11, GPIO.OUT)
GPIO.setup(5,GPIO.IN)
GPIO.setup(8,GPIO.OUT)

# name pins
clock = 11
miso = 5
cs = 8

# bring clock and cs high
GPIO.output(clock,True)
GPIO.output(cs,True)

# begin loop to print a stream of data
def breathalyzer():
    readings = []

    print("Starting breathalyzer measurement for 10 seconds at 100 samples/sec...")
    for _ in range(1000):  # 1000 readings over 10 seconds
        GPIO.output(cs, False)

        voltage_bits = ""

        for i in range(15):
            GPIO.output(clock, False)
            voltage_bits += "1" if GPIO.input(miso) else "0"
            GPIO.output(clock, True)

        voltage_bits = voltage_bits.strip()[2:14]
        voltage = int(voltage_bits, 2) * (5 / 2048)

        # Estimate promille from voltage
        promille = (voltage - 0.4) * (2.0 / 3.0)  # Simple linear map
        promille = max(promille, 0.0)  # No negative promille

        readings.append(promille)

        GPIO.output(cs, True)
        sleep(0.01)  # 0.01 sec = 100 Hz

    avg_promille = sum(readings) / len(readings)
    print(f"Average Promille over 10 seconds: {avg_promille:.3f}")
    
    
breathalyzer()