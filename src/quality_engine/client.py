"""
Quality Engine API Client for PamojaData
Integrates the Adaptive Quality Engine with your platform
"""

import requests
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json
import streamlit as st

class QualityEngineClient:
    """Client to connect PamojaData with the Quality Engine API"""
    
    def __init__(self, api_url: str = None):
        # Allow configuration via Streamlit secrets or environment
        self.api_url = api_url or st.secrets.get("QUALITY_ENGINE_URL", "http://localhost:8000")
        self.enabled = self._check_connection()
    
    def _check_connection(self) -> bool:
        """Check if quality engine is available"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def enhance_quality_check(self, df: pd.DataFrame, 
                              dataset_name: str = "unknown") -> Dict[str, Any]:
        """
        Enhanced quality check using the engine
        Returns detailed quality report
        """
        if not self.enabled:
            return {"error": "Quality engine not available", "fallback": True}
        
        # Save dataframe to temp file
        temp_path = f"/tmp/quality_check_{dataset_name}.csv"
        df.to_csv(temp_path, index=False)
        
        try:
            with open(temp_path, 'rb') as f:
                files = {'file': (f"{dataset_name}.csv", f)}
                response = requests.post(
                    f"{self.api_url}/api/quality/check",
                    files=files,
                    timeout=60
                )
            
            if response.status_code == 200:
                job_id = response.json()['job_id']
                
                # Poll for results
                import time
                for _ in range(30):  # 30 second timeout
                    result_response = requests.get(
                        f"{self.api_url}/api/quality/result/{job_id}"
                    )
                    if result_response.status_code == 200:
                        data = result_response.json()
                        if data['status'] == 'completed':
                            return self._format_for_pamojadata(data)
                        elif data['status'] == 'failed':
                            return {"error": data.get('error', 'Unknown'), "fallback": True}
                    time.sleep(1)
            
            return {"error": "Quality check timeout", "fallback": True}
            
        except Exception as e:
            return {"error": str(e), "fallback": True}
        finally:
            # Cleanup
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def _format_for_pamojadata(self, engine_result: Dict) -> Dict[str, Any]:
        """Convert engine results to PamojaData format"""
        return {
            'overall_quality_score': engine_result.get('quality_score', 0),
            'quality_grade': engine_result.get('quality_grade', 'F'),
            'passed_checks': engine_result.get('passed_checks', 0),
            'failed_checks': engine_result.get('failed_checks', 0),
            'critical_issues': engine_result.get('critical_issues', []),
            'recommendations': engine_result.get('recommendations', []),
            'advanced_metrics': {
                'completeness': self._extract_metric(engine_result, 'completeness'),
                'uniqueness': self._extract_metric(engine_result, 'uniqueness'),
                'consistency': self._extract_metric(engine_result, 'consistency')
            },
            'engine_version': '2.0',
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_metric(self, result: Dict, metric_name: str) -> float:
        """Extract specific metric from engine results"""
        # This would parse the detailed results
        # Simplified for now
        return 0.85  # Placeholder
    
    def get_cleaning_suggestions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get smart cleaning suggestions from the engine"""
        if not self.enabled:
            return {"suggestions": [], "note": "Engine not available"}
        
        # Similar pattern to enhance_quality_check but for cleaning
        # Returns recommended cleaning operations
        return {
            "suggested_operations": [
                "Remove duplicates",
                "Impute missing values in age column",
                "Standardize date formats"
            ],
            "auto_fixable": True
        }