# risk_predictor.py — PamojaData Prediction Engine
# Uses ML to predict which indicators are at risk of going off track
# before the reporting period ends — early warning system for programme managers

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

# Path to save trained models
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'models')


def prepare_features(df, mapping):
    """
    Engineers features from indicator data for ML prediction.
    """
    df = df.copy()

    # Ensure numeric
    df[mapping['target']] = pd.to_numeric(df[mapping['target']], errors='coerce').fillna(0)
    df[mapping['achieved']] = pd.to_numeric(df[mapping['achieved']], errors='coerce').fillna(0)

    # Feature engineering
    df['achievement_rate'] = df.apply(
        lambda row: row[mapping['achieved']] / row[mapping['target']]
        if row[mapping['target']] > 0 else 0, axis=1
    )
    df['variance'] = df[mapping['achieved']] - df[mapping['target']]
    df['target_size'] = df[mapping['target']]
    df['achieved_abs'] = df[mapping['achieved']]

    # Encode sector as numeric
    le = LabelEncoder()
    df['sector_encoded'] = le.fit_transform(
        df[mapping['sector']].fillna('Unknown').astype(str)
    )

    # Encode location if available
    if mapping.get('location') and mapping['location'] in df.columns:
        df['location_encoded'] = le.fit_transform(
            df[mapping['location']].fillna('Unknown').astype(str)
        )
    else:
        df['location_encoded'] = 0

    # Label: 1 = at risk (off track), 0 = safe
    if 'Status' in df.columns:
        df['at_risk'] = df['Status'].apply(
            lambda x: 1 if x == "🔴 Off Track" else 0
        )

    return df


def get_feature_columns():
    """Returns the list of features used for prediction."""
    return [
        'achievement_rate',
        'variance',
        'target_size',
        'achieved_abs',
        'sector_encoded',
        'location_encoded'
    ]


def train_model(df, mapping):
    """
    Trains a Random Forest model on historical indicator data.
    Saves the model to the models/ folder.
    Requires data with known outcomes (Status column).
    """
    df = prepare_features(df, mapping)

    if 'at_risk' not in df.columns:
        return {'error': 'Status column required for training. Run analysis first.'}

    features = get_feature_columns()
    X = df[features]
    y = df['at_risk']

    # Need enough data to split
    if len(df) < 10:
        return {'error': 'Need at least 10 rows of historical data to train model.'}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train Random Forest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42,
        class_weight='balanced'  # Handles imbalanced data
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)

    # Save model
    os.makedirs(MODEL_PATH, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_PATH, 'risk_model.pkl'))

    return {
        'status': 'trained',
        'accuracy': round(float(report.get('accuracy', 0)) * 100, 1),  # type: ignore[arg-type]
        'model_path': os.path.join(MODEL_PATH, 'risk_model.pkl')
    }


def predict_risk(df, mapping):
    """
    Predicts risk level for each indicator.
    Uses saved model if available, otherwise uses rule-based fallback.
    """
    df = prepare_features(df, mapping)
    features = get_feature_columns()
    model_file = os.path.join(MODEL_PATH, 'risk_model.pkl')

    if os.path.exists(model_file):
        # Use trained ML model
        model = joblib.load(model_file)
        df['risk_score'] = model.predict_proba(df[features])[:, 1]
        df['risk_level'] = df['risk_score'].apply(
            lambda x: '🔴 High Risk' if x >= 0.7
            else '🟡 Medium Risk' if x >= 0.4
            else '🟢 Low Risk'
        )
        df['prediction_method'] = 'ML Model'
    else:
        # Rule-based fallback when no model is trained yet
        df['risk_score'] = 1 - df['achievement_rate'].clip(0, 1)
        df['risk_level'] = df['achievement_rate'].apply(
            lambda x: '🔴 High Risk' if x < 0.5
            else '🟡 Medium Risk' if x < 0.8
            else '🟢 Low Risk'
        )
        df['prediction_method'] = 'Rule-based (no model trained yet)'

    return df[[
        mapping['indicator_name'],
        mapping['sector'],
        'achievement_rate',
        'risk_score',
        'risk_level',
        'prediction_method'
    ]]


def get_risk_summary(risk_df):
    """Returns a summary of risk levels across all indicators."""
    return {
        'high_risk': len(risk_df[risk_df['risk_level'] == '🔴 High Risk']),
        'medium_risk': len(risk_df[risk_df['risk_level'] == '🟡 Medium Risk']),
        'low_risk': len(risk_df[risk_df['risk_level'] == '🟢 Low Risk']),
        'total': len(risk_df)
    }


def get_feature_importance(mapping):
    """
    Returns feature importance from trained model.
    Helps programme managers understand what drives risk.
    """
    model_file = os.path.join(MODEL_PATH, 'risk_model.pkl')
    if not os.path.exists(model_file):
        return None

    model = joblib.load(model_file)
    features = get_feature_columns()
    importance = pd.DataFrame({
        'Feature': features,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=False)

    return importance