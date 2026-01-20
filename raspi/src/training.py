import joblib
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from . import config

logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self, db_manager, preprocessor):
        self.db_manager = db_manager
        self.preprocessor = preprocessor

    def train_model(self):
        """Fetch data, process it, train model, save it."""
        logger.info("Starting model training job...")
        raw_data = self.db_manager.get_all_data()
        
        if len(raw_data) < 50:
            logger.warning("Not enough data to train model (need > 50 samples). Skipping.")
            return False

        X, y = self.preprocessor.prepare_dataset(raw_data)
        
        if len(X) == 0:
            logger.warning("Preprocessing returned empty dataset.")
            return False

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train
        clf = RandomForestClassifier(n_estimators=50, max_depth=5)
        clf.fit(X_train, y_train)
        
        # Evaluate
        preds = clf.predict(X_test)
        acc = accuracy_score(y_test, preds)
        logger.info(f"Model trained with accuracy: {acc:.2f}")
        
        # Save
        joblib.dump(clf, config.MODEL_PATH)
        logger.info(f"Model saved to {config.MODEL_PATH}")
        return True
