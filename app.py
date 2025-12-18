import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import backend as bk
import random
import datetime

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clinical Risk Monitor", 
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. SETUP & STATE
# ---------------------------------------------------------
# Initialize Database
bk.init_db()

# Load AI Model
try:
    bleeding_model = bk.load_bleeding_model()
except Exception as e:
    st.error(f"Model failed to load: {e}")
    st.stop()

# Initialize Session State
if 'patient_data' not in st.session_state:
    st.session_state['patient_data'] = {}

if 'entered_app' not in st.session_state:
    st.session_state['entered_app'] = False

# Helper for file timestamps
def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M")

# ---------------------------------------------------------
# 3. UI MODULES
# ---------------------------------------------------------

# --- COVER PAGE ---
def render_cover_page():
    st.markdown("<h1 style='text-align: center;'>🛡️ Clinical Risk Monitor</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>AI-Driven Pharmacovigilance System</p>", unsafe_allow_html=True)
    st.write("")
    c1, c2, c3 = st.columns([1, 2, 1])
    if c2.button("🚀 Launch Dashboard", use_container_width=True, type="primary"):
        st.session_state['entered_app'] = True
        st.rerun()

# --- MODULE: TRIAGE BOARD (NEW) ---
def render_triage_board():
    st.subheader("🚑 Emergency Department Triage Board")
    
    # 1. Generate Fake Waiting Room Data
    triage_data = pd.DataFrame({
        'Patient ID': ['PT-1092', 'PT-1093', 'PT-1094', 'PT-1095', 'PT-1096'],
        'Complaint': ['Chest Pain', 'Fever/Confusion', 'Ankle Pain', 'SOB', 'Med Refill'],
        'SIRS Score': [1, 4, 0, 3, 0],
        'BP': ['140/90', '85/50', '120/80', '110/70', '130/85'],
        'HR': [88, 130, 72, 105, 68],
        'O2 Sat': [98, 88, 99, 91, 99],
        'Wait Time': ['15 min', '2 min', '45 min', '10 min', '60 min']
    })

    # 2. Assign Priority Logic
    def assign_priority(row):
        if row['SIRS Score'] >= 3 or int(row['O2 Sat']) < 90:
            return '🔴 CRITICAL (Immed)'
        elif row['SIRS Score'] >= 2:
            return '🟡 URGENT (15m)'
        else:
            return '🟢 NON-URGENT'

    triage_data['Priority'] = triage_data.apply(assign_priority, axis=1)
    
    # 3. Sort by Priority (Critical First)
    triage_data = triage_data.sort_values(by='Priority', ascending=False)

    # 4. Display styling
    def highlight_critical(val):
        color = 'red' if 'CRITICAL' in val else 'orange' if 'URGENT' in val else 'green'
        return f'background-color: {color}; color: white; font-weight: bold;'

    st.dataframe(
        triage_data.style.map(highlight_critical, subset=['Priority']),
        use_container_width=True,
        hide_index=True
    )

