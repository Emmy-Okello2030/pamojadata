import streamlit as st
import pandas as pd
import requests
from typing import Dict, Any, Tuple
import tempfile
import os

class PamojaDataQualityClient:
    def __init__(self):
        self.api_url = st.secrets.get("QUALITY_ENGINE_URL", "http://localhost:8001")
        self.enabled = self._check_connection()
        if self.enabled:
            st.sidebar.success("âœ… Quality Engine connected")
    
    def _check_connection(self) -> bool:
        try:
            response = requests.get(f"{self.api_url}/", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def check_data_quality(self, df: pd.DataFrame, dataset_name: str = "data") -> Dict[str, Any]:
        if not self.enabled:
            return self._local_quality_check(df)
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
                df.to_csv(tmp.name, index=False)
                tmp_path = tmp.name
            
            with open(tmp_path, 'rb') as f:
                files = {'file': (f"{dataset_name}.csv", f)}
                response = requests.post(f"{self.api_url}/api/quality/check", files=files, timeout=60)
            
            os.unlink(tmp_path)
            
            if response.status_code == 200:
                job_id = response.json()['job_id']
                import time
                for _ in range(30):
                    result_response = requests.get(f"{self.api_url}/api/quality/result/{job_id}")
                    if result_response.status_code == 200:
                        data = result_response.json()
                        if data.get('status') == 'completed':
                            return data
                    time.sleep(1)
            return self._local_quality_check(df)
        except Exception as e:
            st.warning(f"Quality engine error: {str(e)}")
            return self._local_quality_check(df)
    
    def _local_quality_check(self, df: pd.DataFrame) -> Dict[str, Any]:
        missing_pct = df.isna().sum().sum() / (df.shape[0] * df.shape[1]) * 100
        duplicates = df.duplicated().sum()
        quality_score = max(0, min(1, 1 - (missing_pct / 100 + duplicates / len(df) / 2)))
        
        return {
            'status': 'completed',
            'quality_score': quality_score,
            'quality_grade': 'A' if quality_score >= 0.9 else 'B' if quality_score >= 0.8 else 'C' if quality_score >= 0.7 else 'D',
            'passed_checks': 3 if quality_score > 0.7 else 1,
            'failed_checks': 0 if quality_score > 0.7 else 2,
            'critical_issues': [] if quality_score > 0.7 else ['Data quality needs improvement'],
            'recommendations': ['Data looks good'] if quality_score > 0.7 else ['Check for missing values and duplicates'],
            'note': 'Using local quality checks (engine unavailable)'
        }
    
    def clean_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        if not self.enabled:
            return self._local_clean(df), {'method': 'local'}
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
                df.to_csv(tmp.name, index=False)
                tmp_path = tmp.name
            
            with open(tmp_path, 'rb') as f:
                files = {'file': ('data.csv', f)}
                response = requests.post(f"{self.api_url}/api/data/clean", files=files, timeout=120)
            
            os.unlink(tmp_path)
            
            if response.status_code == 200:
                job_data = response.json()
                job_id = job_data['job_id']
                import time
                for _ in range(60):
                    download_url = f"{self.api_url}/api/data/download/{job_id}"
                    check_response = requests.head(download_url)
                    if check_response.status_code == 200:
                        download_response = requests.get(download_url)
                        if download_response.status_code == 200:
                            cleaned_df = pd.read_csv(pd.compat.StringIO(download_response.text))
                            return cleaned_df, {'method': 'engine', 'job_id': job_id}
                    time.sleep(1)
            return self._local_clean(df), {'method': 'local_fallback'}
        except Exception as e:
            st.warning(f"Cleaning error: {str(e)}")
            return self._local_clean(df), {'method': 'local'}
    
    def _local_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        cleaned = df.copy()
        cleaned = cleaned.drop_duplicates()
        for col in cleaned.select_dtypes(include=['number']).columns:
            cleaned[col] = cleaned[col].fillna(cleaned[col].median())
        for col in cleaned.select_dtypes(include=['object']).columns:
            cleaned[col] = cleaned[col].fillna('Unknown')
            cleaned[col] = cleaned[col].astype(str).str.strip()
        return cleaned
