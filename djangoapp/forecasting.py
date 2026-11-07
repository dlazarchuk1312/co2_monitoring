import numpy as np
import pandas as pd
from pymongo import MongoClient
from sklearn.linear_model import LinearRegression

client = MongoClient('localhost', 27017)
db = client['co2db']
logs_collection = db['co2_logs']

HORIZONS = {'month': 30, 'year': 365, '3years': 1095}

STEP_SECONDS = {
    'D': 86400,
    'h': 3600,
    'min': 60,
    '5s': 5,
}

MAX_FORECAST_POINTS = 1000


def list_enterprises():
    names = logs_collection.distinct('enterprise')
    names.sort()
    return names


def load_series(name): # load measurements for one enterprise
    docs = list(logs_collection.find(
        {'enterprise': name},
        {'_id': 0, 'co2_level': 1, 'timestamp': 1, 'limit': 1}
    ).sort('timestamp', 1))
    if len(docs) < 5:
        return None
    df = pd.DataFrame(docs)
    df['time'] = pd.to_datetime(df['timestamp'], unit='s')
    series = df.set_index('time')['co2_level'].astype(float).sort_index()
    resampled, rule = prepare(series)
    if len(resampled) < 5:
        return None
    limit = float(docs[-1].get('limit', 4000.0))
    return resampled, limit, rule


def prepare(series): # group measurements for time
    span_days = (series.index.max() - series.index.min()).total_seconds() / 86400.0
    if span_days >= 30:
        rule = 'D'
    elif span_days >= 2:
        rule = 'h'
    elif span_days >= 0.05:
        rule = 'min'
    else:
        rule = '5s'
    resampled = series.resample(rule).mean().dropna()
    return resampled, rule


def smooth(series): # make history smoother for chart after model learning
    window = max(3, len(series) // 10)
    return series.rolling(window=window, min_periods=1).mean()


def classify_trend(slope):
    if slope > 0.5:
        return 'Rising'
    if slope < -0.5:
        return 'Falling'
    return 'Stable'


def status_for_value(value, limit):
    if value > limit:
        return 'Critical'
    if value > limit * 0.9:
        return 'Warning'
    return 'Normal'


def elapsed_days(times, start_time):
    days = (times - start_time) / pd.Timedelta(days=1)
    return days.to_numpy().reshape(-1, 1)


def fit_model(series): # calculate a trend
    y = series.values.astype(float)
    X = elapsed_days(series.index, series.index[0])
    return LinearRegression().fit(X, y)


def forecast(model, series, rule, horizon_days): # make future data and forecasting co2 in the same time as we are learning
    step_seconds = STEP_SECONDS[rule]
    total_steps = horizon_days * 86400 // step_seconds
    steps = np.linspace(1, total_steps, num=min(total_steps, MAX_FORECAST_POINTS), dtype=int)
    last_time = series.index[-1]
    future_times = last_time + pd.to_timedelta(steps * step_seconds, unit='s')
    future_X = elapsed_days(future_times, series.index[0])
    future_values = np.maximum(model.predict(future_X), 0.0)
    return future_times, future_values


def build_result(name, days): # create result for Forecast details
    loaded = load_series(name)
    if loaded is None:
        return None
    series, limit, rule = loaded
    model = fit_model(series)
    future_times, future_values = forecast(model, series, rule, days)
    history_count = max(len(future_values) * 2, 60)
    history = smooth(series).iloc[-history_count:]
    return {
        'slope': round(float(model.coef_[0]), 3),
        'points': len(series),
        'min': round(float(series.min()), 2),
        'max': round(float(series.max()), 2),
        'status': status_for_value(float(series.iloc[-1]), limit),
        'history_times': list(history.index),
        'history_values': [round(float(v), 2) for v in history],
        'future_times': list(future_times),
        'future_values': [round(float(v), 2) for v in future_values],
    }


def build_overview(): # make direction for slope, status for co2 level (All enterprises)
    rows = []
    for name in list_enterprises():
        loaded = load_series(name)
        if loaded is None:
            rows.append({
                'enterprise': name,
                'current': None,
                'average': None,
                'limit': None,
                'slope': None,
                'trend': 'No data',
                'status': 'No data',
            })
            continue
        series, limit, _ = loaded
        model = fit_model(series)
        slope = float(model.coef_[0])
        current = float(series.iloc[-1])
        rows.append({
            'enterprise': name,
            'current': round(current, 2),
            'average': round(float(series.mean()), 2),
            'limit': round(limit, 2),
            'slope': round(slope, 3),
            'trend': classify_trend(slope),
            'status': status_for_value(current, limit),
        })
    return rows
