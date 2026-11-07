import time
import json
from datetime import datetime, timedelta, timezone
import numpy as np
import paho.mqtt.client as mqtt

START_DATE = "2026-01-01"

enterprises = [
    {"name": "Zaporizhstal", "base": 4200.0, "std": 120.0, "limit": 4500.0},
    {"name": "Motor Sich", "base": 1200.0, "std": 40.0, "limit": 1350.0},
    {"name": "Dneprospetsstal", "base": 2800.0, "std": 80.0, "limit": 3000.0},
    {"name": "Zaporozhkoks", "base": 3100.0, "std": 95.0, "limit": 3300.0},
    {"name": "Zaporozhtransformator", "base": 450.0, "std": 20.0, "limit": 500.0},
]

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("localhost", 1883, 60)
vtime = datetime.strptime(START_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
while True:
    for ent in enterprises:
        # take base value
        base = ent["base"]
        # add noise
        noise = np.random.normal(0, ent["std"])
        # 5% chance to spike
        spike = 0.0
        if np.random.rand() < 0.05:
            spike = float(np.random.uniform(200, 500))
        # calculte value
        value = base + noise + spike
        if value < 0:
            value = 0.0
        value = round(float(value), 2)
        payload = {
            "enterprise": ent["name"],
            "co2_level": value,
            "limit": ent["limit"],
            "timestamp": int(vtime.timestamp())
        }
        client.publish("co2/sensors", json.dumps(payload))
        print(f"Sent: {ent['name']} = {value} ppm")
    vtime += timedelta(days=1)
    time.sleep(1)
