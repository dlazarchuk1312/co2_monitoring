import pandas as pd
import numpy as np
from pymongo import MongoClient
from sklearn.linear_model import LinearRegression

client = MongoClient('localhost', 27017)
db = client['co2db']
logs_collection = db['co2_logs']
data = list(logs_collection.find({}, {'_id': 0, 'enterprise': 1, 'co2_level': 1, 'timestamp': 1}))

if not data:
    print("Database is empty")
else:
    df = pd.DataFrame(data)
    print("Average values:")
    print(f"Total records: {len(df)}")
    names = df['enterprise'].unique()
    for name in names:
        part = df[df['enterprise'] == name]['co2_level']
        avg = part.mean()
        mx = part.max()
        mn = part.min()
        print(f"{name}: avg={round(avg, 2)}, max={round(mx, 2)}, min={round(mn, 2)}")
    print("\nTrends:")
    target = "Zaporizhstal"
    ent_df = df[df['enterprise'] == target].copy()
    if len(ent_df) > 5:
        X = np.arange(len(ent_df)).reshape(-1, 1)
        y = ent_df['co2_level'].values
        model = LinearRegression()
        model.fit(X, y)
        slope = float(model.coef_[0])
        print(f"Enterprise: {target}")
        print(f"Slope: {round(slope, 4)}")
        if slope > 0:
            print("Emissions are increasing")
        elif slope < 0:
            print("Emissions are decreasing")
        else:
            print("Emissions are stable")
    else:
        print(f"Little data")
