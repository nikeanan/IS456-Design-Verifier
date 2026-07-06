"""
ml/train_model.py
=================
Trains a GradientBoostingRegressor on a synthetic but physically-plausible
concrete mix-design dataset and persists the model as concrete_predictor.pkl.

Features (X):
    cement      — kg/m³   [250–500]
    water       — kg/m³   [140–210]
    fa          — kg/m³   (fine aggregate)
    ca          — kg/m³   (coarse aggregate)
    rfa_pct     — %       (recycled fine aggregate replacement 0–100)
    curing_days — days    [3, 7, 14, 28, 56]

Target (y):
    fck_28day   — MPa compressive strength at 28 days
"""

import numpy as np
import pickle
import os
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score

# ── Reproducibility ─────────────────────────────────────────────────────────
RNG = np.random.default_rng(42)
N   = 2000   # synthetic samples

# ── Physically-plausible data generation ────────────────────────────────────
cement      = RNG.uniform(250, 500, N)
wc_ratio    = RNG.uniform(0.35, 0.65, N)
water       = cement * wc_ratio
fa_frac     = RNG.uniform(0.30, 0.45, N)
ca_frac     = 1.0 - fa_frac
density     = 2400   # kg/m³ total mix
fa          = fa_frac * density
ca          = ca_frac * density
rfa_pct     = RNG.uniform(0, 100, N)
curing_days = RNG.choice([3, 7, 14, 28, 56], N)

# ── Strength model (empirical IS-456 inspired) ───────────────────────────────
# Base: Abrams law — f_ck ≈ k1 / (w/c)^k2
k1 = RNG.normal(25, 2, N)
k2 = RNG.normal(1.5, 0.1, N)
fck_base = k1 / (wc_ratio ** k2)

# Curing factor (log growth)
curing_factor = 0.5 + 0.5 * (np.log(curing_days) / np.log(28))

# RFA penalty: slight strength drop above 30% replacement
rfa_penalty = np.where(
    rfa_pct <= 30,
    1.0 + rfa_pct * 0.0005,            # marginal gain (finer packing)
    1.0 - ((rfa_pct - 30) / 100) * 0.18  # gradual reduction
)

fck_28 = fck_base * curing_factor * rfa_penalty + RNG.normal(0, 1.2, N)
fck_28 = np.clip(fck_28, 10, 80)

# ── Assemble dataset ─────────────────────────────────────────────────────────
X = np.column_stack([cement, water, fa, ca, rfa_pct, curing_days])
y = fck_28

FEATURE_NAMES = ["Cement (kg/m³)", "Water (kg/m³)", "Fine Agg. (kg/m³)",
                 "Coarse Agg. (kg/m³)", "RFA Replacement (%)", "Curing Days"]

# ── Train / test split ───────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

# ── Pipeline: StandardScaler + GBR ───────────────────────────────────────────
pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("gbr", GradientBoostingRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    ))
])

pipeline.fit(X_train, y_train)

# ── Evaluate ─────────────────────────────────────────────────────────────────
y_pred = pipeline.predict(X_test)
mae    = mean_absolute_error(y_test, y_pred)
r2     = r2_score(y_test, y_pred)

print(f"Training complete — MAE: {mae:.2f} MPa | R²: {r2:.4f}")
print(f"Feature importances (GBR):")
gbr = pipeline.named_steps["gbr"]
for name, imp in sorted(zip(FEATURE_NAMES, gbr.feature_importances_), key=lambda x: -x[1]):
    print(f"  {name:30s} {imp*100:.1f}%")

# ── Persist model + metadata ──────────────────────────────────────────────────
model_dir = os.path.dirname(__file__)
model_path = os.path.join(model_dir, "concrete_predictor.pkl")

model_bundle = {
    "pipeline":      pipeline,
    "feature_names": FEATURE_NAMES,
    "mae":           mae,
    "r2":            r2,
    "train_std":     float(np.std(y_train)),   # used for ±1σ CI in UI
}

with open(model_path, "wb") as f:
    pickle.dump(model_bundle, f)

print(f"\nModel saved → {model_path}")
