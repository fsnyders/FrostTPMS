import time
import paho.mqtt.client as mqtt
import ssl
import logging
import subprocess
import sys

from datetime import datetime as dt
from paho.mqtt.client import connack_string as ack

#---------- MQTT -----------------------------------------------------------------------------------------------
broker = 'broker.emqx.io'
port = 1883
topic = 'gometro/tpms/debug'
keepalive = 60
#message = "HELLO WORLD"
qos = 1
max_retries = 5
retry_delay = 2

# Define MQTT functions
def establish_mqtt_connection(client, max_retries=5, retry_delay=5):
    connected = False
    retry_count = 0
    # Error handling for MQTT connection result
    while not connected and retry_count < max_retries:
        try:
            client.connect(broker, port, keepalive)
            connected = True
        except Exception as e:
            retry_count += 1
            sys.stdout.write('Connection failed. Retrying in {retry_delay} seconds...')
            time.sleep(retry_delay)

    if not connected:
        sys.stdout.write('Could not establish connection after {max_retries} attempts.')
        # exit or retry logic can be implemented here
    else:
        sys.stdout.write('Connection established successfully.')

def publish_message_with_retry(client, topic, pub_message, qos=1, max_retries=5, retry_delay=5):
    retries = max_retries
    while retries > 0:
    # Error handling for MQTT publishing
        try:
            (rc, mid) = client.publish(topic, pub_message, qos=qos)
            if rc == mqtt.MQTT_ERR_SUCCESS:
                sys.stdout.write('Message with ID {mid} published successfully with QoS {qos}')
                pub_message=""                                                          #Clear published message string
                mystring=""                                                             #Clear mystring
                return True
            else:
                sys.stdout.write('Failed to publish message with QoS {qos}, Error code: {rc}')
        except Exception as e:
            sys.stdout.write('Error: Failed to publish message with QoS {qos}: {str(e)}')
        retries -= 1
        if retries > 0:
            sys.stdout.write('Retrying in {retry_delay} seconds... ({retries} retries left)')
            time.sleep(retry_delay)
    else:
        sys.stdout.write('Failed to publish message after all retries.')
        return False

def on_subscribe(client, userdata, mid, qos, tmp=None):
    # Error handling for MQTT subscription result
    try:
        if isinstance(qos, list):
            qos_msg = str(qos[0])
        else:
            qos_msg = f"and granted QoS {qos[0]}"
        sys.stdout.write(dt.now().strftime("%H:%M:%S.%f")[:-2] + " Subscribed " + qos_msg)
    except Exception as e:
        sys.stdout.write('Error in on_subscribe function:', e)

def on_message(client, userdata, message, tmp=None):
    try:
        sys.stdout.write(dt.now().strftime("%H:%M:%S.%f")[:-2] + " Received message " + str(message.payload) + " on topic " + message.topic + "' with QoS " + str(message.qos))
    except Exception as e:
        sys.stdout.write('Error while processing message:', e)

#--------------------------------------------------------------------------------------------------

#---------------- RS232 ---------------------------------------------------------------------------
def read_serial_data():
    #TPMS tyre string commands
    command_handshake=b'\xaa\x41\xa1\x06\x11\xa3'       #Dummy "handshake" message to clear serial line
    command_alltyres=b'\xaa\x41\xa1\x07\x63\x00\xf6'    #Ask for all tyre data (428 bytes)

    command_trailer=b'\xaa\x41\xa1\x07\x63\x20\x16'     #Ask for trailer data separately (218 bytes)

    out=''  #Clear out string
    ser =serial.Serial(
        port='/dev/rs232',              #Set serial port
        baudrate=9600,                  #Set Baudrate
        parity=serial.PARITY_NONE,      #Set parity = 0
        stopbits=serial.STOPBITS_ONE,   #Set stopbits = 1
        bytesize=serial.EIGHTBITS,      #Set bytesize = 8
        xonxoff=False,  
        rtscts=False,
        dsrdtr=False,
        timeout=10                      #Set timeout = 10 seconds
    )


    try:
        ser.setRTS(False)
        ser.setDTR(False)
        ser.write(command_handshake)    #Perform handshake (Clear serial)
        print('HANDSHAKE')
        time.sleep(1)
        a=ser.read(6)                    #Read response
        handshake=""
        for c in a:                       #Run through received string
            handshake=handshake+" "+hex(c)  #Add a space between each byte
        print(handshake)                  #Print received message
        a=""                             #Clear string
        handshake=""                     #Clear string
        ser.close()                      #Close serial
    except Exception as e:
        sys.stdout.write('Error with handshake request:', e)

    try:
        ser.open()   # Open serial
        ser.write(command_alltyres)   # Ask for all tyre data
        print('ALL TYRES')
        time.sleep(1.5)
        x = ser.read(428)   # Read response 
        mystring = ""
        for c in x:
            mystring = mystring + "," + hex(c)   # Add a space between each byte
        print(mystring)   # Print received message
        x = ""   # Clear string
    except serial.SerialException as e:
        sys.stdout.write('Error: Failed to read serial data. {str(e)}')
    finally:
        ser.close()   # Close serial
