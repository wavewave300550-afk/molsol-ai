import pandas as pd
import numpy as np
import xgboost as xgb
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors, Lipinski, QED
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
import urllib.request
import json
import os

# Initialize Toxicity Catalog
_tox_params = FilterCatalogParams()
_tox_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
_tox_params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
TOX_CATALOG = FilterCatalog(_tox_params)

def extract_features(mol):
    from rdkit.Chem import AllChem
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024)
    return list(fp)

def train_model():
    print("Downloading RDKit ESOL dataset...")
    import urllib.request
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = 'https://raw.githubusercontent.com/rdkit/rdkit/master/Docs/Book/data/solubility.train.sdf'
    urllib.request.urlretrieve(url, 'solubility.sdf')
    
    print("Extracting 1024-bit Morgan Fingerprints (this may take a minute)...")
    suppl = Chem.SDMolSupplier('solubility.sdf')
    features_list = []
    targets = []
    
    for mol in suppl:
        if mol is None:
            continue
        try:
            sol = float(mol.GetProp('SOL'))
            feats = extract_features(mol)
            if feats is not None:
                features_list.append(feats)
                targets.append(sol)
        except Exception:
            continue

    X = pd.DataFrame(features_list)
    y = np.array(targets)
    
    print(f"Features extracted successfully for {len(X)} valid molecules.")
    print("Training Advanced XGBoost Regressor (Fingerprint-based)...")
    
    model = xgb.XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    
    model.fit(X, y)
    score = model.score(X, y)
    print(f"Model trained! R^2 Score on training set: {score:.4f}")
    
    model_path = "xgb_solubility_model.json"
    model.save_model(model_path)
    print(f"Advanced Model saved to {os.path.abspath(model_path)}")

if __name__ == "__main__":
    train_model()
