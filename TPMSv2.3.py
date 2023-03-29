import time
import paho.mqtt.client as mqtt
import ssl
import logging
import subprocess
import sys
import serial

from datetime import datetime as dt
from paho.mqtt.client import connack_string as ack

class RS232Reader:

    def __init__(self, port='/dev/rs232', baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, xonxoff=False, rtscts=False, dsrdtr=False, timeout=10):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.dsrdtr = dsrdtr
        self.timeout = timeout

    def read_serial_data(self):
        global mystring

class RS232Reader:

    def __init__(self, port='/dev/rs232', baudrate=9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, xonxoff=False, rtscts=False, dsrdtr=False, timeout=10):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.dsrdtr = dsrdtr
        self.timeout = timeout

    def read_serial_data(self):
        global mystring

        command_handshake = b'\xaa\x41\xa1\x06\x11\xa3'
        command_alltyres = b'\xaa\x41\xa1\x07\x63\x00\xf6'
        command_trailer = b'\xaa\x41\xa1\x07\x63\x20\x16'

        out = ''
        ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            parity=self.parity,
            stopbits=self.stopbits,
            bytesize=self.bytesize,
            xonxoff=self.xonxoff,
            rtscts=self.rtscts,
            dsrdtr=self.dsrdtr,
            timeout=self.timeout
        )

        error_msg = None

        try:
            ser.setRTS(False)
            ser.setDTR(False)
            ser.write(command_handshake)
            print('HANDSHAKE')
            time.sleep(1)
            a = ser.read(6)
            handshake = ""
            for c in a:
                handshake = handshake + " " + hex(c)
            print(handshake)
            a = ""
            handshake = ""
            ser.close()
        except Exception as e:
            error_msg = f'Error with handshake request: {e}'
            sys.stdout.write(error_msg)

        try:
            ser.open()
            ser.write(command_alltyres)
            print('ALL TYRES')
            time.sleep(1.5)
            x = ser.read(428)
            mystring = ""
            for c in x:
                mystring = mystring + "," + hex(c)
            print(mystring)
            x = ""
        except serial.SerialException as e:
            error_msg = f'Error: Failed to read serial data. {str(e)}'
            sys.stdout.write(error_msg)
        finally:
            ser.close()

        return error_msg  # This line should be inside the function


    def run(self):
        error_msg = self.read_serial_data()
        return error_msg


class DeviceData:

    def __init__(self):
        self.imei = None
        self.latitude = None
        self.longitude = None
        self.pub_message = None

    def get_device_imei(self):
        try:
            returned_output = subprocess.check_output('gsmctl -i', shell=True)
            decoded_imei = returned_output.decode("utf-8")
            self.imei = decoded_imei.strip()
        except Exception as e:
            sys.stdout.write(f'Error: Failed to get device IMEI. {str(e)}')

    def get_gps_latitude(self):
        try:
            returned_lat = subprocess.check_output('gpsctl -i', shell=True)
            decoded_lat = returned_lat.decode("utf-8")
            self.latitude = decoded_lat.strip()
        except Exception as e:
            sys.stdout.write(f'Error: Failed to get GPS latitude. {str(e)}')

    def get_gps_longitude(self):
        try:
            returned_long = subprocess.check_output('gpsctl -x', shell=True)
            decoded_long = returned_long.decode("utf-8")
            self.longitude = decoded_long.strip()
        except Exception as e:
            sys.stdout.write(f'Error: Failed to get GPS longitude. {str(e)}')


    def compile_pub_message(self, global_mystring):
        global mystring
        mystring = global_mystring
        if self.latitude is None or self.longitude is None or self.imei is None:
            sys.stdout.write('Error: Missing device data.')
            return None

        index = 0
        self.pub_message = f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')};{self.latitude};{self.longitude};{self.imei};{mystring}"
    
    def run(self, global_mystring):
        self.get_device_imei()
        self.get_gps_latitude()
        self.get_gps_longitude()
        self.compile_pub_message(global_mystring)
#------------- #V1 --------------------------------------------------------------------------------------
class MQTTClient:

    def __init__(self, broker='broker.emqx.io', port=1883, topic='gometro/tpms/debug', keepalive=60, qos=1, max_retries=5, retry_delay=2):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.keepalive = keepalive
        self.qos = qos
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = mqtt.Client()

    def establish_mqtt_connection(self):
        connected = False
        retry_count = 0
        while not connected and retry_count < self.max_retries:
            try:
                self.client.connect(self.broker, self.port, self.keepalive)
                connected = True
            except Exception as e:
                retry_count += 1
                sys.stdout.write(f'Connection failed. Retrying in {self.retry_delay} seconds...')
                time.sleep(self.retry_delay)

        if not connected:
            sys.stdout.write(f'Could not establish connection after {self.max_retries} attempts.')
        else:
            sys.stdout.write('Connection established successfully.')

    def publish_message_with_retry(self, pub_message):
        retries = self.max_retries
        while retries > 0:
            try:
                (rc, mid) = self.client.publish(self.topic, pub_message, qos=self.qos)
                if rc == mqtt.MQTT_ERR_SUCCESS:
                    sys.stdout.write(f'Message with ID {mid} published successfully with QoS {self.qos}')
                    pub_message = ""
                    mystring = ""
                    return True
                else:
                    sys.stdout.write(f'Failed to publish message with QoS {self.qos}, Error code: {rc}')
            except Exception as e:
                sys.stdout.write(f'Error: Failed to publish message with QoS {self.qos}: {str(e)}')
            retries -= 1
            if retries > 0:
                sys.stdout.write(f'Retrying in {self.retry_delay} seconds... ({retries} retries left)')
                time.sleep(self.retry_delay)
        else:
            sys.stdout.write('Failed to publish message after all retries.')
            return False

    def run(self, pub_message, error_msg=None):
        mqtt.Client.connected_flag = False

        self.establish_mqtt_connection()

        self.client.loop_start()

        if error_msg:
            self.publish_message_with_retry(error_msg)

        self.publish_message_with_retry(pub_message)

        self.client.loop_stop()
        self.client.disconnect()

mystring = ""

if __name__ == '__main__':
    rs232_reader = RS232Reader()
    error_msg = rs232_reader.run()

    if error_msg:
        device_data = DeviceData()
        device_data.run(mystring)

        mqtt_client = MQTTClient()
        mqtt_client.run(device_data.pub_message, error_msg)
    else:
        device_data = DeviceData()
        device_data.run(mystring)

        mqtt_client = MQTTClient()
        mqtt_client.run(device_data.pub_message)






