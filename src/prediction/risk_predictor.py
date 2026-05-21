import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'models')

def prepare_features(df, mapping):
    df = df.copy()
    df[mapping['target']] = pd.to_numeric(df[mapping['target']], errors='coerce').fillna(0)
    df[mapping['achieved']] = pd.to_numeric(df[mapping['achieved']], errors='coerce').fillna(0)
    df['achievement_rate'] = df.apply(lambda row: row[mapping['achieved']] / row[mapping['target']] if row[mapping['target']] > 0 else 0, axis=1)
    df['variance'] = df[mapping['achieved']] - df[mapping['target']]
    df['target_size'] = df[mapping['target']]
    df['achieved_abs'] = df[mapping['achieved']]
    le = LabelEncoder()
    df['sector_encoded'] = le.fit_transform(df[mapping['sector']].fillna('Unknown').astype(str))
    if mapping.get('location') and mapping['location'] in df.columns:
        df['location_encoded'] = le.fit_transform(df[mapping['location']].fillna('Unknown').astype(str))
    else:
        df['location_encoded'] = 0
    if 'Status' in df.columns:
        df['at_risk'] = df['Status'].apply(lambda x: 1 if x == "?? Off Track" else 0)
    return df

def get_feature_columns():
    return ['achievement_rate', 'variance', 'target_size', 'achieved_abs', 'sector_encoded', 'location_encoded']

def train_model(df, mapping):
    df = prepare_features(df, mapping)
    if 'at_risk' not in df.columns: return {'error': 'Status column required'}
    if len(df) < 10: return {'error': 'Need at least 10 rows'}
    
    features = get_feature_columns()
    X, y = df[features], df['at_risk']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    os.makedirs(MODEL_PATH, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_PATH, 'risk_model.pkl'))
    
    return {'status': 'trained', 'accuracy': round(acc * 100, 1)}

def predict_risk(df, mapping):
    df = prepare_features(df, mapping)
    features = get_feature_columns()
    model_file = os.path.join(MODEL_PATH, 'risk_model.pkl')
    if os.path.exists(model_file):
        model = joblib.load(model_file)
        probs = model.predict_proba(df[features])
        if probs.shape[1] > 1:
            df['risk_score'] = probs[:, 1]
        else:
            df['risk_score'] = 1.0 if model.classes_[0] == 1 else 0.0
        df['risk_level'] = df['risk_score'].apply(lambda x: '?? High Risk' if x >= 0.7 else '?? Medium Risk' if x >= 0.4 else '?? Low Risk')
        df['prediction_method'] = 'ML Model'
    else:
        df['risk_score'] = 1 - df['achievement_rate'].clip(0, 1)
        df['risk_level'] = df['achievement_rate'].apply(lambda x: '?? High Risk' if x < 0.5 else '?? Medium Risk' if x < 0.8 else '?? Low Risk')
        df['prediction_method'] = 'Rule-based (no model trained yet)'
    return df[[mapping['indicator_name'], mapping['sector'], 'achievement_rate', 'risk_score', 'risk_level', 'prediction_method']]

def get_risk_summary(risk_df):
    return {'high_risk': len(risk_df[risk_df['risk_level'] == '?? High Risk']), 'medium_risk': len(risk_df[risk_df['risk_level'] == '?? Medium Risk']), 'low_risk': len(risk_df[risk_df['risk_level'] == '?? Low Risk']), 'total': len(risk_df)}
