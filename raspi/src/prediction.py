import joblib
import os
import logging
from . import config

logger = logging.getLogger(__name__)

class Predictor:
    def __init__(self, preprocessor, explainability_module):
        self.preprocessor = preprocessor
        self.explainer = explainability_module
        self.model = None
        self.load_model()

    def load_model(self):
        if os.path.exists(config.MODEL_PATH):
            try:
                self.model = joblib.load(config.MODEL_PATH)
                logger.info("Model loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
        else:
            logger.warning("Model file not found. Predictions will be unavailable until training occurs.")

    def predict(self, recent_data):
        """
        Make a prediction based on recent data.
        Returns: (prediction_label, explanation_text)
        """
        if not self.model:
            # Try reloading in case it was just trained
            self.load_model()
            if not self.model:
                return None, "Model not ready."

        if not recent_data:
            return None, "No data available."

        features = self.preprocessor.prepare_single_prediction(recent_data)
        
        try:
            prediction_idx = self.model.predict(features)[0]
            prediction_label = "Stress (Needs Water)" if prediction_idx == 1 else "Healthy"
            
            # Generate explanation
            explanation = self.explainer.explain_decision(self.model, features, prediction_label)
            
            return prediction_label, explanation
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return None, str(e)