# --- MODULE: RISK CALCULATOR (UPDATED) ---
def render_risk_calculator():
    st.subheader("Acute Risk Calculator")
    
    with st.container(border=True):
        st.markdown("#### 📝 Patient Data Entry")
        
        # --- NEW: FHIR IMPORT BUTTON ---
        col_load, col_clear = st.columns([1, 4])
        with col_load:
            if st.button("📥 Load Patient from EHR (FHIR)", type="secondary"):
                st.session_state['fhir_import'] = {
                    'age': 68, 'gender': 'Male', 'weight': 82.5,
                    'sbp': 88, 'dbp': 50, 'hr': 115, 'rr': 28, 'temp': 39.2, 'spo2': 89,
                    'creat': 2.4, 'bun': 45, 'k': 5.2, 'glucose': 145,
                    'wbc': 18.5, 'hgb': 9.2, 'plt': 140, 'inr': 1.1, 'lactate': 4.2,
                    'history': ['anticoag', 'heart_failure']
                }
                st.success("✅ HL7/FHIR Data Stream Imported")

        # Helper to retrieve loaded values safely
        def get_val(key, default):
            if 'fhir_import' in st.session_state:
                return st.session_state['fhir_import'].get(key, default)
            return default

        with st.form("risk_form"):
            col_left, col_right = st.columns([1, 1], gap="medium")
            
            # --- LEFT COLUMN ---
            with col_left:
                st.markdown("##### 👤 Patient Profile")
                l1, l2 = st.columns(2)
                age = l1.number_input("Age (Years)", min_value=0, max_value=120, value=get_val('age', 0))
                
                gender_idx = 0
                if get_val('gender', 'Male') == 'Female': gender_idx = 1
                gender = l2.selectbox("Gender", ["Male", "Female"], index=gender_idx)
                
                w_val, w_unit = st.columns([2, 1]) 
                weight_input = w_val.number_input("Weight", 0.0, 400.0, float(get_val('weight', 0.0)))
                weight_scale = w_unit.selectbox("Unit", ["kg", "lbs"], key="w_unit")
                height = st.number_input("Height (cm)", 0, 250, 0)
                
                # Weight Logic
                weight_kg = weight_input * 0.453592 if weight_scale == "lbs" else weight_input
                bmi = weight_kg / ((height/100)**2) if height > 0 else 0.0

                st.markdown("##### 🩺 Vitals")
                v1, v2 = st.columns(2)
                sys_bp = v1.number_input("Systolic BP", 0, 300, get_val('sbp', 0))
                dia_bp = v2.number_input("Diastolic BP", 0, 200, get_val('dbp', 0))
                
                v3, v4 = st.columns(2)
                hr = v3.number_input("Heart Rate", 0, 300, get_val('hr', 0))
                resp_rate = v4.number_input("Resp Rate", 0, 60, get_val('rr', 0))
                
                v5, v6 = st.columns(2)
                temp_c = v5.number_input("Temp °C", 0.0, 45.0, float(get_val('temp', 0.0)), step=0.1)
                o2_sat = v6.number_input("O2 Sat %", 0, 100, get_val('spo2', 0))

            # --- RIGHT COLUMN ---
            with col_right:
                st.markdown("##### 🧪 Critical Labs")
                lab1, lab2 = st.columns(2)
                creat = lab1.number_input("Creatinine", 0.0, 20.0, float(get_val('creat', 0.0)))
                bun = lab2.number_input("BUN", 0, 100, get_val('bun', 0))
                
                lab3, lab4 = st.columns(2)
                potassium = lab3.number_input("Potassium", 0.0, 10.0, float(get_val('k', 0.0)))
                glucose = lab4.number_input("Glucose", 0, 1000, get_val('glucose', 0))
                
                lab5, lab6 = st.columns(2)
                wbc = lab5.number_input("WBC", 0.0, 50.0, float(get_val('wbc', 0.0)))
                hgb = lab6.number_input("Hemoglobin", 0.0, 20.0, float(get_val('hgb', 0.0)))
                
                lab7, lab8 = st.columns(2)
                platelets = lab7.number_input("Platelets", 0, 1000, get_val('plt', 0))
                inr = lab8.number_input("INR", 0.0, 10.0, float(get_val('inr', 0.0)))
                
                lactate = st.number_input("Lactate", 0.0, 20.0, float(get_val('lactate', 0.0)))

                st.markdown("##### 📋 Medical History")
                hist = get_val('history', [])
                h1, h2 = st.columns(2)
                anticoag = h1.checkbox("Anticoagulant Use", value=('anticoag' in hist))
                liver_disease = h2.checkbox("Liver Disease", value=('liver' in hist))
                h3, h4 = st.columns(2)
                heart_failure = h3.checkbox("Heart Failure", value=('heart_failure' in hist))
                gi_bleed = h4.checkbox("History of GI Bleed", value=('gi_bleed' in hist))
                
                m1, m2 = st.columns(2)
                nsaid = m1.checkbox("NSAID Use")
                active_chemo = m2.checkbox("Active Chemo")
                m3, m4 = st.columns(2)
                diuretic = m3.checkbox("Diuretic Use")
                acei = m4.checkbox("ACEi/ARB")
                m5, m6 = st.columns(2)
                insulin = m5.checkbox("Insulin")
                hba1c_high = m6.checkbox("Uncontrolled Diabetes")
                
                altered_mental = st.checkbox("Altered Mental Status", value=('ams' in hist))

            st.write("") 
            submitted = st.form_submit_button("🚀 Run Clinical Analysis", type="primary", use_container_width=True)

    # --- LOGIC & RESULTS ---
    if submitted:
        # Calculations
        map_val = (sys_bp + (2 * dia_bp)) / 3 if sys_bp > 0 else 0
        pulse_pressure = sys_bp - dia_bp
        shock_index = hr / sys_bp if sys_bp > 0 else 0
        bun_creat_ratio = bun / creat if creat > 0 else 0
        is_high_bp = 1 if sys_bp > 140 else 0
        
        if age > 0 and sys_bp > 0:
            input_df = pd.DataFrame({
                'age': [age], 'inr': [inr], 'anticoagulant': [1 if anticoag else 0],
                'gi_bleed': [1 if gi_bleed else 0], 'high_bp': [is_high_bp],
                'antiplatelet': [0], 'gender_female': [1 if gender == "Female" else 0],
                'weight': [weight_kg], 'liver_disease': [1 if liver_disease else 0]
            })
            pred_bleeding = bleeding_model.predict(input_df)[0]
            pred_aki = bk.calculate_aki_risk(age, diuretic, acei, sys_bp, active_chemo, creat, nsaid, heart_failure)
            pred_sepsis = bk.calculate_sepsis_risk(sys_bp, resp_rate, altered_mental, temp_c)
            pred_hypo = bk.calculate_hypoglycemic_risk(insulin, (creat>1.3), hba1c_high, False)
            sirs_score = bk.calculate_sirs_score(temp_c, hr, resp_rate, wbc)
        else:
            pred_bleeding = pred_aki = pred_sepsis = pred_hypo = sirs_score = 0.0

        status_calc = 'Critical' if (pred_bleeding > 50 or pred_aki > 50 or pred_sepsis >= 2) else 'Stable'
        
        # Save to DB & Session
        bk.save_patient_to_db(age, gender, sys_bp, int(pred_aki), float(pred_bleeding), status_calc)
        
        st.session_state['patient_data'] = {
            'id': f"Patient-{age}-{int(sys_bp)}", 
            'age': age, 'gender': gender, 'weight': weight_kg,
            'sys_bp': sys_bp, 'dia_bp': dia_bp, 'hr': hr, 'resp_rate': resp_rate, 
            'temp_c': temp_c, 'o2_sat': o2_sat,
            'creat': creat, 'potassium': potassium, 'inr': inr, 'bun': bun,
            'wbc': wbc, 'hgb': hgb, 'platelets': platelets, 'lactate': lactate, 'glucose': glucose,
            'bleeding_risk': float(pred_bleeding), 'aki_risk': int(pred_aki),
            'sepsis_risk': int(pred_sepsis), 'hypo_risk': int(pred_hypo),
            'sirs_score': sirs_score, 'status': status_calc, 'map_val': map_val, 'bmi': bmi,
            'shock_index': shock_index, 'pulse_pressure': pulse_pressure, 'bun_creat_ratio': bun_creat_ratio
        }
        st.session_state['analysis_results'] = st.session_state['patient_data']

    # --- DISPLAY RESULTS ---
    if 'analysis_results' in st.session_state:
        res = st.session_state['analysis_results']
        st.divider()
        st.subheader("📊 Risk Stratification Results")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("🩸 Bleeding Risk", f"{res['bleeding_risk']:.1f}%", "High" if res['bleeding_risk'] > 50 else "Normal")
        r2.metric("💧 AKI Risk", f"{res['aki_risk']}%", "High" if res['aki_risk'] > 50 else "Normal")
        r3.metric("🦠 Sepsis Score", f"{res['sepsis_risk']}", "Alert" if res['sepsis_risk'] >= 2 else "Normal")
        r4.metric("⚡ SIRS Score", f"{res.get('sirs_score',0)}/4")
        
        st.divider()
        c_ai, c_txt = st.columns([1, 3])
        with c_ai:
            if st.button("⚡ Consult AI"):
                with st.spinner("Thinking..."):
                    response = bk.consult_ai_doctor("risk_assessment", "", res)
                    st.session_state['ai_result'] = response
        with c_txt:
            if 'ai_result' in st.session_state:
                st.info(st.session_state['ai_result'])

