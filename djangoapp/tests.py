from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from django.test import SimpleTestCase
from django.urls import reverse
from djangoapp import forecasting, views


class CO2MonitoringTests(SimpleTestCase):
    def setUp(self): # готуємо 8 замірів зі зростанням co2 на 2 ppm за день
        self.enterprise = 'Zaporizhstal'
        start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        self.readings = [
            {
                'enterprise': self.enterprise,
                'co2_level': 1000 + day * 2,
                'timestamp': int((start + timedelta(days=day)).timestamp()),
                'limit': 1100,
            }
            for day in range(0, 36, 5)
        ]

    def test_dashboard_loads(self): # перевірка відкриття головної сторінки
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

    def test_enterprises_show_average_and_status(self): # перевірка середнього значення та статус підприємства
        with (
            patch.object(views, 'enterprises_collection') as enterprises,
            patch.object(views, 'logs_collection') as logs,
        ):
            enterprises.find.return_value = [{'name': self.enterprise}]
            logs.find.return_value.sort.return_value = list(reversed(self.readings))
            response = self.client.get(reverse('enterprises'))

        self.assertTemplateUsed(response, 'enterprises.html')
        self.assertContains(response, '<td>1035.0</td>', html=True)
        self.assertContains(response, 'Warning')

    def test_enterprises_show_zero_average(self): # перевірка, чи показується нульове середнє як 0.0
        with (
            patch.object(views, 'enterprises_collection') as enterprises,
            patch.object(views, 'logs_collection') as logs,
        ):
            enterprises.find.return_value = [{'name': self.enterprise}]
            logs.find.return_value.sort.return_value = [
                {**self.readings[0], 'co2_level': 0},
            ]
            response = self.client.get(reverse('enterprises'))

        self.assertContains(response, '<td>0.0</td>', html=True)

    def test_mqtt_shows_latest_readings(self): # перевірка кількості замірів, останню дату й останнє значення
        with patch.object(views, 'logs_collection') as logs:
            logs.find.return_value.sort.return_value = list(reversed(self.readings))
            logs.count_documents.return_value = len(self.readings)
            response = self.client.get(reverse('mqtt'))

        self.assertTemplateUsed(response, 'mqtt_dashboard.html')
        self.assertContains(response, 'Latest sensor readings (8 total)')
        self.assertContains(response, '<td>05.02.2026</td>', html=True)
        self.assertEqual(response.context['summary'][0]['current'], 1070)

    def test_mqtt_shows_no_data_for_empty_collection(self): # перевірка сторінки mqtt, якщо замірів немає
        with patch.object(views, 'logs_collection') as logs:
            logs.find.return_value.sort.return_value = []
            response = self.client.get(reverse('mqtt'))

        self.assertContains(response, '<p>No data</p>', html=True)
        self.assertFalse(response.context['has_data'])

    def test_forecasting_reaches_each_horizon(self): # перевірка правильності нахилу, кінцеву дату й значення прогнозу для місяця, року, 3 років
        with patch.object(forecasting, 'logs_collection') as logs:
            logs.distinct.return_value = [self.enterprise]
            logs.find.return_value.sort.return_value = self.readings
            for horizon, days in [('month', 30), ('year', 365), ('3years', 1095)]:
                with self.subTest(horizon=horizon):
                    response = self.client.get(reverse('forecasting'), {
                        'enterprise': self.enterprise,
                        'horizon': horizon,
                    })

                    self.assertTemplateUsed(response, 'forecasting.html')
                    self.assertContains(response, 'id="forecastChart"')
                    result = response.context['result']
                    self.assertEqual(result['slope'], 2)
                    self.assertEqual(result['future_values'][-1], 1070 + 2 * days)
                    self.assertEqual(
                        result['future_times'][-1] - result['history_times'][-1],
                        timedelta(days=days),
                    )

    def test_forecasting_needs_at_least_five_readings(self): # перевірка, що <5 значень недостатньо для прогнозу
        with patch.object(forecasting, 'logs_collection') as logs:
            logs.distinct.return_value = [self.enterprise]
            logs.find.return_value.sort.return_value = self.readings[:4]
            response = self.client.get(reverse('forecasting'))

        self.assertContains(response, 'No data')
        self.assertFalse(response.context['has_data'])
        self.assertNotContains(response, 'id="forecastChart"')

    def test_classify_trend(self): # перевірка зростання, падіння та стабільності тренду
        self.assertEqual(forecasting.classify_trend(0.6), 'Rising')
        self.assertEqual(forecasting.classify_trend(-0.6), 'Falling')
        self.assertEqual(forecasting.classify_trend(0.5), 'Stable')
