import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor

# ===== Load JSON =====
with open("result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract listings into DataFrame
df = pd.DataFrame(data["listings"])
df["brand"] = data["brand"]  # add brand column from metadata

# ===== Clean numeric =====
df["price"] = pd.to_numeric(df["price"], errors="coerce")
df["mileage"] = pd.to_numeric(df["mileage_km"], errors="coerce")
df["year"] = pd.to_numeric(df["year"], errors="coerce")

# ===== Handle missing categorical =====
for col in ["model", "brand", "fuel", "transmission", "deal_tag", "province_city"]:
    if col not in df.columns:
        df[col] = "Unknown"
    else:
        df[col] = df[col].fillna("Unknown")

# ===== Drop rows only if critical numeric missing =====
df = df.dropna(subset=["price", "year", "mileage"]).reset_index(drop=True)

# ===== Features & target =====
X = df[["year", "mileage", "brand", "model", "fuel", "transmission", "deal_tag", "province_city"]]
y = df["price"]

# ===== Preprocessor =====
categorical = ["brand", "model", "fuel", "transmission", "deal_tag", "province_city"]
numeric = ["year", "mileage"]

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", StandardScaler(), numeric),
    ]
)

# ===== Train Random Forest on full dataset =====
model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=200, random_state=42)),
    ]
)
model.fit(X, y)

# ===== Prediction function =====
def predict_price(brand, model_name, year, mileage, fuel="Gas", transmission="Automatic", province_city="Unknown"):
    input_df = pd.DataFrame([{
        "brand": brand if brand else "Unknown",
        "model": model_name if model_name else "Unknown",
        "year": year,
        "mileage": mileage,
        "fuel": fuel if fuel else "Unknown",
        "transmission": transmission if transmission else "Unknown",
        "deal_tag": "Unknown",          # always Unknown at inference
        "province_city": province_city if province_city else "Unknown"
    }])
    return model.predict(input_df)[0]

# ===== Example usage =====
if __name__ == "__main__":
    pred = predict_price("mini", "countryman", 2022, 160000, "Gas", "Automatic", "Saskatoon")
    print(f"Predicted fair price: ${pred:,.0f}")
