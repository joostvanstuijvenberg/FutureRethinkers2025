#!/usr/bin/env python

# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
#                                                                                                       #
#                       S E N D L A B   S M A R T   M E T E R   M O N I T O R                           #
#                       -----------------------------------------------------                           #
#                                                                                                       #
#    This Python script connects to SEnDlab's MQTT broker, in order to receive "P1"-messages from       #
#    various (anonymous) smart meters that are installed throughout the Netherlands, at the homes of    #
#    Avans and MNEXT employees and students and their relatives, and at various offices and factories.  #
#    It is intended to be used together with a P1 kit that you can connect to your energy meter. The    #
#    smart meter data is saved in 20 seconds intervals into a comma separated values-file, one for      #
#    each day. Expect a size of approx. 250 kB for each file (at 56 bytes per line).                    #
#                                                                                                       #
#    MNEXT Smart Energy                                                                                 #
#    Joost van Stuijvenberg                                                                             #
#    jc.vanstuijvenberg@avans.nl                                                                        #
#                                                                                                       #
#    SEnDlab.py v1.1 - 06.06.2025                                                                       #
#    https://github.com/joostvanstuijvenberg/FutureRethinkers2025.git                                   #
#    Distributed under the GNU General Public License v3.0                                              #
#    https://www.gnu.org/licenses/gpl-3.0.en.html                                                       #
#                                                                                                       #
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #

# Import necessary class and function libraries.
import base64
import paho.mqtt.client as mqtt
import json
import re
import datetime
import pytz
import csv

# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
# Place your own smart meter kit's signature here.                                                      #
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
my_own_signature = "2019-ETI-EMON-V01-D22C51-16405E"

# Don't change anything on the values listed below, unless explicitly instructed to do so.
mqtt_host = "mqtt.sendlab.nl"
mqtt_port = 11883
mqtt_user = "smartmeter_readonly"
mqtt_pwd = "RjRARDdUUn1oSg=="
mqtt_topic = "smartmeter/raw"


def on_connect(client, userdata, flags, rc, properties):
    """ When connected to the MQTT server, subscribe to the topic broadcasting smart meter data. """
    if rc == 0:
        print("Successfully connected to the MQTT broker.")
        client.subscribe("smartmeter/raw", 0)
    else:
        print("Connection error, not connected to the MQTT broker. Return code: ", rc)
        exit()

def on_message(client, userdata, msg):
    """ When a smart meter data message is received, obtain all useful information and show it on screen. """
    try:
        payload_as_str = msg.payload.decode("utf-8")
        if re.search(r'hello', payload_as_str) is not None:
            return
        json_payload = json.loads(msg.payload)
        signature = json_payload["datagram"]["signature"]
    except Exception as e:
        print("Exception occurred while fetching the JSON payload and meter's signature from the P1 message: ", e)
        return

    # If this is a message from our own kit, decode its contents, print it when needed and save it in a file.
    if signature == my_own_signature:
        try:
            # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
            # 1. Fetch the raw P1 message from the JSON payload inside the MQTT message.                #
            # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
            p1_raw = json_payload["datagram"]["p1"]
            #print(p1_raw) # <-- remove the leading '#' to see the raw P1 message.

            # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
            # 2. Decode all relevant energy data from the DSMR message.                                 #
            # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
            energy_consumed_tariff_1 = float(
                re.search(r'1-0:1\.8\.1\((0*[0-9]*\.[0-9]*)\*(kWh)\)', p1_raw).group(1, 2)[0])
            energy_consumed_tariff_2 = float(
                re.search(r'1-0:1\.8\.2\((0*[0-9]*\.[0-9]*)\*(kWh)\)', p1_raw).group(1, 2)[0])
            energy_produced_tariff_1 = float(
                re.search(r'1-0:2\.8\.1\((0*[0-9]*\.[0-9]*)\*(kWh)\)', p1_raw).group(1, 2)[0])
            energy_produced_tariff_2 = float(
                re.search(r'1-0:2\.8\.2\((0*[0-9]*\.[0-9]*)\*(kWh)\)', p1_raw).group(1, 2)[0])
            power_currently_consumed = float(
                re.search(r'1-0:1\.7\.0\((0*[0-9]*\.[0-9]*)\*(kW)\)', p1_raw).group(1, 2)[0])
            power_currently_produced = float(
                re.search(r'1-0:2\.7\.0\((0*[0-9]*\.[0-9]*)\*(kW)\)', p1_raw).group(1, 2)[0])
            gas_consumed = re.search(r'0-[1-4]+:24\.2\.1\((0*[0-w]*)\)\(*(0*[0-9]*\.[0-9]*)\*(m3)\)', p1_raw)

            # If you need the amounts of energy consumed and produced in the two different tariffs, please
            # remove the '#' before the lines directly below.
            relevant_energy_data = {
                "date": str(datetime.datetime.now(pytz.timezone('Europe/Amsterdam')).strftime("%Y.%m.%d")),
                "time": str(datetime.datetime.now(pytz.timezone('Europe/Amsterdam')).strftime("%H:%M:%S")),
                #"energy_consumed_tariff_1": energy_consumed_tariff_1,
                #"energy_consumed_tariff_2": energy_consumed_tariff_2,
                "energy_consumed_total": "{:.3f}".format(energy_consumed_tariff_1 + energy_consumed_tariff_2),
                #"energy_produced_tariff_1": energy_produced_tariff_1,
                #"energy_produced_tariff_2": energy_produced_tariff_2,
                "energy_produced_total": "{:.3f}".format(energy_produced_tariff_1 + energy_produced_tariff_2, 3),
                "power_currently_consumed": "{:.3f}".format(power_currently_consumed, 3),
                "power_currently_produced": "{:.3f}".format(power_currently_produced, 3),
                "gas_consumed": "{:.3f}".format(float(gas_consumed.group(1, 2, 3)[1]) if gas_consumed is not None else 0, 3)
            }
            #print(relevant_energy_data) # <-- remove the leading '#' to see the decoded relevant energy data.

            # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
            # 3. Save the energy data as comma separated values to a file, one for each day.            #
            # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * #
            filename = str(datetime.datetime.now(pytz.timezone('Europe/Amsterdam')).strftime("%Y%m%d")) + ".csv"
            with open(filename, 'a') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(relevant_energy_data.values())

        except Exception as e:
            print("MQTT.on_message() exception: ", e)


if __name__ == '__main__':
    """ Setup an MQTT client, connect it to SEnDlabs MQTT broker and await P1 messages. """
    try:
        mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqttc.on_connect = on_connect
        mqttc.on_message = on_message
        mqttc.username_pw_set(username=mqtt_user, password=base64.b64decode(mqtt_pwd).decode("utf-8"))
        mqttc.connect(mqtt_host, mqtt_port, 10)
        mqttc.loop_forever()
    except Exception as e:
        print("Something went wrong:", e)
