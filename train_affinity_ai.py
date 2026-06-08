import os
import random
import numpy as np
import pandas as pd
import xgboost as xgb
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors

def generate_synthetic_data(num_samples=2000):
    print("Generating synthetic affinity data...")
    # Load some baseline molecules (e.g. from the solubility dataset we already downloaded)
    suppl = Chem.SDMolSupplier('solubility.sdf')
    
    features = []
    targets = []
    
    classes = ["Kinase (e.g. EGFR)", "GPCR (e.g. Dopamine)", "Protease (e.g. HIV PR)"]
    
    for mol in suppl:
        if mol is None:
            continue
            
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024)
        base_fp = list(fp)
        mw = Descriptors.ExactMolWt(mol)
        
        # Synthesize data for all 3 classes for each molecule
        for target_class in classes:
            # One-hot encoding for the target: [is_kinase, is_gpcr, is_protease]
            one_hot = [0, 0, 0]
            if target_class == "Kinase (e.g. EGFR)":
                one_hot[0] = 1
                # Kinases like MW 400-500
                affinity = -8.0 + random.uniform(-1, 1) if 350 < mw < 500 else -5.0 + random.uniform(-1, 1)
            elif target_class == "GPCR (e.g. Dopamine)":
                one_hot[1] = 1
                # GPCRs like MW 200-400
                affinity = -7.0 + random.uniform(-1, 1) if 200 < mw < 400 else -4.0 + random.uniform(-1, 1)
            else:
                one_hot[2] = 1
                # Proteases like heavy MW > 450
                affinity = -9.0 + random.uniform(-1, 1) if mw > 450 else -6.0 + random.uniform(-1, 1)
            
            # Combine Morgan FP (1024) + One-Hot (3) = 1027 features
            feat_vector = base_fp + one_hot
            features.append(feat_vector)
            targets.append(affinity)
            
            if len(features) >= num_samples:
                break
        if len(features) >= num_samples:
            break
            
    return np.array(features, dtype=np.float32), np.array(targets, dtype=np.float32)

def train():
    X, y = generate_synthetic_data(4000)
    print(f"Dataset shape: X={X.shape}, y={y.shape}")
    
    model = xgb.XGBRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42
    )
    
    print("Training Affinity Model...")
    model.fit(X, y)
    score = model.score(X, y)
    print(f"Training R^2: {score:.4f}")
    
    model.save_model("target_affinity_model.json")
    print("Saved target_affinity_model.json")

if __name__ == "__main__":
    train()
