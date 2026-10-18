from sklearn.datasets import load_wine
from sklearn.ensemble import RandomForestClassifier
import pickle

X, y = load_wine(return_X_y=True)

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)

with open("model/model.pkl", "wb") as f:
    pickle.dump(model, f)

print("Wine dataset model trained and saved to model/model.pkl")