#--------------------------------------------------------------------------------------------------

#---------------- CTL Commands --------------------------------------------------------------------
def get_device_imei():
    # Error handling for IMEI request
    try:
        returned_output = subprocess.check_output('gsmctl -i', shell=True)    # Ask for device IMEI
        decoded_IMEI = returned_output.decode("utf-8")                         # Decode byte response to utf-8 format
        stripped_IMEI = decoded_IMEI.strip()                                   # Remove the next line characters
        return stripped_IMEI
    except Exception as e:
        sys.stdout.write('Error: Failed to get device IMEI. {str(e)}')
        return None

def get_gps_latitude():
    # Error handling for GPS latitude request
    try:
        returned_lat = subprocess.check_output('gpsctl -i', shell=True)     # Ask for GPS latitude
        decoded_lat = returned_lat.decode("utf-8")                            # Decode byte response to utf-8 format
        stripped_lat = decoded_lat.strip()                                    # Remove the next line characters
        return stripped_lat
    except Exception as e:
        sys.stdout.write('Error: Failed to get GPS latitude. {str(e)}')
        return None

def get_gps_longitude():
    # Error handling for GPS longitude request
    try:
        returned_long = subprocess.check_output('gpsctl -x', shell=True)    # Ask for GPS longitude
        decoded_long = returned_long.decode("utf-8")                         # Decode byte response to utf-8 format
        stripped_long = decoded_long.strip()                                 # Remove the next line characters
        return stripped_long
    except Exception as e:
        sys.stdout.write('Error: Failed to get GPS longitude. {str(e)}')
        return None
#--------------------------------------------------------------------------------------------------

#---------- COMPILE MESSAGE  -----------------------------------------------------------------------
def compile_pub_message():
    index = 0                                   
    new_character = ';'                                                     #Add ; separator
    mystring = mystring[:index]+new_character+mystring[index+1:]            #Take mystring and add ; before

    pub_message= dt.now().strftime("%Y-%m-%d %H:%M:%S") + ";" + stripped_lat + ";" + stripped_long + ";" + stripped_IMEI + mystring  
    sys.stdout.write(pub_message)                                                      #Publish message with format: datetime;lat;long;IMEI;mystring

#----------------------------------------------------------------------------------------------------

def run():
    mqtt.Client.connected_flag=False
    client = mqtt.Client()

    # Specify callback function
    client.on_connect = on_connect 
    client.on_message = on_message
    client.on_publish = on_publish
    client.on_subscribe = on_subscribe

    print('Ready...')

    read_serial_data()
    get_device_imei()
    get_gps_latitude()
    get_gps_longitude()
    
    compile_pub_message()

    # Attempt MQTT connection
    establish_mqtt_connection(client, max_retries, retry_delay)

    # Start MQTT client loop
    client.loop_start()

    # Attempt MQTT publish
    publish_message_with_retry(client, topic, pub_message, qos, max_retries, retry_delay)

    # Stop MQTT client loop
    client.loop_stop()
    client.disconnect()

if __name__ == '__main__':
    run()



