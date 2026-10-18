import json
import paho.mqtt.client as mqtt
from pymongo import MongoClient

db_client = MongoClient('localhost', 27017)
db = db_client['co2db']
logs_collection = db['co2_logs']

def on_connect(client, userdata, flags, rc, properties=None):
    client.subscribe("co2/sensors")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        logs_collection.insert_one(payload)
        print(f"[{payload['enterprise']}] CO2: {payload['co2_level']} ppm added to database")
    except Exception as e:
        print(f"Error with message: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.loop_forever()