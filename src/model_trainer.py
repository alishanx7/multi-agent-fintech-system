import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

def train_risk_model():
    # Automatically get the absolute path of this script's directory (src/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Go one level up to the root, then into data/
    data_path = os.path.join(base_dir, '..', 'data', 'financial_data.csv')
    # Go one level up to the root, then into models/
    model_dir = os.path.join(base_dir, '..', 'models')
    model_path = os.path.join(model_dir, 'risk_model.pkl')
    
    # Ensure folders exist
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)
    
    # If the file doesn't exist yet, create a starter one so it never fails
    if not os.path.exists(data_path):
        print(f"Creating a fresh starter dataset at: {data_path}")
        with open(data_path, 'w') as f:
            f.write("revenue,debt,noi,defaulted\n100000,20000,50000,0\n30000,25000,5000,1\n150000,30000,80000,0\n20000,28000,-5000,1\n80000,25000,40000,0\n40000,35000,2000,1\n")

    # Load data dynamically
    df = pd.read_csv(data_path)
    
    # Features and Target
    X = df[['revenue', 'debt', 'noi']]
    y = df['defaulted']
    
    # Train model
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)
    
    # Save model
    joblib.dump(model, model_path)
    print(f"✅ ML Model trained and saved to: {os.path.abspath(model_path)}")

if __name__ == "__main__":
    train_risk_model()