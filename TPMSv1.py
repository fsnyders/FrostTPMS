import time
import serial
import paho.mqtt.client as mqtt
import ssl
import logging
import subprocess

#GIT TEST1

from datetime import datetime as dt
from paho.mqtt.client import connack_string as ack

#Define MQTT functions
def on_connect(client, userdata, flags, rc, v5config=None):
	print(dt.now().strftime("%H:%M:%S.%f")[:-2] + " Connection return result: "+ack(rc))
#Error handling for connection result
	if rc==0:
		client.connected_flag=True
		print("connected OK")						
	else:
		print("Bad connection, Returned code=", rc)

def on_message(client, userdata, message, tmp=None):
	print(dt.now().strftime("%H:%M:%S.%f")[:-2] + " Received message " + str(message.payload) + " on topic " + message.topic + "' with QoS " + str(message.qos))

def on_publish(client, userdata, mid, tmp=None):
	print(dt.now().strftime("%H:%M:%S.%f")[:-2] + " Published message id: "+str(mid))

def on_subscribe(client, userdata, mid, qos, tmp=None):
	if isinstance(qos, list):
		qos_msg = str(qos[0])

	else:
		qos_msg = f"and granted QoS {qos[0]}"
		print(dt.now().strftime("%H:%M:%S.%f")[:-2] + " Subscribed " + qos_msg)

mqtt.Client.connected_flag=False
client = mqtt.Client()

#Specify callback function
client.on_connect = on_connect 
client.on_message = on_message
client.on_publish = on_publish
client.on_subscribe = on_subscribe

print('Ready...')

#TPMS tyre string commands
command_handshake=b'\xaa\x41\xa1\x06\x11\xa3'   	#Dummy "handshake" message to clear serial line
command_alltyres=b'\xaa\x41\xa1\x07\x63\x00\xf6' 	#Ask for all tyre data (428 bytes)

command_trailer=b'\xaa\x41\xa1\x07\x63\x20\x16' 	#Ask for trailer data separately (218 bytes)

out=''  #Clear out string
ser	=serial.Serial(
	port='/dev/rs232',  			#Set serial port
	baudrate=9600,  				#Set Baudrate
	parity=serial.PARITY_NONE,  	#Set parity = 0
	stopbits=serial.STOPBITS_ONE,   #Set stopbits = 1
	bytesize=serial.EIGHTBITS,  	#Set bytesize = 8
	xonxoff=False,  
	rtscts=False,
	dsrdtr=False,
	timeout=10						#Set timeout = 10 seconds
)

#ser.isOpen()
ser.setRTS(False)
ser.setDTR(False)
ser.write(command_handshake)  		#Perform handshake (Clear serial)
print('HANDSHAKE')  
time.sleep(1)
a=ser.read(6)						#Read response
handshake=""
for c in a:							#Run through received string
	handshake=handshake+" "+hex(c)  #Add a space between each byte
print(handshake)  					#Print received message
a=""  								#Clear string
handshake=""  						#Clear string
ser.close()							#Close serial

time.sleep(0.5)
ser.open()							#Open serial
ser.write(command_alltyres)  		#Ask for all tyre data
print('ALL TYRES')
time.sleep(1.5)
x=ser.read(428)  					#Read response 
mystring=""							
for c in x:							#Run through received string
	mystring=mystring+","+hex(c)	#Add a space between each byte
print(mystring)  #					#Print received message
x=""  								#Clear string
ser.close()							#Close serial

#time.sleep(1)
#ser.open()
#ser.write(command_trailer)
#print('TRAILER')
#time.sleep(1)
#y=ser.read(218)
#mystring1=""
#for c in y:
#	mystring1=mystring1+" "+hex(c)
#print(mystring1)
#y=""
#ser.close()

returned_output = subprocess.check_output('gsmctl -i', shell = True)	#Ask for device IMEI
decoded_IMEI = returned_output.decode("utf-8")							#Decode byte response to utf-8 format
stripped_IMEI = decoded_IMEI.strip()									#Remove the next line characters

returned_lat = subprocess.check_output('gpsctl -i', shell=True)    		#Ask for GPS latitude 
decoded_lat = returned_lat.decode("utf-8")        						#Decode byte response to utf-8 format
stripped_lat = decoded_lat.strip()          							#Remove the next line characters

returned_long = subprocess.check_output('gpsctl -x', shell=True)   		#Ask for GPS longitude
decoded_long = returned_long.decode("utf-8")    						#Decode byte response to utf-8 format
stripped_long = decoded_long.strip()    								#Remove the next line characters

index = 0 									
new_character = ';'                                                     #Add ; separator
mystring = mystring[:index]+new_character+mystring[index+1:]			#Take mystring and add ; before

#Start MQTT client loop
client.loop_start()														#Start MQTT Client Loop

#Establish a connection
client.connect('broker.emqx.io', 1883, 60)								#Connect to MQTT broker 

while not client.connected_flag:										#Indicate connection status
	print("in wait loop...")
	time.sleep(1)

#Publish a message
pub_message= dt.now().strftime("%Y-%m-%d %H:%M:%S") + ";" + stripped_lat + ";" + stripped_long + ";" + stripped_IMEI + mystring  
print(pub_message)  													#Publish message with format: datetime;lat;long;IMEI;mystring
client.publish('gometro/tpms/fleet1', payload=pub_message, qos=1)  		#Publish to broker with topic xyz
pub_message=""															#Clear published message string
mystring=""																#Clear mystring
#mystring1=""
#Subscribe to a topic
#client.subscribe('testtopic/pahopython')

#client.loop_forever()
client.loop_stop()														#Stop MQTT Client Loop

