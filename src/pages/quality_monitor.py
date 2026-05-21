# src/pages/quality_monitor.py
import streamlit as st
import pandas as pd
from datetime import datetime

def render_quality_monitor():
    st.markdown('<div class="pamoja-hero"><h1>🔍 Quality Monitoring Dashboard</h1><p>Monitor data quality across all your datasets</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Engine Status")
        try:
            from src.quality_engine.pamojadata_client import PamojaDataQualityClient
            quality_client = PamojaDataQualityClient()
            
            if quality_client.enabled:
                st.success("✅ Quality Engine Connected")
                st.caption(f"Endpoint: {quality_client.api_url}")
            else:
                st.warning("⚠️ Quality Engine Not Connected")
                if st.button("Retry Connection"):
                    st.cache_resource.clear()
                    st.rerun()
        except Exception as e:
            st.error(f"Engine error: {e}")
    
    with col2:
        st.subheader("📈 Quality History")
        if 'quality_history' in st.session_state and st.session_state.quality_history:
            history_df = pd.DataFrame(st.session_state.quality_history)
            st.line_chart(history_df.set_index('timestamp')['quality_score'])
        else:
            st.info("No quality history yet. Upload data to start tracking.")
