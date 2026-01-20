import numpy as np

class ExplainabilityModule:
    def __init__(self):
        pass

    def explain_decision(self, model, feature_row, decision_label):
        """
        Provide a text explanation for why a Model made a decision.
        Uses Feature Importance from Random Forest.
        """
        # Get feature importances
        if not hasattr(model, 'feature_importances_'):
            return "Model does not support feature importance explanation."

        importances = model.feature_importances_
        feature_names = feature_row.columns
        
        # Sort features by importance
        indices = np.argsort(importances)[::-1]
        
        top_feature_idx = indices[0]
        top_feature_name = feature_names[top_feature_idx]
        top_feature_val = feature_row.iloc[0][top_feature_name]
        
        # Simple rule-based string generation based on top factor
        explanation = f"Decision '{decision_label}' was primarily influenced by {top_feature_name} ({top_feature_val:.2f})."
        
        if top_feature_name == 'soil_moisture':
            if decision_label.startswith("Stress") and top_feature_val < 500: 
                 explanation += " Soil moisture is critically low."
        elif top_feature_name == 'soil_slope':
             explanation += " Rapid change in soil moisture detected."
        elif top_feature_name == 'light_intensity':
             if top_feature_val > 600:
                explanation += " High light intensity causing faster evaporation."
             else:
                explanation += " Low light conditions affecting plant cycle."
        elif top_feature_name == 'avg_temp':
             explanation += f" Temperature ({top_feature_val:.1f}C) is a key factor."
             
        return explanation
