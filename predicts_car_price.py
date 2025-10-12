import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor

# ===== Load JSON =====
data = pd.read_json("result.json")
df = pd.DataFrame(data["result"]["Listings"])
df["brand"] = data["result"]["Brand"]

# ===== Clean numeric =====
df["price"] = df["price"].str.replace(r"[^0-9]", "", regex=True).replace("", np.nan).astype(float)
df["mileage"] = df["mileage"].str.replace(r"[^0-9]", "", regex=True).replace("", np.nan).astype(float)
df["year"] = pd.to_numeric(df["year"], errors="coerce")

# Drop rows with missing critical values
df = df.dropna(subset=["price", "year", "mileage", "model", "brand"]).reset_index(drop=True)

# ===== Features & target =====
X = df[["year", "mileage", "brand", "model", "fuel", "transmission"]]
y = df["price"]

# ===== Preprocessor =====
categorical = ["brand", "model", "fuel", "transmission"]
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
def predict_price(brand, model_name, year, mileage, fuel="Gas", transmission="Automatic"):
    input_df = pd.DataFrame([{
        "brand": brand,
        "model": model_name,
        "year": year,
        "mileage": mileage,
        "fuel": fuel,
        "transmission": transmission
    }])
    return model.predict(input_df)[0]

# ===== Example usage =====
if __name__ == "__main__":
    pred = predict_price("MINI", "Countryman", 2022, 160000, "Gas", "Automatic")
    print(f"Predicted fair price: ${pred:,.0f}")
