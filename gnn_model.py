import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from rdkit import Chem

# ==============================================================================
# 1. MOLECULAR FEATURE EXTRACTION
# ==============================================================================

# Allowed atoms for one-hot encoding
SUPPORTED_ATOMS = ['C', 'N', 'O', 'S', 'F', 'Cl', 'Br', 'I', 'P', 'Unknown']

def atom_features(atom) -> list:
    """Extract detailed features for a single RDKit atom."""
    symbol = atom.GetSymbol()
    if symbol in SUPPORTED_ATOMS:
        one_hot = [int(symbol == a) for a in SUPPORTED_ATOMS]
    else:
        one_hot = [int('Unknown' == a) for a in SUPPORTED_ATOMS]
    
    degree = atom.GetDegree()
    one_hot_degree = [int(degree == i) for i in range(6)]
    
    formal_charge = atom.GetFormalCharge()
    is_aromatic = int(atom.GetIsAromatic())
    hybridization = atom.GetHybridization()
    one_hot_hybrid = [
        int(hybridization == Chem.rdchem.HybridizationType.SP),
        int(hybridization == Chem.rdchem.HybridizationType.SP2),
        int(hybridization == Chem.rdchem.HybridizationType.SP3),
        int(hybridization == Chem.rdchem.HybridizationType.SP3D),
        int(hybridization == Chem.rdchem.HybridizationType.SP3D2)
    ]
    
    # Total feature size: 10 (Atom) + 6 (Degree) + 1 (Charge) + 1 (Aromatic) + 5 (Hybridization) = 23 features
    features = one_hot + one_hot_degree + [formal_charge, is_aromatic] + one_hot_hybrid
    return features

def extract_graph_from_smiles(smiles: str):
    """
    Convert SMILES string into Node Feature Matrix (X) and Adjacency Matrix (A).
    Returns None if parsing fails.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, None
    
    num_atoms = mol.GetNumAtoms()
    
    # Build Node Features X (num_atoms x 23)
    X = np.zeros((num_atoms, 23), dtype=np.float32)
    for i, atom in enumerate(mol.GetAtoms()):
        X[i, :] = atom_features(atom)
        
    # Build Adjacency Matrix A (num_atoms x num_atoms)
    A = np.zeros((num_atoms, num_atoms), dtype=np.float32)
    for bond in mol.GetBonds():
        i = bond.GetBeginAtomIdx()
        j = bond.GetEndAtomIdx()
        # Edge weight logic: could use bond type (1.0, 1.5, 2.0, 3.0), but using 1.0 for simple graph topology is safer
        # Adding self-loops is handled inside the GNN layer to prevent division by zero during normalization
        A[i, j] = 1.0
        A[j, i] = 1.0
        
    return torch.tensor(X), torch.tensor(A)

# ==============================================================================
# 2. PURE PYTORCH GNN ARCHITECTURE
# ==============================================================================

class GraphConvLayer(nn.Module):
    """A standard Graph Convolutional Network (GCN) layer without external dependencies."""
    def __init__(self, in_features, out_features):
        super(GraphConvLayer, self).__init__()
        self.linear = nn.Linear(in_features, out_features, bias=False)
        self.bias = nn.Parameter(torch.zeros(out_features))
        
    def forward(self, x, adj):
        # x: (Batch_Size, Num_Nodes, In_Features) or (Num_Nodes, In_Features)
        # adj: (Batch_Size, Num_Nodes, Num_Nodes) or (Num_Nodes, Num_Nodes)
        
        # Add self-loops to adjacency matrix
        identity = torch.eye(adj.size(-1), device=adj.device)
        adj_with_self_loops = adj + identity
        
        # Compute Degree matrix D for normalization: D^(-0.5) * A * D^(-0.5)
        degree = adj_with_self_loops.sum(dim=-1, keepdim=True)
        # Add epsilon to prevent division by zero
        d_inv_sqrt = torch.pow(degree + 1e-8, -0.5)
        
        # Normalize adjacency matrix: element-wise broadcast
        # Note: For simple matrices, D^-0.5 A D^-0.5 can be approximated by D^-1 A
        # Here we do a simple row-normalization (D^-1 A) which is highly stable for molecules
        d_inv = torch.pow(degree + 1e-8, -1.0)
        norm_adj = adj_with_self_loops * d_inv
        
        # Message passing: A * X * W
        support = self.linear(x)
        out = torch.matmul(norm_adj, support) + self.bias
        return out

class SingularityGNN(nn.Module):
    """The Ultimate Graph Neural Network for Molecule Property Prediction."""
    def __init__(self, node_feature_dim=23, hidden_dim=64, output_dim=1):
        super(SingularityGNN, self).__init__()
        
        # 3 Layers of Message Passing (Graph Convolutions)
        self.conv1 = GraphConvLayer(node_feature_dim, hidden_dim)
        self.conv2 = GraphConvLayer(hidden_dim, hidden_dim)
        self.conv3 = GraphConvLayer(hidden_dim, hidden_dim)
        
        # Fully Connected Layers after Global Pooling
        self.fc1 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc2 = nn.Linear(hidden_dim // 2, output_dim)
        
        self.dropout = nn.Dropout(0.2)

    def forward(self, x, adj):
        # Graph Convolutions with ReLU activations
        x = F.relu(self.conv1(x, adj))
        x = self.dropout(x)
        
        x = F.relu(self.conv2(x, adj))
        x = self.dropout(x)
        
        x = F.relu(self.conv3(x, adj))
        
        # Global Pooling (Sum or Mean across all nodes to get a graph-level embedding)
        # x is shape: (Num_Nodes, Hidden_Dim)
        # We pool along dimension 0 (the nodes)
        # If batched, x is (Batch_Size, Num_Nodes, Hidden_Dim), pool along dim 1
        if x.dim() == 3:
            graph_embedding = torch.sum(x, dim=1)
        else:
            graph_embedding = torch.sum(x, dim=0, keepdim=True)
            
        # Final Multilayer Perceptron (MLP) mapping graph embedding to a single scalar (LogS)
        out = F.relu(self.fc1(graph_embedding))
        out = self.fc2(out)
        return out.squeeze()
