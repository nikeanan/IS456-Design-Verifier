# IS 456 Automated Structural Design Verifier

A professional-grade structural engineering tool developed for the Smart India Hackathon. This application automates the verification of singly and doubly reinforced RC beams according to the IS 456:2000 code.

## 🏗️ Key Features
- **Real-time Structural Physics:** Instant calculation of Neutral Axis ($x_u$) vs. Limiting Neutral Axis ($x_{max}$).
- **Automated Design:** Intelligent "Doubly Reinforced Design Protocol" that computes required top and bottom steel for over-reinforced failures.
- **Dynamic Visualization:** Live `matplotlib` cross-section plots showing the compression zone and reinforcement layout.
- **Enterprise Ready:** Batch processing of structural data via CSV upload.
- **Material Science Integration:** Predicts concrete strength ($f_{ck}$) using mix design parameters.
- **Reporting:** Automated generation of professional PDF structural reports.

## 🛠️ Tech Stack
- **Framework:** Streamlit
- **Engineering Logic:** Python (NumPy/Pandas)
- **Visualization:** Matplotlib
- **Documentation:** FPDF2

## 🚀 Deployment
This project is engineered to be deployed on Streamlit Community Cloud, enabling live structural verification from any device.
