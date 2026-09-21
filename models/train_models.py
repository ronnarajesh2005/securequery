import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib

# Load the synthetic data
df = pd.read_csv("data/synthetic_risk_data.csv")

feature_cols = ["result_count", "distinct_sensitive_values", "query_granularity", "is_single_hospital"]
X = df[feature_cols]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- Random Forest ---
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)
rf_preds = rf.predict(X_test)

print("=== Random Forest ===")
print(f"Accuracy:  {accuracy_score(y_test, rf_preds):.4f}")
print(f"Precision: {precision_score(y_test, rf_preds):.4f}")
print(f"Recall:    {recall_score(y_test, rf_preds):.4f}")
print(f"F1 Score:  {f1_score(y_test, rf_preds):.4f}")
print("Feature importances:")
for name, importance in zip(feature_cols, rf.feature_importances_):
    print(f"  {name}: {importance:.4f}")

# --- Logistic Regression ---
lr = LogisticRegression(max_iter=1000)
lr.fit(X_train, y_train)
lr_preds = lr.predict(X_test)

print("\n=== Logistic Regression ===")
print(f"Accuracy:  {accuracy_score(y_test, lr_preds):.4f}")
print(f"Precision: {precision_score(y_test, lr_preds):.4f}")
print(f"Recall:    {recall_score(y_test, lr_preds):.4f}")
print(f"F1 Score:  {f1_score(y_test, lr_preds):.4f}")

# Save both models
joblib.dump(rf, "models/rf_model.joblib")
joblib.dump(lr, "models/lr_model.joblib")
print("\nModels saved to models/rf_model.joblib and models/lr_model.joblib")