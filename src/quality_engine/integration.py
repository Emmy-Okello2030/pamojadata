"""
Bridge between PamojaData's existing quality system and the new engine
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Tuple

# Import existing PamojaData quality modules
from src.quality.quality_checks import QualityChecker as ExistingChecker
from src.quality_engine.client import QualityEngineClient

class UnifiedQualitySystem:
    """
    Unifies existing PamojaData quality checks with the advanced engine
    Falls back to existing system if engine is unavailable
    """
    
    def __init__(self):
        self.engine_client = QualityEngineClient()
        self.existing_checker = ExistingChecker() if self._has_existing() else None
    
    def _has_existing(self) -> bool:
        """Check if existing quality module is available"""
        try:
            from src.quality.quality_checks import QualityChecker
            return True
        except:
            return False
    
    def check_data_quality(self, df: pd.DataFrame, 
                           dataset_name: str = "program_data") -> Dict[str, Any]:
        """
        Comprehensive quality check using both systems
        """
        results = {
            'basic_checks': {},
            'advanced_checks': {},
            'combined_score': 0,
            'recommendations': []
        }
        
        # Run existing checks (always available)
        if self.existing_checker:
            try:
                existing_results = self.existing_checker.run_checks(df)
                results['basic_checks'] = existing_results
                results['combined_score'] += existing_results.get('score', 0) * 0.4
            except Exception as e:
                results['basic_checks'] = {'error': str(e)}
        
        # Run engine checks (if available)
        if self.engine_client.enabled:
            try:
                engine_results = self.engine_client.enhance_quality_check(df, dataset_name)
                if 'error' not in engine_results:
                    results['advanced_checks'] = engine_results
                    results['combined_score'] += engine_results.get('overall_quality_score', 0) * 0.6
                    results['recommendations'].extend(engine_results.get('recommendations', []))
            except Exception as e:
                results['advanced_checks'] = {'error': str(e), 'fallback': True}
        else:
            results['advanced_checks'] = {'status': 'unavailable'}
            # Adjust weight if engine not available
            results['combined_score'] = results['basic_checks'].get('score', 0) * 1.0
        
        return results
    
    def display_quality_dashboard(self, results: Dict[str, Any]):
        """
        Display quality results in Streamlit (PamojaData UI)
        """
        st.subheader("📊 Data Quality Assessment")
        
        # Overall score with gauge
        score = results['combined_score']
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Overall Quality Score", f"{score:.1%}")
        with col2:
            grade = self._score_to_grade(score)
            st.metric("Quality Grade", grade)
        with col3:
            status = "✅ Good" if score > 0.7 else "⚠️ Needs Review"
            st.metric("Status", status)
        
        # Show recommendations
        if results['recommendations']:
            with st.expander("🔧 Recommendations", expanded=True):
                for rec in results['recommendations'][:5]:
                    st.write(f"• {rec}")
        
        # Show advanced metrics if available
        if results['advanced_checks'] and 'error' not in results['advanced_checks']:
            with st.expander("📈 Advanced Quality Metrics"):
                adv = results['advanced_checks']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Passed Checks", adv.get('passed_checks', 0))
                with col2:
                    st.metric("Failed Checks", adv.get('failed_checks', 0))
                with col3:
                    st.metric("Critical Issues", len(adv.get('critical_issues', [])))
    
    def _score_to_grade(self, score: float) -> str:
        if score >= 0.95: return 'A+'
        if score >= 0.9: return 'A'
        if score >= 0.85: return 'B+'
        if score >= 0.8: return 'B'
        if score >= 0.75: return 'C+'
        if score >= 0.7: return 'C'
        if score >= 0.6: return 'D'
        return 'F'