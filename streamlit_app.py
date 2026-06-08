import streamlit as st
from app import RCBeamVerifier

# Set page title and layout
st.set_page_config(page_title="IS 456 Verifier", layout="centered")
st.title("Automated IS 456 Design Verifier")

# Sidebar for user inputs
with st.sidebar:
    st.header("Design Parameters")
    b = st.number_input("Width (b) [mm]", value=230.0, min_value=100.0, max_value=1000.0)
    d = st.number_input("Effective Depth (d) [mm]", value=450.0, min_value=100.0, max_value=1500.0)
    f_ck = st.number_input("Concrete Grade (f_ck) [MPa]", value=25.0, min_value=15.0, max_value=60.0)
    f_y = st.selectbox("Steel Grade (f_y) [MPa]", options=[250, 415, 500], index=1)
    A_st = st.number_input("Tension Steel Area (A_st) [mm²]", value=1000.0, min_value=50.0, max_value=10000.0)
    
    st.divider()
    M_u_applied = st.number_input("Applied Factored Moment [kNm]", value=120.0, min_value=1.0, max_value=1000.0)

# Create an instance of your refactored backend
verifier = RCBeamVerifier(b, d, f_ck, f_y, A_st)

# Calculate neutral axes and capacity natively in mm/kNm
x_max = verifier.limiting_neutral_axis()
x_u = (0.87 * f_y * A_st) / (0.36 * f_ck * b)
M_ur = verifier.ultimate_moment_capacity()
verification_status = verifier.verify_design(M_u_applied)

# Layout for Structural Analysis Results
st.subheader("Structural Analysis")
col1, col2, col3 = st.columns(3)

col1.metric("Limiting NA ($x_{max}$)", f"{x_max:.2f} mm")
col2.metric("Actual NA ($x_u$)", f"{x_u:.2f} mm")
col3.metric("Capacity ($M_{ur}$)", f"{M_ur:.2f} kNm")

st.divider()
# Verification Logic Display
st.subheader("Compliance Status")
if "SAFE" in verification_status:
    st.success(verification_status)
else:
    st.error(verification_status)
