import os
import sys
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm

from gnn_model import SingularityGNN, extract_graph_from_smiles

def train_gnn_model():
    print("="*60)
    print("SINGULARITY ENGINE: INITIALIZING QUANTUM GRAPH NEURAL NETWORK")
    print("="*60)
    
    # Check for device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[SYSTEM] Hardware Accelerator Selected: {device}")

    from rdkit import Chem
    data_path = 'solubility.sdf'
    if not os.path.exists(data_path):
        print(f"[ERROR] Critical dataset '{data_path}' not found! Cannot train model.")
        sys.exit(1)
        
    print(f"[INFO] Loading dataset from {data_path}...")
    suppl = Chem.SDMolSupplier(data_path)
    
    smiles_list = []
    labels_list = []
    
    for mol in suppl:
        if mol is not None and mol.HasProp('SOL') and mol.HasProp('smiles'):
            try:
                val = float(mol.GetProp('SOL'))
                smi = mol.GetProp('smiles')
                smiles_list.append(smi)
                labels_list.append(val)
            except ValueError:
                pass
                
    if not smiles_list:
        print("[ERROR] Failed to parse any molecules from SDF.")
        sys.exit(1)
    
    print(f"[INFO] Extracting Graph Tensors from {len(smiles_list)} SMILES strings...")
    
    X_list = []
    A_list = []
    y_list = []
    
    for smi, lbl in tqdm(zip(smiles_list, labels_list), total=len(smiles_list), desc="Parsing Molecules"):
        X, A = extract_graph_from_smiles(smi)
        if X is not None and A is not None:
            X_list.append(X.to(device))
            A_list.append(A.to(device))
            y_list.append(torch.tensor(lbl, dtype=torch.float32).to(device))
            
    num_samples = len(X_list)
    print(f"[SUCCESS] Successfully parsed {num_samples} molecular graphs.")
    
    # Split Data (80/20)
    split_idx = int(num_samples * 0.8)
    X_train, A_train, y_train = X_list[:split_idx], A_list[:split_idx], y_list[:split_idx]
    X_test, A_test, y_test = X_list[split_idx:], A_list[split_idx:], y_list[split_idx:]
    
    print(f"[INFO] Training set: {len(X_train)} | Test set: {len(X_test)}")
    
    # Initialize Model
    model = SingularityGNN(node_feature_dim=23, hidden_dim=64, output_dim=1).to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)
    criterion = nn.MSELoss()
    
    EPOCHS = 100
    print("\n[TRAINING] Commencing Backpropagation...")
    
    # Because molecular graphs are of different sizes (different N atoms), 
    # building a batched adjacency matrix in pure PyTorch is slightly tricky (requires block-diagonal matrix).
    # For simplicity and robust prototype performance, we will do stochastic gradient descent (batch_size=1) 
    # or accumulate gradients over a pseudo-batch.
    batch_size = 32
    
    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0
        
        optimizer.zero_grad()
        for i in range(len(X_train)):
            x, a, y = X_train[i], A_train[i], y_train[i]
            
            # Forward pass
            pred = model(x, a)
            loss = criterion(pred, y)
            loss.backward()
            
            train_loss += loss.item()
            
            # Gradient accumulation step
            if (i + 1) % batch_size == 0 or (i + 1) == len(X_train):
                optimizer.step()
                optimizer.zero_grad()
                
        avg_train_loss = train_loss / len(X_train)
        
        # Validation
        model.eval()
        test_loss = 0.0
        with torch.no_grad():
            for x, a, y in zip(X_test, A_test, y_test):
                pred = model(x, a)
                loss = criterion(pred, y)
                test_loss += loss.item()
        avg_test_loss = test_loss / len(X_test)
        
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:03d}/{EPOCHS} | Train MSE: {avg_train_loss:.4f} | Test MSE: {avg_test_loss:.4f}")
            
    print("\n[SUCCESS] GNN Brain Training Complete!")
    
    # Save the model
    save_path = "gnn_solubility.pth"
    torch.save(model.state_dict(), save_path)
    print("Singularity Brain Weights saved to '{save_path}'")
    print("="*60)

if __name__ == "__main__":
    train_gnn_model()