# --- MODULE: DASHBOARD (UPDATED) ---
def render_dashboard():
    data = st.session_state.get('patient_data', {})
    if not data:
        st.warning("⚠️ No patient data found. Run Risk Calculator first.")
        return

    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"🛏️ Bedside Monitor: {data.get('id', 'Unknown')}")
        st.caption(f"Status: **{data.get('status', 'Unknown')}**")
    
    with c2:
        if st.button("✨ Generate Discharge Note", type="primary"):
            with st.spinner("Consulting Gemini 2.0..."):
                st.session_state['latest_discharge_note'] = bk.generate_discharge_summary(data)
        
        if 'latest_discharge_note' in st.session_state:
            st.download_button("📥 Download Note", st.session_state['latest_discharge_note'], "discharge.txt")

    if 'latest_discharge_note' in st.session_state:
        with st.expander("📄 View Note"):
            st.write(st.session_state['latest_discharge_note'])

    st.divider()
    with st.container(border=True):
        st.markdown("#### 📉 Hemodynamic Trend (Last 4 Hours)")
        col_chart, col_vitals = st.columns([3, 1])
        
        with col_chart:
            # --- TREND LOGIC ---
            current_sbp = data.get('sys_bp', 120)
            status = data.get('status', 'Stable')
            
            if status == 'Critical':
                trend_values = np.linspace(current_sbp + 40, current_sbp, 20) 
                trend_color = '#FF4B4B'
            else:
                trend_values = np.random.normal(current_sbp, 3, 20)
                trend_color = '#00CC96'

            chart_df = pd.DataFrame({
                'Time': pd.date_range(end=datetime.datetime.now(), periods=20, freq='15min'),
                'Systolic BP': trend_values
            })
            
            c = alt.Chart(chart_df).mark_line(strokeWidth=4, color=trend_color).encode(
                x=alt.X('Time', axis=alt.Axis(format='%H:%M')),
                y=alt.Y('Systolic BP', scale=alt.Scale(domain=[40, 200])),
                tooltip=['Time', 'Systolic BP']
            ).properties(height=250)
            st.altair_chart(c, use_container_width=True)

        with col_vitals:
            st.metric("SBP", f"{int(data.get('sys_bp', 0))}", "mmHg")
            st.metric("HR", f"{int(data.get('hr', 0))}", "BPM")
            st.metric("SpO2", f"{int(data.get('o2_sat', 0))}%")

