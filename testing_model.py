# compare_rf_lgb.py
import json
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# Try import LightGBM
try:
    from lightgbm import LGBMRegressor
    LGB_AVAILABLE = True
except Exception:
    LGB_AVAILABLE = False

# ---- Load data ----
with open("result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data.get("listings", []))
df["brand"] = df.get("brand") or data.get("brand") or "unknown"

# ---- Cleaning / features ----
df["price"] = pd.to_numeric(df.get("price"), errors="coerce")
df["mileage"] = pd.to_numeric(df.get("mileage_km"), errors="coerce")
df["year"] = pd.to_numeric(df.get("year"), errors="coerce")
df = df[df["price"].notna()].reset_index(drop=True)

current_year = datetime.now().year
df["age"] = (current_year - df["year"]).clip(lower=0)
df["price_per_km"] = np.where(df["mileage"].fillna(0) > 0, df["price"] / df["mileage"].replace({0: np.nan}), np.nan)

for col in ["model", "brand", "fuel", "transmission", "deal_tag", "province_city", "title"]:
    if col not in df.columns:
        df[col] = "Unknown"
    else:
        df[col] = df[col].fillna("Unknown").astype(str)

# reduce cardinality on model
TOPK_MODEL = 40
top_models = df["model"].value_counts().nlargest(TOPK_MODEL).index
df["model_reduced"] = df["model"].where(df["model"].isin(top_models), other="Other")

feature_cols = ["age", "mileage", "price_per_km", "brand", "model_reduced", "fuel", "transmission", "deal_tag", "province_city"]
X = df[feature_cols].copy()
y = df["price"].copy()

# ---- Split once for fair comparison ----
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=RANDOM_SEED)

# ---- Preprocessor ----
numeric_cols = ["age", "mileage", "price_per_km"]
categorical_cols = ["brand", "model_reduced", "fuel", "transmission", "deal_tag", "province_city"]

numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

# OneHotEncoder compatibility
try:
    ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
except TypeError:
    try:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)
    except TypeError:
        ohe = OneHotEncoder(handle_unknown="ignore")

categorical_transformer = Pipeline(steps=[("ohe", ohe)])

preprocessor = ColumnTransformer(transformers=[
    ("num", numeric_transformer, numeric_cols),
    ("cat", categorical_transformer, categorical_cols),
], remainder="drop")

# ---- Helper to run CV search and evaluate ----
def run_search_and_eval(pipeline, param_dist, X_train, y_train, X_test, y_test, n_iter=6, model_name="model"):
    rs = RandomizedSearchCV(pipeline, param_distributions=param_dist, n_iter=n_iter, cv=3,
                            scoring="neg_mean_squared_error", random_state=RANDOM_SEED, n_jobs=4, verbose=1)
    rs.fit(X_train, y_train)
    best = rs.best_estimator_
    y_pred_test = best.predict(X_test)
    y_pred_train = best.predict(X_train)
    mae = mean_absolute_error(y_test, y_pred_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    print(f"\n=== {model_name} Results ===")
    print("Best params:", rs.best_params_)
    print(f"Train RMSE: {train_rmse:.2f}")
    print(f"Test  MAE:  {mae:.2f}")
    print(f"Test  RMSE: {rmse:.2f}")

    # top outliers
    residuals = (y_test - y_pred_test).abs()
    outliers = pd.DataFrame({
        "title": df.loc[y_test.index, "title"] if "title" in df.columns else None,
        "true": y_test,
        "pred": y_pred_test,
        "error": residuals
    }).sort_values("error", ascending=False).head(10)
    print("\nTop 10 absolute errors:")
    print(outliers.to_string(index=False))
    return best, mae, rmse

# ---- Random Forest pipeline + TTR (log target) ----
rf = RandomForestRegressor(n_estimators=300, random_state=RANDOM_SEED, n_jobs=-1)
rf_pipe = Pipeline([("preprocessor", preprocessor), ("regressor", rf)])
ttr_rf = TransformedTargetRegressor(regressor=rf_pipe, func=np.log1p, inverse_func=np.expm1)

rf_param_dist = {
    "regressor__regressor__n_estimators": [200, 400],
    "regressor__regressor__max_depth": [None, 10, 20],
    "regressor__regressor__min_samples_leaf": [1, 3, 5],
    "regressor__regressor__max_features": ["sqrt", 0.5]
}

best_rf, rf_mae, rf_rmse = run_search_and_eval(ttr_rf, rf_param_dist, X_train, y_train, X_test, y_test, n_iter=6, model_name="RandomForest")

# ---- LightGBM pipeline + TTR (log target) ----
if LGB_AVAILABLE:
    lgb = LGBMRegressor(random_state=RANDOM_SEED, n_jobs=-1)
    lgb_pipe = Pipeline([("preprocessor", preprocessor), ("regressor", lgb)])
    ttr_lgb = TransformedTargetRegressor(regressor=lgb_pipe, func=np.log1p, inverse_func=np.expm1)

    lgb_param_dist = {
        "regressor__regressor__num_leaves": [31, 63, 127],
        "regressor__regressor__learning_rate": [0.01, 0.03, 0.05],
        "regressor__regressor__n_estimators": [200, 500, 1000],
        "regressor__regressor__min_child_samples": [5, 10, 20]
    }

    best_lgb, lgb_mae, lgb_rmse = run_search_and_eval(ttr_lgb, lgb_param_dist, X_train, y_train, X_test, y_test, n_iter=8, model_name="LightGBM")
else:
    best_lgb = None
    lgb_mae = lgb_rmse = None
    print("\nLightGBM not available (install with `pip install lightgbm`) — skipping LGB comparison.")

# ---- Summary comparison ----
print("\n=== Summary Comparison ===")
rows = []
rows.append(("RandomForest", rf_mae, rf_rmse))
if LGB_AVAILABLE:
    rows.append(("LightGBM", lgb_mae, lgb_rmse))
summary = pd.DataFrame(rows, columns=["Model", "MAE", "RMSE"])
print(summary.to_string(index=False))
