import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from tensorflow import keras
from tensorflow.keras import layers

# ===== Load JSON =====
with open("result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract listings into DataFrame
df = pd.DataFrame(data["listings"])
df["brand"] = data["brand"]

# ===== Clean numeric =====
df["price"] = pd.to_numeric(df["price"], errors="coerce")
df["mileage"] = pd.to_numeric(df["mileage_km"], errors="coerce")
df["year"] = pd.to_numeric(df["year"], errors="coerce")

# ===== Handle missing categorical =====
for col in ["model", "brand", "fuel", "transmission", "deal_tag"]:
    if col not in df.columns:
        df[col] = "Unknown"
    else:
        df[col] = df[col].fillna("Unknown")

# ===== Drop rows only if critical numeric missing =====
df = df.dropna(subset=["price", "year", "mileage"]).reset_index(drop=True)

# ===== Features & target =====
X = df[["year", "mileage", "brand", "model", "fuel", "transmission", "deal_tag"]]
y = df["price"]

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ===== Preprocessor =====
categorical = ["brand", "model", "fuel", "transmission", "deal_tag"]
numeric = ["year", "mileage"]

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", StandardScaler(), numeric),
    ]
)

# ===== Random Forest =====
rf = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=200, random_state=42)),
    ]
)
rf.fit(X_train, y_train)
y_pred_rf = rf.predict(X_test)

# ===== Linear Regression =====
linreg = Pipeline(
    steps=[("preprocessor", preprocessor), ("regressor", LinearRegression())]
)
linreg.fit(X_train, y_train)
y_pred_lin = linreg.predict(X_test)

# ===== Neural Network (MLP) =====
# Encode features once for NN
X_train_enc = preprocessor.fit_transform(X_train)
X_test_enc = preprocessor.transform(X_test)
input_dim = X_train_enc.shape[1]

nn = keras.Sequential(
    [
        layers.Input(shape=(input_dim,)),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.2),
        layers.Dense(64, activation="relu"),
        layers.Dropout(0.2),
        layers.Dense(1),
    ]
)

nn.compile(optimizer="adam", loss="mse", metrics=["mae"])
nn.fit(
    X_train_enc,
    y_train,
    validation_split=0.2,
    epochs=20,
    batch_size=256,
    verbose=0,
)

y_pred_nn = nn.predict(X_test_enc).ravel()

# ===== Evaluate =====
def evaluate(name, y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"{name}: MAE={mae:.2f}, RMSE={rmse:.2f}")
    return mae, rmse

results = {}
results["Linear Regression"] = evaluate("Linear Regression", y_test, y_pred_lin)
results["Random Forest"] = evaluate("Random Forest", y_test, y_pred_rf)
results["Neural Network"] = evaluate("Neural Network", y_test, y_pred_nn)

# ===== Show comparison as DataFrame =====
results_df = pd.DataFrame([
    {"Model": model, "MAE": mae, "RMSE": rmse}
    for model, (mae, rmse) in results.items()
])

print("\nModel Performance Comparison:")
print(results_df.to_string(index=False))
