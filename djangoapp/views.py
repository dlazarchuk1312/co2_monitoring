from django.shortcuts import render
from pymongo import MongoClient
import json
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.linear_model import LinearRegression
from djangoapp import forecasting as fc

client = MongoClient('localhost', 27017)
db = client['co2db']
enterprises_collection = db['enterprises']
logs_collection = db['co2_logs']

def dashboard(request):
    return render(request, 'dashboard.html')

def enterprise_list(request):
    enterprises = list(enterprises_collection.find())
    for ent in enterprises:
        logs = list(logs_collection.find({'enterprise': ent.get('name')}).sort('timestamp', -1))
        if logs:
            last_log = logs[0]
            current = float(last_log.get('co2_level', 0))
            limit = float(last_log.get('limit', 4000.0))
            ent['live_co2'] = round(current, 2)
            ent['limit'] = limit
            vals = [float(l.get('co2_level', 0)) for l in logs]
            ent['avg_co2'] = round(sum(vals) / len(vals), 2)
            ent['min_co2'] = round(min(vals), 2)
            ent['max_co2'] = round(max(vals), 2)
            ent['count'] = len(vals)
            if current > limit:
                ent['live_status'] = 'danger'
                ent['live_text'] = 'Critical'
            elif current > limit * 0.9:
                ent['live_status'] = 'warning'
                ent['live_text'] = 'Warning'
            else:
                ent['live_status'] = 'success'
                ent['live_text'] = 'Normal'
        else:
            ent['live_co2'] = None
            ent['limit'] = '-'
            ent['avg_co2'] = None
            ent['min_co2'] = None
            ent['max_co2'] = None
            ent['count'] = 0
            ent['live_status'] = 'secondary'
            ent['live_text'] = 'No data'

    return render(request, 'enterprises.html', {'enterprises': enterprises})

def mqtt_dashboard(request):
    raw_data = list(logs_collection.find({}, {'_id': 0}).sort('timestamp', -1))
    if not raw_data:
        return render(request, 'mqtt_dashboard.html', {'has_data': False})
    
    df = pd.DataFrame(raw_data)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    summary = []
    names = df['enterprise'].unique()
    for ent_name in names:
        ent_df = df[df['enterprise'] == ent_name].sort_values('timestamp')
        last = ent_df.iloc[-1]
        current_val = float(last['co2_level'])
        limit_val = float(last.get('limit', 4000.0))
        mean_val = float(ent_df['co2_level'].mean())
        max_val = float(ent_df['co2_level'].max())
        min_val = float(ent_df['co2_level'].min())
        if current_val > limit_val:
            status = 'danger'
            status_text = 'Critical'
        elif current_val > (limit_val * 0.9):
            status = 'warning'
            status_text = 'Warning'
        else:
            status = 'success'
            status_text = 'Normal'
        trend_text = "Little data"
        slope = 0.0
        if len(ent_df) >= 5:
            X = np.arange(len(ent_df)).reshape(-1, 1)
            y = ent_df['co2_level'].values
            model = LinearRegression()
            model.fit(X, y)
            slope = round(float(model.coef_[0]), 4)
            if slope > 0.5:
                trend_text = "Rising"
            elif slope < -0.5:
                trend_text = "Falling"
            else:
                trend_text = "Stable"
        summary.append({
            'enterprise': ent_name,
            'current': round(current_val, 2),
            'limit': limit_val,
            'mean': round(mean_val, 2),
            'max': round(max_val, 2),
            'min': round(min_val, 2),
            'status': status,
            'status_text': status_text,
            'slope': slope,
            'trend': trend_text,
        })
    all_times = sorted(df['timestamp'].unique())
    chart_labels = json.dumps([datetime.fromtimestamp(t).strftime('%d.%m.%Y') for t in all_times])
    colors = ['blue', 'green', 'orange', 'red', 'purple']
    chart_data_json = []
    i = 0
    for ent_name in names:
        ent_df = df[df['enterprise'] == ent_name].sort_values('timestamp')
        vals_by_time = dict(zip(ent_df['timestamp'], ent_df['co2_level']))
        vals = [float(vals_by_time[t]) if t in vals_by_time else None for t in all_times]
        c = colors[i % len(colors)]
        chart_data_json.append({
            'label': ent_name,
            'data': json.dumps(vals),
            'color': c,
        })
        i = i + 1
    chart_ent = "All enterprises"
    recent_logs = []
    for item in raw_data:
        recent_logs.append({
            'enterprise': item.get('enterprise'),
            'co2_level': item.get('co2_level'),
            'date_str': datetime.fromtimestamp(item.get('timestamp')).strftime('%d.%m.%Y'),
        })
    context = {
        'has_data': True,
        'total_records': logs_collection.count_documents({}),
        'summary': summary,
        'recent_logs': recent_logs,
        'chart_ent': chart_ent,
        'chart_labels': chart_labels,
        'chart_data': chart_data_json,
    }
    return render(request, 'mqtt_dashboard.html', context)

def forecasting(request):
    names = fc.list_enterprises()
    name = request.GET.get('enterprise', '')
    if name not in names:
        name = names[0] if names else ''
    horizon = request.GET.get('horizon', 'month')
    if horizon not in fc.HORIZONS:
        horizon = 'month'
    days = fc.HORIZONS[horizon]

    result = fc.build_result(name, days) if name else None
    overview = fc.build_overview()

    chart_labels = []
    chart_history = []
    chart_forecast = []

    if result:
        hist_n = len(result['history_values'])
        fut_n = len(result['future_values'])
        chart_labels = json.dumps(
            [t.strftime('%d.%m.%Y') for t in result['history_times']]
            + [t.strftime('%d.%m.%Y') for t in result['future_times']]
        )
        chart_history = json.dumps(result['history_values'] + [None] * fut_n)
        anchor = result['history_values'][-1] if result['history_values'] else None
        chart_forecast = json.dumps([None] * (hist_n - 1) + [anchor] + result['future_values'])

    context = {
        'names': names,
        'selected': name,
        'horizon': horizon,
        'result': result,
        'overview': overview,
        'has_data': result is not None,
        'chart_labels': chart_labels,
        'chart_history': chart_history,
        'chart_forecast': chart_forecast,
    }
    return render(request, 'forecasting.html', context)