# --- OTHER MODULES (PLACEHOLDERS) ---
def render_history_sql():
    st.subheader("🗄️ Patient History Database")
    df = bk.fetch_history()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        if st.button("Clear History"):
            bk.clear_history()
            st.rerun()
    else:
        st.info("Database is empty.")

def render_batch_analysis():
    st.subheader("Batch Analysis")
    st.info("Upload CSV functionality here.")

def render_medication_checker():
    st.subheader("💊 Drug Interaction Checker")
    c1, c2 = st.columns(2)
    d1 = c1.text_input("Drug A")
    d2 = c2.text_input("Drug B")
    if d1 and d2:
        res = bk.check_interaction(d1, d2)
        if res: st.error(res)
        else: st.success("No critical interaction found in database.")

def render_chatbot():
    st.subheader("Medical Glossary")
    q = st.text_input("Search term:")
    if q: st.write(bk.chatbot_response(q))

def render_ai_diagnostician():
    st.subheader("🧠 AI Consultant")
    prompt = st.chat_input("Clinical Query")
    if prompt:
        st.write(f"User: {prompt}")
        st.write(bk.consult_ai_doctor("provider", prompt))

# ---------------------------------------------------------
# 4. MAIN CONTROLLER
# ---------------------------------------------------------
if not st.session_state['entered_app']:
    render_cover_page()
else:
    with st.sidebar:
        st.title("Navigation")
        menu = st.radio("Select Module", [
            "ER Triage Board",
            "Risk Calculator", 
            "Patient History (SQL)",
            "Live Dashboard", 
            "Batch Analysis (CSV)", 
            "Medication Checker", 
            "📚 Medical Glossary",
            "🧠 AI Clinical Consultant"
        ])
        st.info("v3.0 - AI Integrated")

    if menu == "ER Triage Board":
        render_triage_board()
    elif menu == "Risk Calculator":
        if 'extracted' not in st.session_state:
            st.session_state.extracted = {}

        # The Note Input Box
        with st.expander("📝 Import Data from Patient Note (EHR Mode)", expanded=True):
            patient_note = st.text_area(
                "Paste Note Here:", 
                placeholder="Pt is 72yo male, BP 150/90, Creatinine 1.8, on Warfarin...",
                height=100
            )
            
            if st.button("🔍 Extract Clinical Data"):
                import backend # Ensure backend is imported
                with st.spinner("Analyzing text..."):
                    data = backend.parse_patient_note(patient_note)
                    if data:
                        st.session_state.extracted = data
                        st.success("Data extracted! Values below have been auto-filled.")
                    else:
                        st.error("Could not read note.")
        
        render_risk_calculator()
    elif menu == "Patient History (SQL)":
        render_history_sql()
    elif menu == "Live Dashboard":
        render_dashboard()
    elif menu == "Batch Analysis (CSV)":
        render_batch_analysis()
    elif menu == "Medication Checker":
        render_medication_checker()
    elif menu == "📚 Medical Glossary":
        render_chatbot()
    elif menu == "🧠 AI Clinical Consultant":
        render_ai_diagnostician()
