import pandas as pd
import numpy as np

class DataPreprocessor:
    def __init__(self):
        pass

    def prepare_dataset(self, raw_data):
        """
        Convert raw DB tuples into a DataFrame with features.
        raw_data: list of tuples (timestamp, soil, temp, hum, light, temp_lm35)
        """
        if not raw_data:
            return pd.DataFrame(), pd.Series()

        df = pd.DataFrame(raw_data, columns=['timestamp', 'soil_moisture', 'temperature', 'humidity', 'light_intensity', 'temperature_lm35'])
        
        # Merge temperatures for robustness (average) or use primary
        df['avg_temp'] = df[['temperature', 'temperature_lm35']].mean(axis=1)

        # Feature Engineering: Rate of change (slope)
        df = df.sort_values('timestamp')
        
        df['time_diff'] = df['timestamp'].diff()
        df['soil_diff'] = df['soil_moisture'].diff()
        
        df['soil_slope'] = df.apply(
            lambda row: row['soil_diff'] / row['time_diff'] if row['time_diff'] > 0 else 0, axis=1
        )
        
        df = df.dropna()

        threshold = 400 
        df['is_stressed'] = (df['soil_moisture'] < threshold).astype(int)

        # Features to use for training
        # Added light and avg_temp
        feature_cols = ['soil_moisture', 'avg_temp', 'humidity', 'light_intensity', 'soil_slope']
        X = df[feature_cols]
        y = df['is_stressed']
        
        return X, y

    def prepare_single_prediction(self, recent_data):
        """
        Prepare features for a single prediction based on recent history.
        recent_data: list of tuples (timestamp, soil, temp, hum, light, temp_lm35)
        """
        if len(recent_data) < 2:
            last_point = recent_data[-1]
            avg_temp = (last_point[2] + last_point[5]) / 2
            return pd.DataFrame([{
                'soil_moisture': last_point[1], 
                'avg_temp': avg_temp, 
                'humidity': last_point[3],
                'light_intensity': last_point[4],
                'soil_slope': 0
            }])
            
        df = pd.DataFrame(recent_data, columns=['timestamp', 'soil_moisture', 'temperature', 'humidity', 'light_intensity', 'temperature_lm35'])
        df['avg_temp'] = df[['temperature', 'temperature_lm35']].mean(axis=1)
        df = df.sort_values('timestamp')
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        time_diff = last_row['timestamp'] - prev_row['timestamp']
        soil_diff = last_row['soil_moisture'] - prev_row['soil_moisture']
        
        slope = (soil_diff / time_diff) if time_diff > 0 else 0
        
        features = pd.DataFrame([{
            'soil_moisture': last_row['soil_moisture'],
            'avg_temp': last_row['avg_temp'],
            'humidity': last_row['humidity'],
            'light_intensity': last_row['light_intensity'],
            'soil_slope': slope
        }])
        
        return features
