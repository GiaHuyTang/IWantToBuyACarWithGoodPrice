import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from tensorflow import keras
from sklearn.metrics import root_mean_squared_error
from tensorflow.keras import layers
import matplotlib.pyplot as plt

# ===== Load JSON =====
data = pd.read_json("result.json")

# Extract listings and brand
df = pd.DataFrame(data["result"]["Listings"])
brand_name = data["result"]["Brand"]
df["brand"] = brand_name

# ===== Clean numeric =====
df["price"] = (
    df["price"].str.replace(r"[^0-9]", "", regex=True).replace("", np.nan).astype(float)
)
df["mileage"] = (
    df["mileage"].str.replace(r"[^0-9]", "", regex=True).replace("", np.nan).astype(float)
)
df["year"] = pd.to_numeric(df["year"], errors="coerce")

# Drop rows with missing critical values
df = df.dropna(subset=["price", "year", "mileage", "model", "brand"]).reset_index(drop=True)

# ===== Features & target =====
X = df[["year", "mileage", "brand", "model", "fuel", "transmission"]]
y = df["price"]

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ===== Preprocessor =====
categorical = ["brand", "model", "fuel", "transmission"]
numeric = ["year", "mileage"]

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", StandardScaler(), numeric),
    ]
)

# ===== Random Forest =====
model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=200, random_state=42)),
    ]
)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

print("MAE: ", mean_absolute_error(y_test, y_pred))
print("RMSE: ", root_mean_squared_error(y_test, y_pred))

# Dont need to tune for now (data is small and no change expected)

# # ===== Tuning Model =====
# param_grid = {
#     "regressor__n_estimators": [100, 200],
#     "regressor__max_depth": [None, 5, 10],
#     "regressor__min_samples_split": [2, 5],
# }

# grid = GridSearchCV(
#     Pipeline([
#         ("preprocessor", preprocessor),
#         ("regressor", RandomForestRegressor(random_state=42)),
#     ]),
#     param_grid,
#     scoring="neg_mean_squared_error",
#     cv=5,   # using KFold CV with 5 folds
#     n_jobs=-1
# )

# grid.fit(X_train, y_train)

# print("Best Params:", grid.best_params_)
# print("Best CV Score (RMSE):", np.sqrt(-grid.best_score_))

# best_model = grid.best_estimator_
# y_pred_tuned = best_model.predict(X_test)
# print("Tuned MAE: ", mean_absolute_error(y_test, y_pred_tuned))
# print("Tuned RMSE: ", root_mean_squared_error(y_test, y_pred_tuned))

# # ===== Linear Regression =====
# linreg = Pipeline(
#     steps=[("preprocessor", preprocessor), ("regressor", LinearRegression())]
# )
# linreg.fit(X_train, y_train)
# y_pred_lin = linreg.predict(X_test)

# # ===== Neural Network (MLP) =====
# # Encode features once for NN
# X_train_enc = preprocessor.fit_transform(X_train)
# X_test_enc = preprocessor.transform(X_test)
# input_dim = X_train_enc.shape[1]

# nn = keras.Sequential(
#     [
#         layers.Input(shape=(input_dim,)),
#         layers.Dense(128, activation="relu"),
#         layers.Dropout(0.2),
#         layers.Dense(64, activation="relu"),
#         layers.Dropout(0.2),
#         layers.Dense(1),
#     ]
# )

# nn.compile(optimizer="adam", loss="mse", metrics=["mae"])
# nn.fit(
#     X_train_enc,
#     y_train,
#     validation_split=0.2,
#     epochs=20,
#     batch_size=256,
#     verbose=1,
# )

# y_pred_nn = nn.predict(X_test_enc).ravel()

# # ===== Evaluate (compatible with all sklearn versions) =====
# def evaluate(name, y_true, y_pred):
#     mae = mean_absolute_error(y_true, y_pred)
#     try:
#         rmse = root_mean_squared_error(y_true, y_pred)
#     except TypeError:
#         rmse = np.sqrt(mean_squared_error(y_true, y_pred))
#     print(f"{name}: MAE={mae:.2f}, RMSE={rmse:.2f}")
#     return mae, rmse

# results = {}
# results["Linear Regression"] = evaluate("Linear Regression", y_test, y_pred_lin)
# results["Random Forest"] = evaluate("Random Forest", y_test, y_pred_rf)
# results["Neural Network"] = evaluate("Neural Network", y_test, y_pred_nn)

# # ===== Show comparison as DataFrame =====
# results_df = pd.DataFrame([
#     {"Model": model, "MAE": mae, "RMSE": rmse}
#     for model, (mae, rmse) in results.items()
# ])

# print("\nModel Performance Comparison:")
# print(results_df.to_string(index=False))

