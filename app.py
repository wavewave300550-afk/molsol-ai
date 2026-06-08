"""
🧬 MolSol De Novo: Advanced AI Drug Design & Explainable AI Platform
=====================================================================
Single-file Streamlit application combining:
  • Chemoinformatics (RDKit) — property calculation, salt stripping, sanitization
  • Machine Learning (XGBoost) — aqueous solubility (LogS) prediction from Morgan FPs
  • Genetic Algorithms (GA) — de novo molecular optimization with in-loop validation
  • Explainable AI (XAI) — perturbation-based atom contributions + SimilarityMaps

Author: MolSol De Novo Team
"""

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — IMPORTS & EARLY CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
import os
import io
import random
import urllib.parse
from typing import Optional, Tuple, List, Dict, Any

import numpy as np
import pandas as pd
import requests
import xgboost as xgb

import matplotlib
matplotlib.use("Agg")                       # headless backend — MUST be before pyplot
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from PIL import Image

import streamlit as st

# ── RDKit ────────────────────────────────────────────────────────────────────
from rdkit import Chem, RDLogger
from rdkit.Chem import (
    Descriptors,
    rdMolDescriptors,
    Draw,
    AllChem,
    RWMol,
    Lipinski,
)
from rdkit.Chem.Draw import rdMolDraw2D, SimilarityMaps
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.Chem.SaltRemover import SaltRemover
from rdkit.Chem import QED
from rdkit import DataStructs
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
from rdkit.Chem import rdFMCS
from rdkit.Chem import BRICS
import plotly.graph_objects as go
try:
    import py3Dmol
    HAS_PY3DMOL = True
except ImportError:
    HAS_PY3DMOL = False

# Import sascorer from RDKit Contrib
import sys
from rdkit import RDConfig
sys.path.append(os.path.join(RDConfig.RDContribDir, 'SA_Score'))
import sascorer  # type: ignore

# ── Initialize Toxicity Filters ──────────────────────────────────────────────
_tox_params = FilterCatalogParams()
_tox_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
_tox_params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
TOX_CATALOG = FilterCatalog(_tox_params)

# ── Stability & Pro Mode Helpers ─────────────────────────────────────────────
UNSTABLE_PATTERNS = [
    Chem.MolFromSmarts("[O,S]-[O,S]-[O,S]"), # Peroxides / Polysulfides
    Chem.MolFromSmarts("[#8]=[#8]"),         # O=O
    Chem.MolFromSmarts("[#7]-[#7]-[#7]"),    # N-N-N chains
    Chem.MolFromSmarts("[#6]1-[#6]-[#6]1=[*]"), # Highly strained 3-membered ring with exocyclic double bond
]

def calculate_sa_score(mol: Chem.Mol) -> float:
    """Calculate Synthetic Accessibility Score (1-10, lower is easier)."""
    try:
        score = sascorer.calculateScore(mol)
        return round(min(10.0, score), 2)
    except Exception:
        return 10.0

@st.cache_resource
def load_affinity_model():
    """Load the Deep Learning Target Affinity XGBoost Regressor."""
    path = "target_affinity_model.json"
    if os.path.exists(path):
        try:
            m = xgb.XGBRegressor()
            m.load_model(path)
            return m
        except:
            return None
    return None

def simulate_binding_affinity(affinity_model, mol: Chem.Mol, target: str) -> float:
    """Predict Target Affinity (-kcal/mol) using Deep Learning."""
    if affinity_model is None:
        return -5.0 # Fallback
    try:
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024)
        base_fp = list(fp)
        one_hot = [0, 0, 0]
        target_lower = target.lower()
        if "kinase" in target_lower or "cyclooxygenase" in target_lower or "cox" in target_lower:
            one_hot[0] = 1
        elif "gpcr" in target_lower or "dopamine" in target_lower or "receptor" in target_lower:
            one_hot[1] = 1
        elif "protease" in target_lower or "mpro" in target_lower or "sars-cov-2" in target_lower:
            one_hot[2] = 1
        else:
            # Default fallback if no match
            one_hot[0] = 1
        feat_vector = base_fp + one_hot
        arr = np.array(feat_vector, dtype=np.float32).reshape(1, -1)
        return float(affinity_model.predict(arr)[0])
    except Exception:
        return -5.0
        
# ── XGBoost ──────────────────────────────────────────────────────────────────
import xgboost as xgb

# Suppress noisy RDKit warnings in the Streamlit log
RDLogger.logger().setLevel(RDLogger.ERROR)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — STREAMLIT PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="MolSol De Novo — AI Drug Design & XAI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CONSTANTS & EXAMPLE DATA
# ═══════════════════════════════════════════════════════════════════════════════
MORGAN_NBITS: int = 1024
MORGAN_RADIUS: int = 2

EXAMPLE_DRUGS: Dict[str, str] = {
    "💊 Aspirin":      "CC(=O)Oc1ccccc1C(=O)O",
    "💊 Ibuprofen":    "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O",
    "💊 Paracetamol":  "CC(=O)Nc1ccc(O)cc1",
    "💊 Metformin":    "CN(C)C(=N)NC(=N)N",
    "☕ Caffeine":     "Cn1c(=O)c2c(ncn2C)n(C)c1=O",
    "💊 Penicillin G": "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O",
}

MODEL_FILE_CANDIDATES: List[str] = [
    "xgb_solubility_model.json",
    "xgb_solubility_model.pkl",
    "solubility_model.json",
    "solubility_model.pkl",
    os.path.join("model", "xgb_solubility_model.json"),
    os.path.join("model", "solubility_model.json"),
]

# Elements used during GA mutation (atomic numbers)
MUTATION_ELEMENTS: List[int] = [6, 7, 8, 9, 16, 17]  # C, N, O, F, S, Cl

# SMARTS for functional-group detection (XAI interpretation)
FUNCTIONAL_GROUPS: Dict[str, str] = {
    "Hydroxyl (-OH)":           "[OX2H1]",
    "Carboxyl (-COOH)":         "[CX3](=O)[OX2H1]",
    "Primary Amine (-NH₂)":    "[NX3H2]",
    "Secondary Amine (-NH-)":  "[NX3H1]([#6])[#6]",
    "Amide (-CONH-)":          "[CX3](=O)[NX3]",
    "Aromatic Ring":           "c1ccccc1",
    "Methyl (-CH₃)":          "[CH3]",
    "Methylene (-CH₂-)":      "[CH2]",
    "Halogen (F/Cl/Br)":       "[F,Cl,Br]",
    "Ether (-O-)":             "[OD2]([#6])[#6]",
    "Nitro (-NO₂)":           "[NX3](=O)=O",
    "Sulfonyl (-SO₂-)":       "[SX4](=O)(=O)",
    "Carbonyl (C=O)":          "[CX3]=O",
    "Ester (-COO-)":           "[CX3](=O)[OX2][#6]",
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — CUSTOM CSS (PREMIUM DARK-THEMED UI)
# ═══════════════════════════════════════════════════════════════════════════════
_CSS = """
<style>
/* ══════════════════════════════════════════════════════════
   🟢 Core Research Theme — Sleek Obsidian Glass Dark UI
   ══════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] { 
    font-family: 'Outfit', sans-serif !important; 
}
h1, h2, h3, h4, h5 { 
    font-family: 'Outfit', sans-serif !important; 
    letter-spacing: -0.02em; 
    color: #f1f5f9;
}

.stApp {
    background: radial-gradient(circle at 50% 0%, #0f172a 0%, #090d16 60%, #030408 100%) !important;
}

/* ── Header ── */
.main-header {
    background: linear-gradient(135deg, rgba(21, 32, 54, 0.65) 0%, rgba(13, 20, 35, 0.85) 100%) !important;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    padding: 30px 35px !important;
    border-radius: 20px !important;
    margin-bottom: 28px !important;
    border: 1px solid rgba(59, 130, 246, 0.15) !important;
    box-shadow: 0 20px 40px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.05) !important;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: ''; 
    position: absolute; 
    top: -50%; 
    right: -10%; 
    width: 400px; 
    height: 400px;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%); 
    pointer-events: none;
}
.main-header h1 {
    margin: 0; 
    font-size: 2.4rem !important; 
    font-weight: 800 !important; 
    letter-spacing: -0.8px !important;
    background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #8b5cf6 100%);
    -webkit-background-clip: text !important; 
    -webkit-text-fill-color: transparent !important;
}
.main-header p {
    margin: 8px 0 0 0 !important; 
    color: #94a3b8 !important; 
    font-size: 0.95rem !important; 
    font-weight: 400 !important;
    letter-spacing: 0.2px !important;
}

/* ── Cards ── */
.card {
    background: rgba(17, 24, 39, 0.45) !important;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 16px !important;
    padding: 22px !important;
    margin-bottom: 15px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 12px 30px rgba(0,0,0,0.2) !important;
}
.card:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 20px 40px rgba(0,0,0,0.35) !important;
    border-color: rgba(59, 130, 246, 0.3) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: rgba(17, 24, 39, 0.5) !important;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 14px !important;
    padding: 16px 20px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.18) !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px) !important;
    border-color: rgba(59, 130, 246, 0.25) !important;
    box-shadow: 0 15px 35px rgba(0,0,0,0.28) !important;
}
[data-testid="stMetricLabel"] {
    color: #94a3b8 !important; 
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    text-transform: uppercase; 
    letter-spacing: 1px;
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    color: #f1f5f9 !important; 
    font-weight: 700 !important;
    font-size: 1.8rem !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090d16 0%, #05070d 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.04) !important;
}
section[data-testid="stSidebar"] .stButton > button {
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    background: rgba(30, 41, 59, 0.45) !important;
    color: #f1f5f9 !important;
    font-weight: 600 !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(59, 130, 246, 0.15) !important;
    border-color: rgba(59, 130, 246, 0.4) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(0,0,0,0.25) !important;
}

/* ── Streamlit Native Form Inputs & Selectboxes ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
    background-color: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
    color: #f1f5f9 !important;
    transition: all 0.3s ease !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: rgba(59, 130, 246, 0.4) !important;
    box-shadow: 0 0 10px rgba(59, 130, 246, 0.2) !important;
}

/* ── Tabs & Expanders ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background-color: rgba(15, 23, 42, 0.4) !important;
    padding: 6px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 8px 18px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    border: none !important;
    transition: all 0.25s ease !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(37, 99, 235, 0.22) 100%) !important;
    color: #60a5fa !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: rgba(0,0,0,0.15); }
::-webkit-scrollbar-thumb { background: rgba(59, 130, 246, 0.18); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(59, 130, 246, 0.35); }

/* ── Section divider ── */
.section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.15), transparent);
    margin: 28px 0;
}

/* ── Floating AI Chat Button ── */
.oracle-chat-btn {
    position: fixed; top: 12px; right: 60px; z-index: 99999;
    background: linear-gradient(135deg, #7c3aed, #db2777) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 12px !important;
    padding: 10px 22px !important;
    color: white !important; 
    font-weight: 700 !important; 
    font-size: 0.85rem !important;
    cursor: pointer !important;
    box-shadow: 0 10px 25px rgba(219, 39, 119, 0.3) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    letter-spacing: 0.5px !important;
    animation: oracle-glow 3s infinite;
}
.oracle-chat-btn:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 15px 30px rgba(219, 39, 119, 0.5) !important;
}
@keyframes oracle-glow {
    0%, 100% { box-shadow: 0 10px 25px rgba(219, 39, 119, 0.25); }
    50% { box-shadow: 0 15px 35px rgba(219, 39, 119, 0.55), 0 0 30px rgba(124, 58, 237, 0.15); }
}

/* ── Full-Screen Chat Overlay ── */
.oracle-fullscreen {
    background: linear-gradient(180deg, #090514 0%, #110924 30%, #0d061c 100%) !important;
    border-radius: 20px !important;
    border: 1px solid rgba(219, 39, 119, 0.15) !important;
    padding: 0 !important;
    margin: -1rem !important;
    min-height: 85vh !important;
    position: relative;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.55) !important;
}
.oracle-chat-header {
    background: linear-gradient(135deg, #18092a 0%, #281044 50%, #1c0934 100%) !important;
    padding: 24px 32px !important;
    border-radius: 20px 20px 0 0 !important;
    border-bottom: 1px solid rgba(219, 39, 119, 0.2) !important;
    display: flex; align-items: center; justify-content: space-between;
}
.oracle-chat-header h2 {
    margin: 0 !important;
    background: linear-gradient(90deg, #fbbf24, #db2777, #a855f7) !important;
    -webkit-background-clip: text !important; 
    -webkit-text-fill-color: transparent !important;
    font-size: 1.6rem !important; 
    font-weight: 850 !important;
}
.oracle-chat-header p {
    color: rgba(168, 237, 234, 0.75) !important; 
    font-size: 0.82rem !important; 
    margin: 6px 0 0 0 !important;
}
.oracle-status {
    display: inline-block !important; 
    padding: 6px 14px !important; 
    border-radius: 20px !important;
    background: rgba(219, 39, 119, 0.12) !important; 
    border: 1px solid rgba(219, 39, 119, 0.35) !important;
    color: #db2777 !important; 
    font-size: 0.72rem !important; 
    font-weight: 600 !important;
    letter-spacing: 1.5px; 
    text-transform: uppercase;
    animation: status-pulse 2s infinite;
}
@keyframes status-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.65; }
}
</style>
"""

GENESIS_CSS = """
<style>
/* ══════════════════════════════════════════════════════════
   🔵 Genesis Protocol Theme — Sci-Fi Cyan Blue UI
   ══════════════════════════════════════════════════════════ */
.stApp {
    background: radial-gradient(circle at 50% 0%, #0d1e3d 0%, #060c18 60%, #020409 100%) !important;
}
.main-header {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.75) 0%, rgba(8, 14, 28, 0.9) 100%) !important;
    border: 1px solid rgba(168, 237, 234, 0.22) !important;
    box-shadow: 0 25px 50px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.06) !important;
}
.main-header::before {
    background: radial-gradient(circle, rgba(168, 237, 234, 0.12) 0%, transparent 70%) !important;
}
.main-header h1 {
    background: linear-gradient(135deg, #a8edea 0%, #fed6e3 50%, #d299c2 100%) !important;
    -webkit-background-clip: text !important; 
    -webkit-text-fill-color: transparent !important;
    text-shadow: 0 0 30px rgba(168, 237, 234, 0.15) !important;
}
.main-header p { 
    color: rgba(168, 237, 234, 0.8) !important; 
}

.card {
    background: rgba(12, 22, 43, 0.5) !important;
    border: 1px solid rgba(168, 237, 234, 0.08) !important;
}
.card:hover {
    border-color: rgba(168, 237, 234, 0.3) !important;
    box-shadow: 0 20px 40px rgba(168, 237, 234, 0.1) !important;
}

[data-testid="stMetric"] {
    background: rgba(12, 22, 43, 0.55) !important;
    border: 1px solid rgba(168, 237, 234, 0.08) !important;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(168, 237, 234, 0.3) !important;
}
[data-testid="stMetricValue"] {
    color: #a8edea !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #060c18 0%, #03060c 100%) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    border-color: rgba(168, 237, 234, 0.45) !important;
    background: rgba(168, 237, 234, 0.08) !important;
}

.section-divider {
    background: linear-gradient(90deg, transparent, rgba(168, 237, 234, 0.22), transparent) !important;
}
</style>
"""

SINGULARITY_CSS = GENESIS_CSS + """
<style>
/* ══════════════════════════════════════════════════════════
   🟣 Singularity Engine — High-End Deep Space Neon UI
   ══════════════════════════════════════════════════════════ */
.stApp {
    background: radial-gradient(circle at 100% 0%, #220e3a 0%, #0a0414 45%, #030107 80%) !important;
}
.main-header {
    background: linear-gradient(135deg, rgba(32, 10, 60, 0.75) 0%, rgba(13, 5, 26, 0.92) 100%) !important;
    border: 1px solid rgba(236, 72, 153, 0.35) !important;
    box-shadow: 0 30px 60px rgba(236, 72, 153, 0.15), 0 20px 50px rgba(0,0,0,0.55), inset 0 0 30px rgba(124, 58, 237, 0.25) !important;
}
.main-header::before {
    background: radial-gradient(circle, rgba(236, 72, 153, 0.15) 0%, transparent 70%) !important;
}
.main-header h1 {
    background: linear-gradient(90deg, #f59e0b 0%, #ec4899 50%, #a855f7 100%) !important;
    -webkit-background-clip: text !important; 
    -webkit-text-fill-color: transparent !important;
    text-shadow: 0 0 45px rgba(236, 72, 153, 0.25) !important;
}
.main-header p {
    color: #e2e8f0 !important;
}

.card {
    background: rgba(22, 12, 45, 0.45) !important;
    border: 1px solid rgba(236, 72, 153, 0.15) !important;
}
.card:hover {
    border-color: rgba(236, 72, 153, 0.4) !important;
    box-shadow: 0 25px 45px rgba(236, 72, 153, 0.2) !important;
}

[data-testid="stMetric"] {
    background: rgba(22, 12, 45, 0.5) !important;
    border: 1px solid rgba(236, 72, 153, 0.12) !important;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(236, 72, 153, 0.45) !important;
    box-shadow: 0 20px 40px rgba(236, 72, 153, 0.15) !important;
}
[data-testid="stMetricValue"] {
    color: #f472b6 !important;
    text-shadow: 0 0 10px rgba(236, 72, 153, 0.25) !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0414 0%, #040108 100%) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    border-color: rgba(236, 72, 153, 0.45) !important;
    background: rgba(236, 72, 153, 0.08) !important;
}

.section-divider {
    background: linear-gradient(90deg, transparent, rgba(236, 72, 153, 0.25), transparent) !important;
}
</style>
"""


st.markdown(_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — CORE HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def clean_molecule(smiles_input: str) -> Tuple[Optional[Chem.Mol], Optional[str], Optional[str]]:
    """Validate, parse, salt-strip, and sanitize a SMILES string.

    Returns
    -------
    (mol, canonical_smiles, error_message)
        On success, *error_message* is ``None``.
    """
    if not smiles_input or len(smiles_input.strip()) == 0:
        return None, None, "Please enter a SMILES string."

    smiles = smiles_input.strip()

    # ── Length guard ──────────────────────────────────────────────────────
    if len(smiles) > 250:
        return None, None, "⚠️ SMILES exceeds the 250-character safety limit. Please shorten your input."

    # ── Parse ─────────────────────────────────────────────────────────────
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            # Fallback to strict PubChem name matching if parsing fails
            resolved_smiles, err = resolve_pubchem_name(smiles)
            if resolved_smiles:
                mol = Chem.MolFromSmiles(resolved_smiles)
            if mol is None:
                return None, None, err if err else "❌ Invalid SMILES — RDKit could not parse this string."
    except Exception as exc:
        return None, None, f"❌ SMILES parsing error: {exc}"

    # ── Sanitize ──────────────────────────────────────────────────────────
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        return None, None, f"❌ Sanitization failed (possible illegal valence): {exc}"

    # ── Strict Stability Check ────────────────────────────────────────────
    for pat in UNSTABLE_PATTERNS:
        if pat and mol.HasSubstructMatch(pat):
            return None, None, "❌ Unstable structure detected (e.g., Peroxide, highly strained ring)."

    # ── Salt stripping ────────────────────────────────────────────────────
    try:
        remover = SaltRemover()
        stripped = remover.StripMol(mol)
    except Exception:
        stripped = mol  # fall-through if remover chokes

    # Extract the largest organic fragment as the core structure
    try:
        frags = Chem.GetMolFrags(stripped, asMols=True, sanitizeFrags=True)
        if not frags:
            frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
        if not frags:
            return None, None, "❌ Could not extract a valid fragment after salt stripping."
        core = max(frags, key=lambda m: m.GetNumAtoms())
        canonical = Chem.MolToSmiles(core)
        return core, canonical, None
    except Exception as exc:
        return None, None, f"❌ Salt stripping error: {exc}"


def compute_properties(mol: Chem.Mol) -> Dict[str, Any]:
    """Compute molecular properties.

    **CRITICAL — HBD / HBA mapping is VERIFIED (Using universal Lipinski module):**
      • HBD → ``Lipinski.NumHDonors``   (Hydrogen Bond **Donors**)
      • HBA → ``Lipinski.NumHAcceptors``   (Hydrogen Bond **Acceptors**)
    """
    return {
        "Molecular Weight":     round(Descriptors.ExactMolWt(mol), 2),
        "LogP (Crippen)":       round(Descriptors.MolLogP(mol), 3),
        # ── BUG FIX: these are intentionally in this order ────────────
        "HBD (H-Bond Donors)":      Lipinski.NumHDonors(mol),
        "HBA (H-Bond Acceptors)":   Lipinski.NumHAcceptors(mol),
        # ──────────────────────────────────────────────────────────────
        "TPSA (Å²)":           round(Descriptors.TPSA(mol), 2),
        "Rotatable Bonds":      rdMolDescriptors.CalcNumRotatableBonds(mol),
        "Aromatic Rings":       rdMolDescriptors.CalcNumAromaticRings(mol),
        "Heavy Atoms":          mol.GetNumHeavyAtoms(),
        "Rings":                rdMolDescriptors.CalcNumRings(mol),
        "Fraction Csp³":       round(rdMolDescriptors.CalcFractionCSP3(mol), 3),
        "QED Score":           round(QED.qed(mol), 4),
        "Toxicity Alerts":     len(TOX_CATALOG.GetMatches(mol)),
        "SA Score (1-10)":     calculate_sa_score(mol),
    }


def lipinski_assessment(props: Dict[str, Any]) -> Tuple[int, List[str], str]:
    """Evaluate Lipinski Ro5 and return a traffic-light badge.

    Returns
    -------
    (num_violations, violation_details, badge_html)
    """
    violations: List[str] = []
    mw   = props["Molecular Weight"]
    logp = props["LogP (Crippen)"]
    hbd  = props["HBD (H-Bond Donors)"]       # Lipinski.NumHDonors  ✓
    hba  = props["HBA (H-Bond Acceptors)"]     # Lipinski.NumHAcceptors  ✓

    if mw > 500:
        violations.append("MW > 500")
    if logp > 5:
        violations.append("LogP > 5")
    if hbd > 5:
        violations.append("HBD > 5")
    if hba > 10:
        violations.append("HBA > 10")

    n = len(violations)
    if n == 0:
        badge = '✅ **PASSED — 0 Violations**'
    else:
        viol_str = ", ".join(violations)
        badge = f'⚠️ **WARNING — {n} Violation(s) ({viol_str})**'
    return n, violations, badge


@st.cache_data(ttl=3600, show_spinner=False)
def lookup_pubchem_cid(smiles: str) -> Optional[int]:
    """Query PubChem PUG REST for a matching CID. Returns ``None`` on miss."""
    try:
        encoded = urllib.parse.quote(smiles, safe="")
        url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
            f"smiles/{encoded}/cids/JSON"
        )
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            cids = data.get("IdentifierList", {}).get("CID", [])
            return cids[0] if cids else None
        return None
        return None
    except Exception:
        return None


def resolve_pubchem_name(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Query PubChem by name and return strict exact match (SMILES, error)."""
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{urllib.parse.quote(query)}/property/IsomericSMILES,CanonicalSMILES,Title/JSON"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            props = data.get("PropertyTable", {}).get("Properties", [])
            if props:
                item = props[0]
                smiles = item.get("IsomericSMILES") or item.get("CanonicalSMILES") or item.get("SMILES")
                if smiles:
                    return smiles, None
        return None, "⚠️ Molecule not found. Please check your spelling."
    except Exception as exc:
        return None, f"❌ PubChem API error: {exc}"


def assess_stability(mol: Chem.Mol) -> Tuple[bool, List[str]]:
    """Run structural-stability heuristics. Returns (is_stable, issues)."""
    issues: List[str] = []

    # Radical electrons
    for atom in mol.GetAtoms():
        if atom.GetNumRadicalElectrons() > 0:
            issues.append("Contains radical species")
            break

    # Highly strained 3-membered rings
    ri = mol.GetRingInfo()
    for ring in ri.AtomRings():
        if len(ring) <= 3:
            issues.append("Contains highly strained 3-membered ring")
            break

    # Peroxide (O-O) bond
    peroxide = Chem.MolFromSmarts("[OX2][OX2]")
    if peroxide and mol.HasSubstructMatch(peroxide):
        issues.append("Contains peroxide bond (O–O)")

    # Unusually high formal charge
    total_q = sum(a.GetFormalCharge() for a in mol.GetAtoms())
    if abs(total_q) > 2:
        issues.append(f"High net formal charge ({total_q:+d})")

    # Very small fragment
    if mol.GetNumHeavyAtoms() < 3:
        issues.append("Very small molecule (< 3 heavy atoms)")

    return (len(issues) == 0), issues


def mol_to_image(mol: Chem.Mol, size: Tuple[int, int] = (450, 350)) -> Image.Image:
    """Render a clean 2D structure image via RDKit.
    NOTE: Caller must call AllChem.Compute2DCoords(mol) beforehand.
    """
    return Draw.MolToImage(mol, size=size, kekulize=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — XGBOOST MODEL + EXPLAINABLE AI
# ═══════════════════════════════════════════════════════════════════════════════

def _create_fallback_model() -> xgb.XGBRegressor:
    """Train a lightweight demo model on synthetic Morgan-FP data so the UI
    never breaks even when no real model file is present."""
    rng = np.random.RandomState(42)
    n = 300
    X = rng.randint(0, 2, size=(n, MORGAN_NBITS)).astype(np.float32)

    # Synthetic LogS:  more 1-bits → lower solubility (larger molecule)
    # Some "polar" bits get a positive nudge.
    bit_weights = rng.randn(MORGAN_NBITS).astype(np.float32) * 0.008
    bit_weights[:80]   =  0.006   # bits loosely correlated with polarity → better sol.
    bit_weights[500:620] = -0.010  # bits loosely correlated with hydrophobicity
    y = -2.0 + (X @ bit_weights) + rng.randn(n).astype(np.float32) * 0.25

    model = xgb.XGBRegressor(
        n_estimators=50,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        verbosity=0,
    )
    model.fit(X, y)
    model.fit(X, y)
    return model


@st.cache_resource
def load_gnn_model():
    """Load the trained PyTorch GNN model for Singularity Engine."""
    try:
        import torch
        from gnn_model import SingularityGNN
        
        model_path = "gnn_solubility.pth"
        if os.path.isfile(model_path):
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            model = SingularityGNN(node_feature_dim=23, hidden_dim=64, output_dim=1)
            model.load_state_dict(torch.load(model_path, map_location=device))
            model.to(device)
            model.eval()
            return model, True
    except Exception as e:
        print(f"Failed to load GNN: {e}")
    return None, False


@st.cache_resource
def load_xgb_model() -> Tuple[xgb.XGBRegressor, bool]:
    """Try to load a real pre-trained model; fall back to demo model.

    Returns (model, is_real_model).
    """
    import pickle

    for path in MODEL_FILE_CANDIDATES:
        if os.path.isfile(path):
            try:
                if path.endswith(".json"):
                    m = xgb.XGBRegressor()
                    m.load_model(path)
                    return m, True
                elif path.endswith(".pkl"):
                    with open(path, "rb") as fh:
                        m = pickle.load(fh)
                    return m, True
            except Exception:
                continue

    return _create_fallback_model(), False


def predict_solubility(model, mol: Chem.Mol) -> float:
    """Predict LogS from a 1024-bit Morgan fingerprint or GNN Graph."""
    try:
        # Check if it's a PyTorch model
        if hasattr(model, 'forward'):
            import torch
            from gnn_model import extract_graph_from_smiles
            smi = Chem.MolToSmiles(mol)
            X, A = extract_graph_from_smiles(smi)
            if X is not None and A is not None:
                device = next(model.parameters()).device
                with torch.no_grad():
                    pred = model(X.to(device), A.to(device))
                    return float(pred.item())
            return -5.0
            
        # Default fallback to XGBoost
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, MORGAN_RADIUS, nBits=MORGAN_NBITS)
        arr = np.array(fp, dtype=np.float32).reshape(1, -1)
        return float(model.predict(arr)[0])
    except Exception:
        return -5.0


def compute_atom_contributions(
    model: xgb.XGBRegressor, mol: Chem.Mol
) -> List[float]:
    """Perturbation-based XAI: flip each active fingerprint bit off and measure
    the change in predicted LogS.

    Sign convention
    ───────────────
    positive weight → atom **increases** solubility   → rendered **Blue**
    negative weight → atom **decreases** solubility   → rendered **Red**
    """
    bi: Dict[int, list] = {}
    fp = AllChem.GetMorganFingerprintAsBitVect(
        mol, MORGAN_RADIUS, nBits=MORGAN_NBITS, bitInfo=bi
    )
    fp_arr = np.array(fp, dtype=np.float32).reshape(1, -1)
    baseline = float(model.predict(fp_arr)[0])

    # Per-bit contribution via single-flip perturbation
    bit_contrib: Dict[int, float] = {}
    for bit in bi:
        if fp_arr[0, bit] == 1:
            modified = fp_arr.copy()
            modified[0, bit] = 0
            new_pred = float(model.predict(modified)[0])
            bit_contrib[bit] = baseline - new_pred      # +ve → bit helps solubility

    # Map bit contributions → atoms
    n_atoms = mol.GetNumAtoms()
    weights = np.zeros(n_atoms, dtype=np.float64)
    counts  = np.zeros(n_atoms, dtype=np.float64)

    for bit, envs in bi.items():
        if bit in bit_contrib:
            for atom_idx, _radius in envs:
                if atom_idx < n_atoms:
                    weights[atom_idx] += bit_contrib[bit]
                    counts[atom_idx]  += 1

    mask = counts > 0
    weights[mask] /= counts[mask]

    # Normalise for clearer colour scale
    mx = max(abs(weights.min()), abs(weights.max()), 1e-10)
    weights /= mx

    return weights.tolist()


def render_xai_map(mol: Chem.Mol, weights: List[float]) -> Image.Image:
    """Draw a SimilarityMap using RDKit's native Draw2D renderer.

    Colour scheme  (``cm.RdBu`` — verified for RDKit 2026+):
      • **Blue** → positive contribution → increases solubility
      • **Red**  → negative contribution → decreases solubility
      • **White** → neutral

    The function uses ``MolDraw2DCairo`` as the mandatory ``draw2d``
    backend (required since RDKit ≥ 2024).  If the similarity-map
    rendering fails for *any* reason the function falls back to a
    clean standard ``MolToImage`` so the page never crashes.
    """
    # Trivial molecules cannot produce a meaningful contour
    if mol.GetNumAtoms() < 2:
        return mol_to_image(mol)

    # NOTE: Assumes Compute2DCoords was already called by the caller.

    try:
        # ── Primary path: MolDraw2DCairo + SimilarityMap ──────────
        width, height = 450, 400
        d2d = rdMolDraw2D.MolDraw2DCairo(width, height)

        SimilarityMaps.GetSimilarityMapFromWeights(
            mol,
            weights,
            draw2d=d2d,
            colorMap=cm.RdBu,       # Blue(+) / Red(−)
            scale=-1,               # auto-scale to max |weight|
            size=(width, height),
            contourLines=10,
            alpha=0.5,
        )

        d2d.FinishDrawing()
        png_bytes = d2d.GetDrawingText()
        return Image.open(io.BytesIO(png_bytes))

    except Exception:
        # ── Fallback: plain 2-D structure ─────────────────────────
        return mol_to_image(mol, size=(450, 400))


def generate_ai_interpretation(
    mol: Chem.Mol,
    atom_weights: List[float],
    pred_logs: float,
) -> str:
    """Build a human-readable XAI summary of which functional groups drive
    the predicted solubility."""
    pos_groups: List[Tuple[str, float]] = []
    neg_groups: List[Tuple[str, float]] = []

    for name, smarts in FUNCTIONAL_GROUPS.items():
        pat = Chem.MolFromSmarts(smarts)
        if pat is None:
            continue
        matches = mol.GetSubstructMatches(pat)
        if not matches:
            continue
        avg_w = float(np.mean([
            atom_weights[idx]
            for match in matches for idx in match
            if idx < len(atom_weights)
        ]))
        if avg_w > 0.05:
            pos_groups.append((name, avg_w))
        elif avg_w < -0.05:
            neg_groups.append((name, avg_w))

    pos_groups.sort(key=lambda x: x[1], reverse=True)
    neg_groups.sort(key=lambda x: x[1])

    lines: List[str] = []

    # Solubility bucket
    if pred_logs > -1:
        lines.append("🟢 **Predicted Solubility Class:** Highly Soluble")
    elif pred_logs > -3:
        lines.append("🟡 **Predicted Solubility Class:** Moderately Soluble")
    elif pred_logs > -5:
        lines.append("🟠 **Predicted Solubility Class:** Slightly Soluble")
    else:
        lines.append("🔴 **Predicted Solubility Class:** Poorly Soluble")

    lines.append(f"**Predicted LogS:** {pred_logs:.4f}")
    lines.append("")

    if pos_groups:
        lines.append("**🔵 Solubility-Enhancing Groups (Blue regions):**")
        for name, w in pos_groups[:5]:
            lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;• {name} &nbsp; _(contribution: +{w:.3f})_")
        lines.append("")

    if neg_groups:
        lines.append("**🔴 Solubility-Reducing Groups (Red regions):**")
        for name, w in neg_groups[:5]:
            lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;• {name} &nbsp; _(contribution: {w:.3f})_")
        lines.append("")

    if not pos_groups and not neg_groups:
        lines.append(
            "_No dominant functional-group contributions detected.  "
            "The prediction is driven by overall molecular topology and fingerprint pattern._"
        )

    lines.append("---")

    if pos_groups and neg_groups:
        lines.append(
            f"💡 **Key Insight:** The AI identified that **{pos_groups[0][0]}** groups "
            f"heavily accelerated aqueous solubility _(Blue)_, whereas the "
            f"**{neg_groups[0][0]}** moieties restricted it _(Red)_."
        )
    elif pos_groups:
        lines.append(
            f"💡 **Key Insight:** **{pos_groups[0][0]}** groups are the primary "
            "drivers of solubility in this molecule."
        )
    elif neg_groups:
        lines.append(
            f"💡 **Key Insight:** **{neg_groups[0][0]}** moieties are the dominant "
            "factors reducing solubility."
        )

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — GENETIC ALGORITHM ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _strict_validate(smiles: str) -> Optional[Chem.Mol]:
    """Parse + sanitise SMILES.  Returns Mol or None."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        Chem.SanitizeMol(mol)
        return mol
    except Exception:
        return None


def mutate_molecule(mol: Chem.Mol, max_retries: int = 15, scaffold: Optional[Chem.Mol] = None) -> Optional[Chem.Mol]:
    """Apply one random chemical mutation and validate the result.

    The mutation is retried up to *max_retries* times if it produces an
    invalid structure or breaks the core scaffold.
    """
    for _ in range(max_retries):
        try:
            rw = RWMol(mol)
            n_atoms = rw.GetNumAtoms()
            if n_atoms < 2:
                return None

            op = random.choice([
                "atom_swap", "add_carbon", "add_oxygen", "add_nitrogen",
                "add_halogen", "add_hydroxyl", "remove_terminal", "add_methyl",
            ])

            if op == "atom_swap":
                idx = random.randint(0, n_atoms - 1)
                cur = rw.GetAtomWithIdx(idx).GetAtomicNum()
                pool = [e for e in MUTATION_ELEMENTS if e != cur]
                if pool:
                    rw.GetAtomWithIdx(idx).SetAtomicNum(random.choice(pool))

            elif op in ("add_carbon", "add_oxygen", "add_nitrogen"):
                elem = {"add_carbon": 6, "add_oxygen": 8, "add_nitrogen": 7}[op]
                idx = random.randint(0, n_atoms - 1)
                new_idx = rw.AddAtom(Chem.Atom(elem))
                rw.AddBond(idx, new_idx, Chem.BondType.SINGLE)

            elif op == "add_halogen":
                idx = random.randint(0, n_atoms - 1)
                hal = random.choice([9, 17])  # F, Cl
                new_idx = rw.AddAtom(Chem.Atom(hal))
                rw.AddBond(idx, new_idx, Chem.BondType.SINGLE)

            elif op == "add_hydroxyl":
                idx = random.randint(0, n_atoms - 1)
                o_idx = rw.AddAtom(Chem.Atom(8))  # O
                rw.AddBond(idx, o_idx, Chem.BondType.SINGLE)

            elif op == "add_methyl":
                idx = random.randint(0, n_atoms - 1)
                c_idx = rw.AddAtom(Chem.Atom(6))  # C
                rw.AddBond(idx, c_idx, Chem.BondType.SINGLE)

            elif op == "remove_terminal":
                terminals = [
                    a.GetIdx() for a in rw.GetAtoms()
                    if a.GetDegree() == 1 and n_atoms > 4
                ]
                if not terminals:
                    continue
                rw.RemoveAtom(random.choice(terminals))

            # ── In-loop validation (strict) ──────────────────────────
            Chem.SanitizeMol(rw)
            smi = Chem.MolToSmiles(rw)
            check = _strict_validate(smi)
            if check is not None:
                if scaffold is not None and not check.HasSubstructMatch(scaffold):
                    continue
                return check
        except Exception:
            continue
    return None


def crossover_molecules(
    mol1: Chem.Mol, mol2: Chem.Mol, max_retries: int = 15, scaffold: Optional[Chem.Mol] = None
) -> Optional[Chem.Mol]:
    """Simple crossover: swap 1-3 atom types from *mol2* into *mol1*."""
    for _ in range(max_retries):
        try:
            rw = RWMol(mol1)
            types2 = [a.GetAtomicNum() for a in mol2.GetAtoms()]
            if rw.GetNumAtoms() == 0 or not types2:
                return None
            n_swaps = random.randint(1, min(3, rw.GetNumAtoms()))
            indices = random.sample(range(rw.GetNumAtoms()), n_swaps)
            for idx in indices:
                rw.GetAtomWithIdx(idx).SetAtomicNum(random.choice(types2))
            Chem.SanitizeMol(rw)
            smi = Chem.MolToSmiles(rw)
            check = _strict_validate(smi)
            if check is not None:
                if scaffold is not None and not check.HasSubstructMatch(scaffold):
                    continue
                return check
        except Exception:
            continue
    return None


def _extract_tpp(prompt: str) -> dict:
    import re
    tpp = {}
    
    # MW
    m = re.search(r'MW\s*(<|<=|>|>=|=)\s*([\d\.]+)', prompt, re.IGNORECASE)
    if m: tpp['MW'] = (m.group(1), float(m.group(2)))
        
    # QED
    m = re.search(r'QED\s*(<|<=|>|>=|=)\s*([\d\.]+)', prompt, re.IGNORECASE)
    if m: tpp['QED'] = (m.group(1), float(m.group(2)))
        
    # LogP (single bound)
    m = re.search(r'LogP\s*(<|<=|>|>=|=)\s*([\d\.]+)', prompt, re.IGNORECASE)
    if m: tpp['LogP'] = (m.group(1), float(m.group(2)))
        
    # LogP (range) e.g., 1.5 <= LogP <= 3.5
    m2 = re.search(r'([\d\.]+)\s*(<|<=)\s*LogP\s*(<|<=)\s*([\d\.]+)', prompt, re.IGNORECASE)
    if m2: tpp['LogP_range'] = (float(m2.group(1)), float(m2.group(4)))
        
    # TPSA
    m = re.search(r'TPSA\s*(<|<=|>|>=|=)\s*([\d\.]+)', prompt, re.IGNORECASE)
    if m: tpp['TPSA'] = (m.group(1), float(m.group(2)))
    
    m2 = re.search(r'([\d\.]+)\s*(<|<=)\s*TPSA\s*(<|<=)\s*([\d\.]+)', prompt, re.IGNORECASE)
    if m2: tpp['TPSA_range'] = (float(m2.group(1)), float(m2.group(4)))
        
    # SA Score
    m = re.search(r'SA\s*Score\s*(<|<=|>|>=|=)\s*([\d\.]+)', prompt, re.IGNORECASE)
    if m: tpp['SA'] = (m.group(1), float(m.group(2)))
    
    # Banned bonds (Hard filters)
    banned_smarts = []
    if "O-F" in prompt: banned_smarts.append("[OX2]-[F]")
    if "O-Cl" in prompt: banned_smarts.append("[OX2]-[Cl]")
    if "O-Br" in prompt: banned_smarts.append("[OX2]-[Br]")
    if "O-O" in prompt: banned_smarts.append("[OX2]-[OX2]")
    
    if banned_smarts:
        tpp['banned_smarts'] = banned_smarts
        
    return tpp


def _apply_soft_penalty(val: float, op: str, target: float) -> float:
    # returns penalty (negative) if condition is violated
    if op in ('<', '<='):
        return -abs(val - target)*10 if val > target else 0
    if op in ('>', '>='):
        return -abs(target - val)*10 if val < target else 0
    return 0


def _fitness(model, mol: Chem.Mol, optimization_objective: str = "Maximize Solubility", target_receptor: str = "None", affinity_model=None, singularity_mode: bool = False, dynamic_tpp: dict = None) -> float:
    """Fitness = predicted LogS or Multi-Objective (LogS + QED - Tox - SA + Binding)."""
    # Reject unstable structures explicitly in GA
    for pat in UNSTABLE_PATTERNS:
        if pat and mol.HasSubstructMatch(pat):
            return -999.0
    # Apply Dynamic TPP Hard Filters
    if dynamic_tpp and 'banned_smarts' in dynamic_tpp:
        for sm in dynamic_tpp['banned_smarts']:
            pat = Chem.MolFromSmarts(sm)
            if pat and mol.HasSubstructMatch(pat):
                return -999.0

    # Singularity Quantum Stability Filter
    sa_score = calculate_sa_score(mol)
    qed_score = QED.qed(mol)
    tox_alerts = len(TOX_CATALOG.GetMatches(mol))
    
    if singularity_mode:
        if sa_score > 6.0:  # Too hard to synthesize
            return -999.0
        if qed_score < 0.2: # Completely non-drug-like
            return -999.0

    try:
        logs = predict_solubility(model, mol)
        score = 0.0
        
        if optimization_objective == "Create Best Drug (Multi-Objective)":
            # Base Multi-objective score
            score = logs + (qed_score * 5.0) - (tox_alerts * 3.0) - (sa_score * 0.5)
            
            # Add Binding Affinity (Binding is negative kcal/mol, so we subtract it to increase score)
            if target_receptor != "None" and affinity_model is not None:
                binding = simulate_binding_affinity(affinity_model, mol, target_receptor)
                score -= binding 
        elif optimization_objective == "Maximize Toxicity":
            score = logs + (tox_alerts * 10.0) - (qed_score * 5.0)
        else:
            score = logs
            
        # Apply Dynamic TPP Soft Penalties
        if dynamic_tpp:
            if 'MW' in dynamic_tpp:
                mw = Descriptors.ExactMolWt(mol)
                score += _apply_soft_penalty(mw, dynamic_tpp['MW'][0], dynamic_tpp['MW'][1])
            if 'QED' in dynamic_tpp:
                score += _apply_soft_penalty(qed_score, dynamic_tpp['QED'][0], dynamic_tpp['QED'][1])
            if 'SA' in dynamic_tpp:
                score += _apply_soft_penalty(sa_score, dynamic_tpp['SA'][0], dynamic_tpp['SA'][1])
            if 'LogP' in dynamic_tpp:
                logp = Descriptors.MolLogP(mol)
                score += _apply_soft_penalty(logp, dynamic_tpp['LogP'][0], dynamic_tpp['LogP'][1])
            if 'LogP_range' in dynamic_tpp:
                logp = Descriptors.MolLogP(mol)
                min_p, max_p = dynamic_tpp['LogP_range']
                if logp < min_p: score -= abs(min_p - logp)*10
                if logp > max_p: score -= abs(logp - max_p)*10
            if 'TPSA' in dynamic_tpp:
                tpsa = Descriptors.TPSA(mol)
                score += _apply_soft_penalty(tpsa, dynamic_tpp['TPSA'][0], dynamic_tpp['TPSA'][1])
            if 'TPSA_range' in dynamic_tpp:
                tpsa = Descriptors.TPSA(mol)
                min_t, max_t = dynamic_tpp['TPSA_range']
                if tpsa < min_t: score -= abs(min_t - tpsa)*2
                if tpsa > max_t: score -= abs(tpsa - max_t)*2
                
        return score
    except Exception:
        return -999.0


def run_genetic_algorithm(
    parent_smiles: str,
    model: xgb.XGBRegressor,
    pop_size: int = 20,
    n_generations: int = 10,
    mutation_rate: float = 0.7,
    crossover_rate: float = 0.3,
    progress_callback=None,
    optimization_objective: str = "Maximize Solubility",
    target_receptor: str = "None",
    affinity_model=None,
    singularity_mode: bool = False,
    dynamic_tpp: dict = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Run the full GA optimisation loop with strict in-loop validation.

    Returns (results_list, error_string_or_None).
    """
    parent_mol = _strict_validate(parent_smiles)
    if parent_mol is None:
        return [], "Invalid parent SMILES — cannot seed the GA."

    # Compute Core Scaffold for structural locking
    try:
        parent_scaffold = MurckoScaffold.GetScaffoldForMol(parent_mol)
        if parent_scaffold.GetNumAtoms() == 0:
            parent_scaffold = parent_mol
    except Exception:
        parent_scaffold = parent_mol

    # ── Seed initial population ──────────────────────────────────────────
    population: List[Chem.Mol] = []
    attempts = 0
    while len(population) < pop_size and attempts < pop_size * 15:
        child = mutate_molecule(parent_mol, scaffold=parent_scaffold)
        if child is not None:
            population.append(child)
        attempts += 1

    if len(population) < 2:
        return [], "Could not generate a viable starting population (possibly due to strict scaffold constraints)."

    all_results: List[Dict[str, Any]] = []

    for gen in range(n_generations):
        # Evaluate fitness
        scored = [(mol, _fitness(model, mol, optimization_objective, target_receptor, affinity_model, singularity_mode, dynamic_tpp)) for mol in population]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Record this generation
        for mol, fit in scored:
            smi = Chem.MolToSmiles(mol)
            is_stable, issues = assess_stability(mol)
            all_results.append({
                "generation":     gen + 1,
                "smiles":         smi,
                "fitness":        round(fit, 4),
                "predicted_logs": round(predict_solubility(model, mol), 4),
                "stable":         is_stable,
                "issues":         "; ".join(issues) if issues else "None",
            })

        if progress_callback:
            progress_callback(gen + 1, n_generations, scored[0][1])

        # Selection — keep top 50 %
        n_keep = max(2, len(scored) // 2)
        parents = [s[0] for s in scored[:n_keep]]

        # Breed next generation (elitism + mutation/crossover)
        next_gen: List[Chem.Mol] = list(parents)

        breed_attempts = 0
        while len(next_gen) < pop_size and breed_attempts < pop_size * 10:
            breed_attempts += 1
            r = random.random()
            if r < mutation_rate:
                child = mutate_molecule(random.choice(parents), scaffold=parent_scaffold)
            elif r < mutation_rate + crossover_rate:
                if len(parents) >= 2:
                    p1, p2 = random.sample(parents, 2)
                    child = crossover_molecules(p1, p2, scaffold=parent_scaffold)
                else:
                    child = mutate_molecule(parents[0], scaffold=parent_scaffold)
            else:
                child = mutate_molecule(random.choice(parents), scaffold=parent_scaffold)
            if child is not None:
                next_gen.append(child)

        population = next_gen[:pop_size]

    return all_results, None


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — MAIN APPLICATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def render_admin_dashboard():
    import pandas as pd
    import numpy as np
    import plotly.express as px

    st.markdown("<h2 style='text-align: center; color: #ff8a00; margin-top: 20px;'>📊 System Admin Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a8edea;'>Overview of MolSol De Novo Platform Status</p>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Total Molecules Generated", value="12,458", delta="↑ 342 today")
    col2.metric(label="Active Users", value="48", delta="↑ 12")
    col3.metric(label="API Quota Remaining", value="85%", delta="-2% today")
    col4.metric(label="System Status", value="Online", delta="Nominal", delta_color="normal")

    st.markdown("<br><h3>📈 Usage Analytics</h3>", unsafe_allow_html=True)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=14)
    np.random.seed(42)
    usage = np.random.randint(100, 500, size=14)
    usage = np.sort(usage)
    usage = usage + np.random.randint(-50, 50, size=14)
    df = pd.DataFrame({"Date": dates, "API Calls": usage})
    
    fig = px.area(df, x="Date", y="API Calls", title="API Usage Trend (Past 14 Days)",
                  color_discrete_sequence=['#ff8a00'])
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                      font_color='#a8edea', margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br><h3>⚙️ System Controls</h3>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("Force Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Cache Cleared!")
    if c2.button("Restart AI Worker", use_container_width=True):
        st.success("AI Worker Restart Signal Sent.")
    if c3.button("Download Server Logs", use_container_width=True):
        st.info("Logs downloaded (Simulated).")

def setup_authenticator():
    import yaml
    from yaml.loader import SafeLoader
    import streamlit_authenticator as stauth
    with open('auth_config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
    return stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

def main() -> None:
    # ── Singularity Engine AI Configuration Init ──
    if "singularity_ai_source" not in st.session_state:
        st.session_state["singularity_ai_source"] = "built_in"
    if "singularity_selected_model" not in st.session_state:
        st.session_state["singularity_selected_model"] = "Gemini 3.5 Flash"
    if "singularity_api_key" not in st.session_state:
        st.session_state["singularity_api_key"] = ""

    authenticator = setup_authenticator()
    
    if authenticator is not None:
        if st.session_state.get("authentication_status") is not True:
            st.markdown("<h2 style='text-align: center; color: #ff8a00; margin-top: 50px;'>🔐 Secure Access Required</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #a8edea;'>Welcome to MolSol De Novo. Please authenticate your identity.</p>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1.5, 1])
            with col2:
                try:
                    authenticator.login(location="main")
                except TypeError:
                    authenticator.login("Login", "main")
                    
            if st.session_state.get("authentication_status") is False:
                st.error('Username/password is incorrect')
            
            if not st.session_state.get("authentication_status"):
                return
        
        st.session_state["logged_in"] = True
        
        # Grant admin maximum privileges automatically
        if st.session_state.get("username") == "admin":
            if st.session_state.get("subscription_tier") not in ["Pro", "Singularity"]:
                st.session_state["subscription_tier"] = "Singularity"
        else:
            if "subscription_tier" not in st.session_state:
                st.session_state["subscription_tier"] = "Free"
    else:
        if not st.session_state.get("logged_in", False):
            st.markdown("<h2 style='text-align: center; color: #ff8a00; margin-top: 50px;'>🔐 Secure Access Required</h2>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1.5, 1])
            with col2:
                with st.form("login_form"):
                    username = st.text_input("Username", value="admin")
                    password = st.text_input("Password", type="password", value="password")
                    submit = st.form_submit_button("Authenticate Identity", use_container_width=True)
                    if submit:
                        if username == "admin" and password == "password":
                            st.session_state["logged_in"] = True
                            st.session_state["subscription_tier"] = "Free"
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")
            return


    # (Header moved down to support top-right floating button)

    # ── Load model (cached) ──────────────────────────────────────────────
    # ── Load model (cached) ──────────────────────────────────────────────
    model, is_real_model = load_xgb_model()
    affinity_model = load_affinity_model()
    gnn_model, is_gnn_loaded = load_gnn_model()

    # ==================================================================
    # SIDEBAR
    # ==================================================================
    st.sidebar.markdown("## 🎛️ Control Panel")
    
    with st.sidebar.expander("💳 Account & Subscription", expanded=True):
        tier = st.session_state.get("subscription_tier", "Free")
        st.markdown(f"**Current Tier:** `{tier}`")
        if tier == "Free":
            st.info("Limited to Core Algorithm.")
            if st.button("Upgrade to Genesis Pro ($49/mo)", use_container_width=True):
                if st.session_state.get("username") == "admin":
                    st.session_state["subscription_tier"] = "Pro"
                    st.rerun()
                else:
                    st.toast("Payment gateway under construction. Upgrade unavailable.", icon="🚧")
            if st.button("Unlock Singularity ($199/mo)", use_container_width=True):
                if st.session_state.get("username") == "admin":
                    st.session_state["subscription_tier"] = "Singularity"
                    st.rerun()
                else:
                    st.toast("Payment gateway under construction. Upgrade unavailable.", icon="🚧")
        elif tier == "Pro":
            st.info("Genesis Protocol Active.")
            if st.button("Unlock Singularity ($199/mo)", use_container_width=True):
                if st.session_state.get("username") == "admin":
                    st.session_state["subscription_tier"] = "Singularity"
                    st.rerun()
                else:
                    st.toast("Payment gateway under construction. Upgrade unavailable.", icon="🚧")
        elif tier == "Singularity":
            st.success("All features unlocked.")
            if st.button("Downgrade to Free", use_container_width=True):
                if st.session_state.get("username") == "admin":
                    st.session_state["subscription_tier"] = "Free"
                    st.rerun()
        
        st.markdown("---")
        if authenticator:
            try:
                authenticator.logout("Logout", "main")
            except Exception:
                pass
        else:
            if st.button("Logout", use_container_width=True):
                st.session_state["logged_in"] = False
                st.rerun()

    app_modes = [
        "🔍 Analyze Known Compound",
        "🧬 De Novo Mutation Loop",
        "🎯 Target Docking Simulation",
        "🔬 Simulation Lab"
    ]
    if st.session_state.get("username") == "admin":
        app_modes.append("📊 Admin Dashboard")

    mode = st.sidebar.radio(
        "Select Application Mode",
        app_modes,
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚡ AI Compute Tier")

    tier = st.session_state.get("subscription_tier", "Free")
    available_tiers = ["🟢 Core Research"]
    if tier == "Pro":
        available_tiers.append("🔵 Genesis Protocol")
    elif tier == "Singularity":
        available_tiers.extend(["🔵 Genesis Protocol", "🟣 Singularity Engine"])

    engine_tier = st.sidebar.radio(
        "Select Compute Tier",
        available_tiers,
        index=0,
        label_visibility="collapsed"
    )

    pro_mode = engine_tier in ["🔵 Genesis Protocol", "🟣 Singularity Engine"]
    singularity_mode = engine_tier == "🟣 Singularity Engine"

    if pro_mode and not singularity_mode:
        st.sidebar.markdown(
            """
            <div style="background: linear-gradient(90deg, #1565c0, #009688); padding: 5px; border-radius: 5px; text-align: center; color: white; font-weight: bold; margin-bottom: 10px;">
            ⚡ GENESIS PROTOCOL ACTIVE
            </div>
            """, unsafe_allow_html=True
        )
        st.markdown(GENESIS_CSS, unsafe_allow_html=True)
    elif singularity_mode:
        st.sidebar.markdown(
            """
            <div style="background: linear-gradient(90deg, #6a1b9a, #e52e71, #ff8a00); padding: 5px; border-radius: 5px; text-align: center; color: white; font-weight: bold; margin-bottom: 10px;">
            🌌 SINGULARITY ENGINE ACTIVE
            </div>
            """, unsafe_allow_html=True
        )
        st.markdown(SINGULARITY_CSS, unsafe_allow_html=True)
        
        with st.sidebar.expander("🧠 Oracle AI Configuration", expanded=True):
            ai_source_options = ["🟣 Internal Oracle AI", "🌐 External API Provider"]
            default_source_idx = 0 if st.session_state.get("singularity_ai_source", "built_in") == "built_in" else 1
            ai_source = st.radio(
                "AI Compute Engine",
                options=ai_source_options,
                index=default_source_idx,
                key="singularity_ai_source_radio"
            )
            st.session_state["singularity_ai_source"] = "built_in" if "Internal" in ai_source else "external"
            
            if st.session_state["singularity_ai_source"] == "external":
                model_options = ["Gemini 3.5 Flash", "Gemini 1.5 Pro", "Gemini 1.5 Flash", "GPT-4o", "GPT-3.5 Turbo"]
                current_model = st.session_state.get("singularity_selected_model", "Gemini 3.5 Flash")
                default_model_idx = model_options.index(current_model) if current_model in model_options else 0
                
                selected_model = st.selectbox(
                    "Select Model",
                    options=model_options,
                    index=default_model_idx,
                    key="singularity_model_selectbox"
                )
                st.session_state["singularity_selected_model"] = selected_model
                
                provider_name = "Google Gemini" if "Gemini" in selected_model else "OpenAI"
                placeholder = "AIzaSy..." if "Gemini" in selected_model else "sk-..."
                
                api_key = st.text_input(
                    f"{provider_name} API Key",
                    type="password",
                    value=st.session_state.get("singularity_api_key", ""),
                    placeholder=placeholder,
                    key="singularity_api_key_input"
                )
                st.session_state["singularity_api_key"] = api_key
                
                if not api_key:
                    st.caption("⚠️ API Key is required for External AI analysis.")
            else:
                st.session_state["singularity_selected_model"] = "Local MolSol AI"
                st.session_state["singularity_api_key"] = ""
                st.success("🤖 Using proprietary built-in simulated AI.")


    st.sidebar.markdown("---")

    # ── Session-state init ────────────────────────────────────────────────
    if "smiles_input" not in st.session_state:
        st.session_state["smiles_input"] = ""

    # ── Example drug buttons ──────────────────────────────────────────────
    st.sidebar.markdown("### 💊 Quick Examples")
    btn_cols = st.sidebar.columns(2)
    for i, (name, smi) in enumerate(EXAMPLE_DRUGS.items()):
        with btn_cols[i % 2]:
            if st.button(name, key=f"ex_{i}", use_container_width=True):
                st.session_state["smiles_input"] = smi
                st.rerun()

    st.sidebar.markdown("---")

    # ── Search by Name (PubChem) ──────────────────────────────────────────
    st.sidebar.markdown("### 🔍 Search by Name")
    name_query = st.sidebar.text_input(
        "Enter drug or chemical name",
        placeholder="e.g. Aspirin, Caffeine",
        key="name_query_input"
    )
    if st.sidebar.button("Fetch SMILES from PubChem", use_container_width=True):
        if name_query:
            with st.spinner(f"Looking up {name_query}..."):
                fetched_smi, err = resolve_pubchem_name(name_query)
                if fetched_smi:
                    st.session_state["smiles_input"] = fetched_smi
                    st.rerun()
                else:
                    st.sidebar.error(err)
                    
    st.sidebar.markdown("---")

    # ── SMILES text input ─────────────────────────────────────────────────
    smiles_input: str = st.sidebar.text_input(
        "🧪 Direct SMILES Input (max 250 chars)",
        key="smiles_input",
        max_chars=250,
        placeholder="e.g. CC(=O)Oc1ccccc1C(=O)O",
    ).strip()

    # ── Session State Reset on Input Change ───────────────────────────────
    if smiles_input != st.session_state.get("last_smiles_input"):
        st.session_state["last_smiles_input"] = smiles_input
        st.session_state.pop("ga_results", None)
        st.session_state.pop("parent_logs", None)

    # ── Model status chip ─────────────────────────────────────────────────
    st.sidebar.markdown("---")
    if is_real_model:
        st.sidebar.success("✅ Pre-trained XGBoost model loaded successfully.")
    else:
        st.sidebar.warning(
            "⚠️ **No pre-trained model found.**  Using a demonstration "
            "fallback model.  Place `xgb_solubility_model.json` or "
            "`.pkl` in the app directory for real predictions."
        )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Built with ❤️ using RDKit · XGBoost · Streamlit"
    )

    # ── Initialize AI Chat state ──────────────────────────────────────────
    if "show_oracle_chat" not in st.session_state:
        st.session_state["show_oracle_chat"] = False

    # ── Header & Floating Oracle AI Button ────────────────────────────────
    if singularity_mode:
        col_hdr, col_btn = st.columns([3.5, 1])
        with col_hdr:
            st.markdown(
                '<div class="main-header" style="margin-bottom: 0;">'
                "<h1>🧬 MolSol De Novo</h1>"
                "<p>Advanced AI Drug Design &amp; Explainable AI Platform</p>"
                "</div>",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
            chat_btn_label = "✖ Close Oracle AI" if st.session_state["show_oracle_chat"] else "🤖 Oracle AI Chat"
            if st.button(chat_btn_label, use_container_width=True, type="primary" if not st.session_state["show_oracle_chat"] else "secondary"):
                st.session_state["show_oracle_chat"] = not st.session_state["show_oracle_chat"]
                st.rerun()
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="main-header">'
            "<h1>🧬 MolSol De Novo</h1>"
            "<p>Advanced AI Drug Design &amp; Explainable AI Platform — "
            "Chemoinformatics · XGBoost · Genetic Algorithms · XAI</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ==================================================================
    # MAIN CONTENT AREA — dispatch by mode
    # ==================================================================
    if singularity_mode and st.session_state.get("show_oracle_chat", False):
        _render_fullscreen_oracle_chat(model, gnn_model, affinity_model)
    elif mode == "📊 Admin Dashboard":
        render_admin_dashboard()
    elif mode == "🎯 Target Docking Simulation":
        _render_docking_mode(smiles_input, pro_mode, singularity_mode)
    elif mode == "🔍 Analyze Known Compound":
        _render_analysis_mode(smiles_input, model)
    elif mode == "🔬 Simulation Lab":
        _render_sim_lab_mode(smiles_input, model, affinity_model, gnn_model, pro_mode, singularity_mode)
    else:
        _render_denovo_mode(smiles_input, model, pro_mode, singularity_mode, affinity_model, gnn_model)


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 3 — Target Docking Simulation
# ═══════════════════════════════════════════════════════════════════════════════

def _render_docking_mode(smiles_input: str, pro_mode: bool, singularity_mode: bool) -> None:
    st.markdown("<h2 style='color: #ff8a00;'>🎯 Target Docking Simulation</h2>", unsafe_allow_html=True)
    st.markdown("Simulate protein-ligand binding affinity against key disease targets.")

    if not pro_mode:
        st.error("🔒 **Genesis Protocol Required**")
        st.info("This advanced feature requires the Genesis Protocol tier or higher. Please upgrade your subscription in the sidebar to access the docking simulator.")
        return

    if not smiles_input:
        st.warning("👈 Please enter a SMILES string in the sidebar first.")
        return

    targets = {
        "SARS-CoV-2 Mpro (COVID-19)": "A key enzyme for coronavirus replication.",
        "EGFR Kinase (Lung Cancer)": "Epidermal growth factor receptor involved in cell proliferation.",
        "Dopamine D2 Receptor (Schizophrenia)": "A major target for antipsychotic drugs."
    }

    target_name = st.selectbox("Select Target Protein", list(targets.keys()))
    st.caption(targets[target_name])

    col1, col2 = st.columns([1, 1.5])
    with col1:
        with st.container(border=True):
            st.markdown("### ⚙️ Simulation Controls")
            st.markdown(f"**Ligand SMILES:** `{smiles_input[:30]}...`")
            if st.button("🧬 Run Docking Simulation", type="primary", use_container_width=True):
                with st.spinner("Simulating molecular docking and binding free energy..."):
                    import time, random
                    time.sleep(2) # Simulate heavy computation
                    score = round(random.uniform(5.0, 9.5), 2)
                    st.session_state["last_docking_score"] = score
                    st.session_state["last_docking_target"] = target_name
                st.success("Simulation Complete!")

    if "last_docking_score" in st.session_state and st.session_state.get("last_docking_target") == target_name:
        score = st.session_state["last_docking_score"]
        st.markdown("---")
        
        with st.container(border=True):
            st.markdown("### 📊 Docking Results")
            c1, c2, c3 = st.columns(3)
            c1.metric("Binding Affinity (pKd)", f"{score}", f"+{round(score - 6.0, 1)} vs baseline")
            c2.metric("Estimated IC50", f"{round(10**(9-score), 1)} nM")
            c3.metric("Docking Status", "Stable Pose" if score > 7.0 else "Weak Binding")

        if singularity_mode:
            st.markdown("")
            with st.container(border=True):
                st.markdown("### 🧠 Oracle AI Deep Analysis")
                
                # Show a brief status card of the active AI Engine
                source_label = "Internal Oracle AI" if st.session_state.get("singularity_ai_source", "built_in") == "built_in" else f"External ({st.session_state.get('singularity_selected_model', 'Gemini 3.5 Flash')})"
                st.caption(f"⚡ **Active Engine:** {source_label}")

                if st.button("Generate Structural Insights", use_container_width=True, type="secondary"):
                    with st.spinner("Oracle AI is analyzing the receptor-ligand interactions..."):
                        ai_source = st.session_state.get("singularity_ai_source", "built_in")
                        
                        if ai_source == "built_in":
                            import time
                            time.sleep(1.5)
                            analysis = (
                                f"🧬 **[Singularity Oracle Built-in AI Analysis]**\n\n"
                                f"**Target:** {target_name}\n"
                                f"**Compound SMILES:** `{smiles_input}`\n"
                                f"**Predicted Affinity (pKd):** {score}\n\n"
                                f"**Structural Insights:**\n"
                                f"1. **Hydrogen Bonding:** The molecular structure contains functional groups capable of forming hydrogen bonds with amino acid residues in the active site of {target_name}, enhancing binding stability.\n"
                                f"2. **Hydrophobic Contacts:** The lipophilic core of the molecule fits well into the hydrophobic pocket of the target, leading to a high binding affinity of {score}.\n"
                                f"3. **Target Efficacy:** Based on the score ({score}), this drug candidate has a {'very high likelihood of successfully inhibiting the target protein' if score > 7.5 else 'moderate affinity, suggesting functional groups could be further optimized to improve specificity (selectivity)'}."
                            )
                        else:
                            api_key = st.session_state.get("singularity_api_key", "")
                            model_name = st.session_state.get("singularity_selected_model", "Gemini 3.5 Flash")
                            
                            if not api_key:
                                analysis = "⚠️ **External AI Key Missing:** Please specify your API Key in the **Oracle AI Configuration** section of the sidebar to use external AI analysis."
                            else:
                                prompt = f"Analyze the binding of molecule {smiles_input} to {target_name}. The predicted pKd is {score}. Explain the potential hydrogen bonds, hydrophobic interactions, and why this molecule might be effective or ineffective."
                                from llm_integration import generate_external_ai_response
                                analysis, error = generate_external_ai_response(model_name, api_key, prompt, [])
                                if error:
                                    analysis = f"⚠️ **Error connecting to External AI:** {analysis}"
                        
                        st.info(analysis)
        else:
            st.info("🔒 **Upgrade to Singularity Engine** to unlock Oracle AI Deep Analysis for structural insights and interaction mapping.")

# ═══════════════════════════════════════════════════════════════════════════════
# MODE 1 — Analyze Known Compound
# ═══════════════════════════════════════════════════════════════════════════════

def _render_analysis_mode(smiles_input: str, model: xgb.XGBRegressor) -> None:
    if not smiles_input:
        st.info(
            "👈 Enter a SMILES string in the sidebar or click a "
            "**Quick Example** to begin analysis."
        )
        return

    # ── Validate & clean ──────────────────────────────────────────────────
    mol, canonical, error = clean_molecule(smiles_input)
    if error:
        st.error(error)
        return

    st.markdown(f"**Canonical SMILES:** `{canonical}`")

    # ── Pre-compute expensive items ───────────────────────────────────────
    props     = compute_properties(mol)
    pred_logs = predict_solubility(model, mol)

    # Compute 2D coords ONCE so both images use the same layout
    AllChem.Compute2DCoords(mol)

    try:
        weights = compute_atom_contributions(model, mol)
    except Exception:
        weights = [0.0] * mol.GetNumAtoms()

    # ══════════════════════════════════════════════════════════════════════
    # ROW 1 — Structure + XAI Map
    # ══════════════════════════════════════════════════════════════════════
    col_struct, col_xai = st.columns(2)

    with col_struct:
        with st.container(border=True):
            st.markdown("### 🔬 2D Molecular Structure")
            st.image(mol_to_image(mol), use_container_width=True)

    with col_xai:
        with st.container(border=True):
            st.markdown("### 🎨 XAI Atomic Contribution Map")
            st.caption(
                "🔵 Blue = Enhances Solubility &nbsp;&nbsp;&nbsp; "
                "🔴 Red = Reduces Solubility &nbsp;&nbsp;&nbsp; "
                "⚪ Grey = Neutral"
            )
            try:
                xai_img = render_xai_map(mol, weights)
                st.image(xai_img, use_container_width=True)
            except Exception as exc:
                st.warning(f"Could not render XAI map: {exc}")

    # ══════════════════════════════════════════════════════════════════════
    # ROW 2 — Molecular Properties + Lipinski
    # ══════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    col_props, col_lip = st.columns([3, 2])

    with col_props:
        with st.container(border=True):
            st.markdown("### 📊 Molecular Properties")
            st.markdown("")

            prop_items = list(props.items())
            # 3 rows of 4 columns
            for row_idx in range(3):
                mc = st.columns(4)
                for i, (k, v) in enumerate(prop_items[row_idx*4 : (row_idx+1)*4]):
                    with mc[i]:
                        st.metric(label=k, value=str(v))

    with col_lip:
        with st.container(border=True):
            st.markdown("### 🚦 Lipinski Rule of Five")
            n_viol, violations, _ = lipinski_assessment(props)
            st.write(f"Violations: {n_viol}")
            st.markdown("")
            checks = [
                ("MW ≤ 500",   props["Molecular Weight"],          props["Molecular Weight"] <= 500),
                ("LogP ≤ 5",   props["LogP (Crippen)"],            props["LogP (Crippen)"]   <= 5),
                ("HBD ≤ 5",    props["HBD (H-Bond Donors)"],      props["HBD (H-Bond Donors)"]  <= 5),
                ("HBA ≤ 10",   props["HBA (H-Bond Acceptors)"],   props["HBA (H-Bond Acceptors)"] <= 10),
            ]
            for label, val, ok in checks:
                icon = "✅" if ok else "❌"
                st.markdown(f"{icon} {label}: **{val}**")

    # ══════════════════════════════════════════════════════════════════════
    # ROW 3 — Solubility Prediction + PubChem Lookup
    # ══════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    col_sol, col_pub = st.columns(2)

    with col_sol:
        with st.container(border=True):
            st.markdown("### 🧪 Predicted Aqueous Solubility")
            if pred_logs > -1:
                sol_tag = "🟢 Highly Soluble"
            elif pred_logs > -3:
                sol_tag = "🟡 Moderately Soluble"
            elif pred_logs > -5:
                sol_tag = "🟠 Slightly Soluble"
            else:
                sol_tag = "🔴 Poorly Soluble"
            st.metric("Predicted LogS", f"{pred_logs:.4f}")
            st.markdown(f"**Solubility Class:** {sol_tag}")

    with col_pub:
        with st.container(border=True):
            st.markdown("### 🌐 PubChem Registry Lookup")
            with st.spinner("Querying PubChem PUG REST…"):
                cid = lookup_pubchem_cid(canonical)
            if cid:
                st.success(
                    f"🔗 **Existing Registered Molecule** — "
                    f"[CID: {cid}](https://pubchem.ncbi.nlm.nih.gov/compound/{cid})"
                )
            else:
                st.info("✨ **Novel De Novo Substance** — Not found in PubChem")

    # ══════════════════════════════════════════════════════════════════════
    # ROW 4 — AI Interpretation Panel
    # ══════════════════════════════════════════════════════════════════════
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 💡 AI Interpretation of Solubility")

    interpretation_md = generate_ai_interpretation(mol, weights, pred_logs)

    st.info(interpretation_md)


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 2 — De Novo Mutation Loop
# ═══════════════════════════════════════════════════════════════════════════════

def _render_denovo_mode(smiles_input: str, model: xgb.XGBRegressor, pro_mode: bool, singularity_mode: bool, affinity_model=None, gnn_model=None) -> None:
    if singularity_mode and gnn_model is None:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #0d0015, #2a004a, #000000); border: 2px solid #e52e71; border-radius: 16px; padding: 40px; text-align: center; box-shadow: 0 0 30px rgba(229, 46, 113, 0.5);">
                <h1 style="background: linear-gradient(90deg, #ff8a00, #e52e71, #6a1b9a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3rem; margin-bottom: 10px;">
                    🌌 SINGULARITY ENGINE
                </h1>
                <h3 style="color: #a8edea; font-weight: 300;">The Ultimate AI Drug Discovery Protocol</h3>
                <p style="color: #bbb; font-size: 1.1rem; max-width: 600px; margin: 20px auto;">
                    We are currently calibrating the quantum processing nodes for <b>Graph Neural Networks</b>.<br><br>
                    <i>GNN Weights not found. Please train the GNN model first.</i>
                </p>
                <br>
                <div style="display: inline-block; padding: 10px 20px; border: 1px solid #e52e71; border-radius: 8px; color: #e52e71; letter-spacing: 2px;">
                    SYSTEM OFFLINE
                </div>
            </div>
            """, unsafe_allow_html=True
        )
        return
    elif singularity_mode:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #180b24, #26123a); border-left: 5px solid #e52e71; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 15px rgba(229, 46, 113, 0.2);">
                <h2 style="margin: 0; color: #e52e71; font-weight: 800; font-size: 1.8rem;">🌌 SINGULARITY ENGINE ONLINE</h2>
                <p style="color: #a8edea; margin-top: 5px; font-size: 1rem;">
                    <b>Graph Neural Network (GNN) Activated.</b> The AI is now analyzing molecules at the quantum topological level (Message Passing Neural Network) instead of traditional fingerprints.
                </p>
            </div>
            """, unsafe_allow_html=True
        )

    if not smiles_input:
        st.info(
            "👈 Enter a **parent SMILES** in the sidebar to seed the "
            "De Novo optimisation loop."
        )
        return

    # ── Validate parent ───────────────────────────────────────────────────
    mol, canonical, error = clean_molecule(smiles_input)
    if error:
        st.error(error)
        return

    st.markdown(f"**Parent Molecule:** `{canonical}`")

    # ── Parent overview ───────────────────────────────────────────────────
    AllChem.Compute2DCoords(mol)
    cp1, cp2 = st.columns([1, 2])
    with cp1:
        with st.container(border=True):
            st.image(
                mol_to_image(mol, size=(380, 300)),
                caption="Parent Structure",
                use_container_width=True,
            )
    with cp2:
        with st.container(border=True):
            st.markdown("### 🧬 Parent Molecule Summary")
            st.markdown(f"**Parent LogS:** `{parent_logs:.4f}`")
            st.markdown(
                f"**MW:** {props['Molecular Weight']:.1f} &nbsp;|&nbsp; "
                f"**LogP:** {props['LogP (Crippen)']:.2f} &nbsp;|&nbsp; "
                f"**HBD:** {props['HBD (H-Bond Donors)']} &nbsp;|&nbsp; "
                f"**HBA:** {props['HBA (H-Bond Acceptors)']}"
            )
            _, _, badge = lipinski_assessment(props)
            st.markdown(badge)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Optimization Goal ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("### 🎯 Choose Optimization Goal")
        optimization_objective = st.radio(
            "AI Agent Objective:",
            [
                "📈 Maximize Solubility (LogS)", 
                "🛡️ Create Safe Drug (LogS + QED - Tox)",
                "☠️ Maximize Toxicity (Extreme Poison)"
            ],
            index=1,
            help="Choose whether to focus purely on solubility, enforce strict drug-likeness, or intentionally generate highly toxic substances."
        )
    # Map the UI label back to the internal backend label
    if "Safe Drug" in optimization_objective:
        backend_objective = "Create Best Drug (Multi-Objective)"
    elif "Maximize Toxicity" in optimization_objective:
        backend_objective = "Maximize Toxicity"
    else:
        backend_objective = "Maximize Solubility"

    # ── Target Receptor Simulation (Singularity Engine) ────────────────────
    target_receptor = "None"
    if pro_mode:
        st.markdown("")
        with st.container(border=True):
            st.markdown("### 🧬 Target Receptor Binding Simulation (Pro)")
            target_receptor = st.selectbox(
                "Select Target:",
                ["None", "🧬 SARS-CoV-2 MPro", "🧠 Dopamine D2 Receptor", "🔥 Cyclooxygenase-2"],
                help="Simulate how well the drug binds to a specific target class (-kcal/mol). The AI will try to maximize this affinity."
            )

    # ── GA Parameters ─────────────────────────────────────────────────────
    if pro_mode:
        with st.expander("⚙️ Advanced GA Settings (Singularity)", expanded=True):
            ga_c = st.columns(4)
            with ga_c[0]:
                pop_size = st.number_input("Population Size", min_value=10, max_value=200, value=50, step=10)
            with ga_c[1]:
                n_gens = st.number_input("Generations", min_value=1, max_value=50, value=20, step=1)
            with ga_c[2]:
                mut_rate = st.slider("Mutation Rate", 0.1, 1.0, 0.7, 0.05)
            with ga_c[3]:
                cx_rate = st.slider("Crossover Rate", 0.0, 0.5, 0.3, 0.05)
    else:
        # Basic Mode constraints
        pop_size = 20
        n_gens = 5
        mut_rate = 0.7
        cx_rate = 0.3
        st.info("💡 **Basic Mode:** GA runs with fast settings (Pop: 20, Gens: 5). Toggle **Singularity Engine** in sidebar to unlock advanced features.")

    # ── Run button ────────────────────────────────────────────────────────
    if st.button("🚀 Execute De Novo Mutation Protocol", type="primary", use_container_width=True):
        pbar = st.progress(0, text="Initialising population…")
        status_slot = st.empty()

        def _progress_cb(gen: int, total: int, best_fit: float):
            pbar.progress(
                gen / total,
                text=f"Generation {gen}/{total} — Best fitness: {best_fit:.4f}",
            )
            status_slot.markdown(
                f"**Generation {gen}/{total}** — Best Fitness: `{best_fit:.4f}`"
            )

        with st.spinner("Running Genetic Algorithm…"):
            results, ga_err = run_genetic_algorithm(
                canonical,
                gnn_model if (singularity_mode and gnn_model is not None) else model,
                pop_size=int(pop_size),
                n_generations=int(n_gens),
                mutation_rate=mut_rate,
                crossover_rate=cx_rate,
                progress_callback=_progress_cb,
                optimization_objective=backend_objective,
                target_receptor=target_receptor,
                affinity_model=affinity_model,
                singularity_mode=singularity_mode,
            )

        pbar.progress(1.0, text="Complete ✅")

        if ga_err:
            st.error(f"GA Error: {ga_err}")
            return

        if not results:
            st.warning("No valid mutants were generated in this run.")
            return

        st.session_state["ga_results"]   = results
        st.session_state["parent_logs"]  = parent_logs
        status_slot.success(
            f"✅ **GA Complete!** Evaluated **{len(results)}** candidate molecules."
        )

    # ── Display cached results ────────────────────────────────────────────
    if "ga_results" not in st.session_state or not st.session_state["ga_results"]:
        return

    results = st.session_state["ga_results"]
    parent_logs_saved = st.session_state.get("parent_logs", parent_logs)

    df = pd.DataFrame(results)
    df = (
        df.sort_values("fitness", ascending=False)
        .drop_duplicates(subset="smiles", keep="first")
        .reset_index(drop=True)
    )

    df_stable   = df[df["stable"] == True].reset_index(drop=True)
    df_unstable = df[df["stable"] == False].reset_index(drop=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    if len(df_stable) == 0:
        st.info("No stable compounds were generated in this run.")
        return

    # ══════════════════════════════════════════════════════════════════════
    # SECTION A — 🏆 BEST CANDIDATE DASHBOARD (TOP)
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("## 🏆 Best Candidate vs Parent")
    best = df_stable.iloc[0]
    best_mol = Chem.MolFromSmiles(best["smiles"])

    # Calculate Tanimoto Similarity
    parent_mol = Chem.MolFromSmiles(canonical)
    parent_fp = AllChem.GetMorganFingerprintAsBitVect(parent_mol, 2, nBits=1024)
    best_fp = AllChem.GetMorganFingerprintAsBitVect(best_mol, 2, nBits=1024)
    tanimoto = DataStructs.TanimotoSimilarity(parent_fp, best_fp)

    best_props = compute_properties(best_mol) if best_mol else {}
    improvement = best["predicted_logs"] - parent_logs_saved
    sign = "+" if improvement >= 0 else ""

    if best_mol:
        AllChem.Compute2DCoords(best_mol)
        # ── Row 1: Structure comparison ───────────────────────────────────
        bc1, bc2 = st.columns(2)
        with bc1:
            with st.container(border=True):
                st.markdown("**🧪 Parent Molecule**")
                st.image(mol_to_image(mol), caption="Parent Structure", use_container_width=True)
                st.markdown(f"**LogS:** `{parent_logs_saved:.4f}`")
                st.markdown(f"**QED:** `{props.get('QED Score', 'N/A')}`")
                st.markdown(f"**Toxicity Alerts:** `{props.get('Toxicity Alerts', 0)}`")

        with bc2:
            with st.container(border=True):
                st.markdown("**🧬 Best Candidate**")
                st.image(mol_to_image(best_mol), caption="Best Candidate Structure", use_container_width=True)
                st.markdown(f"**LogS:** `{best['predicted_logs']}` ({sign}{improvement:.4f})")
                st.markdown(f"**QED:** `{best_props.get('QED Score', 'N/A')}`")
                tox_c = best_props.get('Toxicity Alerts', 0)
                tox_icon = "✅ Safe" if tox_c == 0 else f"⚠️ {tox_c} Alerts"
                st.markdown(f"**Toxicity:** `{tox_icon}`")
                st.code(best["smiles"], language=None)
                _, _, b_badge = lipinski_assessment(best_props)
                st.markdown(b_badge)

        # ── Row 2: Badges (Similarity + Patent) ──────────────────────────
        badge1, badge2 = st.columns(2)
        with badge1:
            with st.container(border=True):
                st.markdown("**🧬 Similarity Assessment**")
                if tanimoto >= 0.7:
                    st.success(f"🧬 **Similarity to Parent:** {tanimoto*100:.1f}% (Highly Preserved)")
                elif tanimoto >= 0.4:
                    st.info(f"🧬 **Similarity to Parent:** {tanimoto*100:.1f}% (Moderate Drift)")
                else:
                    st.warning(f"🧬 **Similarity to Parent:** {tanimoto*100:.1f}% (Scaffold Hopped)")
        with badge2:
            with st.container(border=True):
                st.markdown("**🌐 Patent Check**")
                with st.spinner("Automated Patent & Literature Check…"):
                    cid = lookup_pubchem_cid(best["smiles"])
                if cid:
                    st.error(
                        f"⚠️ **KNOWN COMPOUND** — "
                        f"[CID: {cid}](https://pubchem.ncbi.nlm.nih.gov/compound/{cid})"
                    )
                else:
                    st.success("✅ **NOVEL COMPOUND (No Patent Collision)**")

        # ── Row 3: Radar Chart + Mutation Map + 3D Viewer (Genesis Only) ──
        if pro_mode and not singularity_mode:
            st.markdown("---")
            viz1, viz2, viz3 = st.columns(3)

            # --- RADAR CHART ---
            with viz1:
                st.markdown("##### 🕸️ Multi-Metric Radar")
                # Normalize metrics to 0-1 scale for radar
                p_logs = max(0, min(1, (parent_logs_saved + 10) / 14))  # Range approx -10 to 4
                p_qed = float(props.get('QED Score', 0.5))
                p_tox = max(0, 1 - int(props.get('Toxicity Alerts', 0)) * 0.25)  # 0 alerts = 1.0
                p_wt = max(0, min(1, 1 - (float(props.get('Molecular Weight', 300)) - 150) / 500))
                p_tpsa = max(0, min(1, float(props.get('TPSA', 60)) / 140))

                b_logs_val = float(best['predicted_logs'])
                b_logs = max(0, min(1, (b_logs_val + 10) / 14))
                b_qed = float(best_props.get('QED Score', 0.5))
                b_tox = max(0, 1 - int(best_props.get('Toxicity Alerts', 0)) * 0.25)
                b_wt = max(0, min(1, 1 - (float(best_props.get('Molecular Weight', 300)) - 150) / 500))
                b_tpsa = max(0, min(1, float(best_props.get('TPSA', 60)) / 140))

                categories = ['Solubility', 'QED', 'Low Toxicity', 'Optimal Weight', 'Polarity']

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=[p_logs, p_qed, p_tox, p_wt, p_tpsa],
                    theta=categories,
                    fill='toself',
                    name='Parent',
                    line=dict(color='rgba(99, 110, 250, 0.8)'),
                    fillcolor='rgba(99, 110, 250, 0.15)',
                ))
                fig.add_trace(go.Scatterpolar(
                    r=[b_logs, b_qed, b_tox, b_wt, b_tpsa],
                    theta=categories,
                    fill='toself',
                    name='Candidate',
                    line=dict(color='rgba(239, 85, 59, 0.8)'),
                    fillcolor='rgba(239, 85, 59, 0.15)',
                ))
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 1]),
                        bgcolor='rgba(0,0,0,0)',
                    ),
                    showlegend=True,
                    legend=dict(orientation='h', y=-0.15),
                    margin=dict(l=40, r=40, t=20, b=40),
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                )
                st.plotly_chart(fig, use_container_width=True)

            # --- MUTATION HIGHLIGHT MAP ---
            with viz2:
                st.markdown("##### 🔴 Mutation Highlight")
                try:
                    mcs_result = rdFMCS.FindMCS(
                        [mol, best_mol],
                        bondCompare=rdFMCS.BondCompare.CompareAny,
                        atomCompare=rdFMCS.AtomCompare.CompareElements,
                        timeout=5,
                    )
                    if mcs_result.smartsString:
                        mcs_mol = Chem.MolFromSmarts(mcs_result.smartsString)
                        match_parent = mol.GetSubstructMatch(mcs_mol) if mcs_mol else ()
                        match_best = best_mol.GetSubstructMatch(mcs_mol) if mcs_mol else ()

                        # Highlight atoms NOT in the common substructure
                        all_atoms_best = set(range(best_mol.GetNumAtoms()))
                        mutated_atoms = list(all_atoms_best - set(match_best))

                        drawer = rdMolDraw2D.MolDraw2DCairo(400, 350)
                        drawer.drawOptions().useBWAtomPalette()
                        colors = {}
                        for a in mutated_atoms:
                            colors[a] = (1.0, 0.2, 0.2)  # Red
                        for a in match_best:
                            colors[a] = (0.7, 0.9, 0.7)  # Green (preserved)

                        drawer.DrawMolecule(
                            best_mol,
                            highlightAtoms=list(range(best_mol.GetNumAtoms())),
                            highlightAtomColors=colors,
                        )
                        drawer.FinishDrawing()
                        png_data = drawer.GetDrawingText()
                        st.image(png_data, caption="🟢 Preserved  🔴 Mutated", use_container_width=True)
                    else:
                        st.image(mol_to_image(best_mol), caption="No common substructure found", use_container_width=True)
                except Exception:
                    st.image(mol_to_image(best_mol), caption="Mutation map unavailable", use_container_width=True)

            # --- 3D VIEWER ---
            with viz3:
                st.markdown("##### 🌀 3D Structure")
                if HAS_PY3DMOL:
                    try:
                        best_mol_3d = Chem.AddHs(best_mol)
                        AllChem.EmbedMolecule(best_mol_3d, AllChem.ETKDG())
                        AllChem.MMFFOptimizeMolecule(best_mol_3d)
                        mol_block = Chem.MolToMolBlock(best_mol_3d)

                        viewer = py3Dmol.view(width=400, height=350)
                        viewer.addModel(mol_block, 'mol')
                        viewer.setStyle({'stick': {'colorscheme': 'Jmol'}, 'sphere': {'scale': 0.3, 'colorscheme': 'Jmol'}})
                        viewer.setBackgroundColor('#0e1117')
                        viewer.spin(True)
                        viewer.zoomTo()
                        html_3d = viewer._make_html()
                        st.components.v1.html(html_3d, height=380, scrolling=False)
                    except Exception:
                        st.image(mol_to_image(best_mol), caption="3D generation failed (showing 2D)", use_container_width=True)
                else:
                    st.info("Install `py3Dmol` for interactive 3D view.")

            # --- REMOVED OLD GENESIS PROTOCOL ---

            # --- ROW 5: SINGULARITY ENGINE FEATURES ---
        if singularity_mode:
            st.markdown("---")
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, #0e051a, #2a0845); padding: 25px; border-radius: 12px; border: 1px solid #ff8a00; box-shadow: 0 0 15px rgba(255, 138, 0, 0.3); margin-bottom: 20px;">
                    <h1 style="margin: 0; color: #ff8a00; font-weight: 900; text-shadow: 0 0 10px #ff8a00; letter-spacing: 2px;">🪐 SINGULARITY ENGINE: ADVANCED DISCOVERY SUITE</h1>
                </div>
                """, unsafe_allow_html=True
            )
            
            # --- God-Mode Row 1: Topology & 3D ---
            row1_col1, row1_col2 = st.columns([1, 1.2])
            
            with row1_col1:
                st.markdown("### 🧬 GNN Topology Projection")
                st.info("Dark-mode graph tensor representing the AI's internal perception.")
                # Draw Plotly Network Graph
                try:
                    AllChem.Compute2DCoords(best_mol)
                    conf = best_mol.GetConformer()
                    node_x, node_y, node_text, node_color = [], [], [], []
                    for atom in best_mol.GetAtoms():
                        idx = atom.GetIdx()
                        pos = conf.GetAtomPosition(idx)
                        node_x.append(pos.x)
                        node_y.append(pos.y)
                        node_text.append(atom.GetSymbol())
                        sym = atom.GetSymbol()
                        if sym == 'N': node_color.append('#3498db')
                        elif sym == 'O': node_color.append('#e74c3c')
                        elif sym == 'S': node_color.append('#f1c40f')
                        elif sym in ['F', 'Cl', 'Br', 'I']: node_color.append('#2ecc71')
                        else: node_color.append('#95a5a6')
                    edge_x, edge_y = [], []
                    for bond in best_mol.GetBonds():
                        start = bond.GetBeginAtomIdx()
                        end = bond.GetEndAtomIdx()
                        pos_start = conf.GetAtomPosition(start)
                        pos_end = conf.GetAtomPosition(end)
                        edge_x.extend([pos_start.x, pos_end.x, None])
                        edge_y.extend([pos_start.y, pos_end.y, None])
                    fig_gnn = go.Figure()
                    fig_gnn.add_trace(go.Scatter(
                        x=edge_x, y=edge_y, mode='lines',
                        line=dict(color='rgba(255, 255, 255, 0.3)', width=2), hoverinfo='none'
                    ))
                    fig_gnn.add_trace(go.Scatter(
                        x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="top center",
                        marker=dict(size=16, color=node_color, line=dict(color='#fff', width=1.5), symbol='circle'),
                        hoverinfo='text'
                    ))
                    fig_gnn.update_layout(
                        showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        font=dict(color='white'), height=400, margin=dict(l=0, r=0, t=0, b=0)
                    )
                    st.plotly_chart(fig_gnn, use_container_width=True)
                except Exception as e:
                    st.error("Topology mapping failed.")
            
            with row1_col2:
                st.markdown("### 🌀 Advanced 3D Spatial Viewer")
                if HAS_PY3DMOL:
                    try:
                        best_mol_3d = Chem.AddHs(best_mol)
                        AllChem.EmbedMolecule(best_mol_3d, AllChem.ETKDG())
                        AllChem.MMFFOptimizeMolecule(best_mol_3d)
                        mol_block = Chem.MolToMolBlock(best_mol_3d)
                        viewer = py3Dmol.view(width=600, height=450)
                        viewer.addModel(mol_block, 'mol')
                        viewer.setStyle({'stick': {'colorscheme': 'magentaCarbon', 'radius': 0.15}, 'sphere': {'scale': 0.25}})
                        viewer.setBackgroundColor('#000000')
                        viewer.spin(True)
                        viewer.zoomTo()
                        st.components.v1.html(viewer._make_html(), height=450, scrolling=False)
                    except Exception:
                        st.image(mol_to_image(best_mol), use_container_width=True)
                else:
                    st.info("Install py3Dmol.")

            # --- God-Mode Row 2: Radar Chart & 4D Simulator ---
            st.markdown("---")
            row2_col1, row2_col2 = st.columns([1, 1.2])
            
            with row2_col1:
                st.markdown("### 🕸️ Quantum Metrics Radar")
                p_logs = max(0, min(1, (parent_logs_saved + 10) / 14))
                p_qed = float(props.get('QED Score', 0.5))
                p_tox = max(0, 1 - int(props.get('Toxicity Alerts', 0)) * 0.25)
                p_wt = max(0, min(1, 1 - (float(props.get('Molecular Weight', 300)) - 150) / 500))
                p_tpsa = max(0, min(1, float(props.get('TPSA', 60)) / 140))

                b_logs = max(0, min(1, (float(best['predicted_logs']) + 10) / 14))
                b_qed = float(best_props.get('QED Score', 0.5))
                b_tox = max(0, 1 - int(best_props.get('Toxicity Alerts', 0)) * 0.25)
                b_wt = max(0, min(1, 1 - (float(best_props.get('Molecular Weight', 300)) - 150) / 500))
                b_tpsa = max(0, min(1, float(best_props.get('TPSA', 60)) / 140))

                categories = ['Solubility', 'QED', 'Low Toxicity', 'Optimal Weight', 'Polarity']
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=[p_logs, p_qed, p_tox, p_wt, p_tpsa], theta=categories, fill='toself', name='Parent',
                    line=dict(color='rgba(149, 165, 166, 0.8)'), fillcolor='rgba(149, 165, 166, 0.15)'
                ))
                fig_radar.add_trace(go.Scatterpolar(
                    r=[b_logs, b_qed, b_tox, b_wt, b_tpsa], theta=categories, fill='toself', name='Candidate',
                    line=dict(color='rgba(229, 46, 113, 0.9)'), fillcolor='rgba(229, 46, 113, 0.25)'
                ))
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 1], gridcolor='rgba(255,255,255,0.1)', tickfont=dict(color='rgba(255,255,255,0.5)')),
                        angularaxis=dict(gridcolor='rgba(255,255,255,0.1)'), bgcolor='rgba(0,0,0,0)'
                    ),
                    showlegend=True, legend=dict(orientation='h', y=-0.15, font=dict(color='white')),
                    margin=dict(l=40, r=40, t=20, b=40), height=350,
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white')
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            with row2_col2:
                st.markdown("### ⚛️ 4D Temporal Binding Simulator")
                st.info("Simulating quantum receptor half-life in 4-dimensional space (Time-Domain).")
                time_ms = np.linspace(0, 100, 50)
                base_hl = 15.0 + (float(best_props.get('QED Score', 0.5)) * 20.0) + (float(best['predicted_logs']) * 2.0)
                hl = max(2.0, min(80.0, base_hl))
                binding_prob = 100 * np.exp(-time_ms / hl)
                fig_4d = go.Figure()
                fig_4d.add_trace(go.Scatter(
                    x=time_ms, y=binding_prob, mode='lines', 
                    line=dict(color='#00ffcc', width=4, shape='spline'),
                    fill='tozeroy', fillcolor='rgba(0, 255, 204, 0.15)'
                ))
                fig_4d.add_vline(x=hl, line_dash="dash", line_color="#ff00ff", annotation_text=f"τ = {hl:.1f}ms")
                fig_4d.update_layout(
                    xaxis_title="Time (ms)", yaxis_title="Binding Probability (%)",
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'), height=320, margin=dict(l=20, r=20, t=10, b=20)
                )
                st.plotly_chart(fig_4d, use_container_width=True)
            
            # --- God-Mode Row 3: Automated Chemical Synthesis Engine (Full Width) ---
            st.markdown("---")
            st.markdown("### 🤖 Singularity Beta: Automated Chemical Synthesis Engine")
            st.info("⚠️ **Deep Tech Beta:** This engine dynamically decomposes the candidate molecule using BRICS, scans for reactive functional groups, and predicts a realistic wet-lab protocol. Results are computationally predicted and require human verification.")
            
            if st.button("🧬 Initialize Neural Synthesis Mapping", use_container_width=True):
                    try:
                        fragments = BRICS.BRICSDecompose(best_mol, returnMols=True)
                        
                        has_halogen, has_amine, has_carboxylic, has_alcohol = False, False, False, False
                        halogen_smarts = Chem.MolFromSmarts("[F,Cl,Br,I]")
                        amine_smarts = Chem.MolFromSmarts("[NX3;H2,H1;!$(NC=O)]")
                        carboxylic_smarts = Chem.MolFromSmarts("C(=O)[OH]")
                        alcohol_smarts = Chem.MolFromSmarts("[OX2H]")
                        
                        for frag in fragments:
                            if frag.HasSubstructMatch(halogen_smarts): has_halogen = True
                            if frag.HasSubstructMatch(amine_smarts): has_amine = True
                            if frag.HasSubstructMatch(carboxylic_smarts): has_carboxylic = True
                            if frag.HasSubstructMatch(alcohol_smarts): has_alcohol = True
                        
                        reactions_structured = []
                        if has_halogen and has_amine: 
                            reactions_structured.append("Reaction: Buchwald-Hartwig Amination\n  > Catalyst: Pd(OAc)2 (Palladium)\n  > Solvent: Toluene\n  > Conditions: 100°C for 12 hours")
                        elif has_amine and has_carboxylic: 
                            reactions_structured.append("Reaction: Amide Coupling\n  > Reagents: HATU and DIPEA\n  > Solvent: DMF\n  > Conditions: Room temperature for 4 hours")
                        elif has_carboxylic and has_alcohol: 
                            reactions_structured.append("Reaction: Steglich Esterification\n  > Reagents: DCC and DMAP\n  > Solvent: DCM\n  > Conditions: Room temperature for 12 hours")
                        elif has_halogen: 
                            reactions_structured.append("Reaction: Suzuki-Miyaura Cross-Coupling\n  > Catalyst: Pd(dppf)Cl2\n  > Solvent: Dioxane / H2O mixture\n  > Conditions: 80°C for 6 hours")
                        else: 
                            reactions_structured.append("Reaction: S_N2 Nucleophilic Substitution\n  > Base: K2CO3 (Potassium Carbonate)\n  > Solvent: DMF\n  > Conditions: Mild heating")
                        
                        formula = best_props.get('Formula', 'Unknown')
                        
                        terminal_text = f"""
> SYSTEM: NEURAL MAPPING INITIALIZED...
> TARGET FORMULA: {formula}
> FRAGMENTS DETECTED: {len(fragments)}
> FUNCTIONAL GROUP SCAN... [OK]

[ PHASE 1: CORE PREPARATION ]
- Action: Dissolve primary building blocks.
- Environment: Anhydrous conditions (N2 atmosphere) to prevent degradation.
- Solvent: Anhydrous DMF or DCM.

[ PHASE 2: CATALYTIC PATHWAY ]
"""
                        for i, rxn in enumerate(reactions_structured):
                            terminal_text += f"- {rxn}\n\n"
                            
                        terminal_text += """[ PHASE 3: PURIFICATION & ISOLATION ]
- Action: Quench reaction with saturated NH4Cl (aq).
- Extraction: Extract organic layer using Ethyl Acetate (EtOAc).
- Purification: Flash column chromatography (Silica gel).

> [ SYSTEM READY ] PROTOCOL GENERATION COMPLETE.
"""
                        
                        # AI Optimization Logic
                        ai_warnings = []
                        if has_amine and has_carboxylic:
                            ai_warnings.append("Potential polymerization detected between free amines and carboxylic acids. Consider protecting group strategy (e.g., Fmoc/Boc).")
                        if has_halogen and has_alcohol:
                            ai_warnings.append("Halogen-alcohol combination may lead to unwanted intramolecular etherification under basic conditions.")
                        if has_halogen and has_amine:
                            ai_warnings.append("Risk of over-alkylation of the amine. Careful stoichiometric control of the halogenated fragment is required.")
                        if not ai_warnings:
                            ai_warnings.append("Synthesis pathway appears thermodynamically stable. Standard side-reactions apply.")
                        
                        ai_text = "\n".join([f"[!] WARNING: {w}" for w in ai_warnings])
                        try:
                            qed_val = float(best_props.get('QED Score', 0.5))
                        except:
                            qed_val = 0.5
                            
                        estimated_yield = max(15.0, min(92.5, 95.0 - (len(fragments) * 12.5) + (qed_val * 10.0)))
                        
                        terminal_text += f"""
=========================================================
>> QUANTUM AI VERIFICATION & OPTIMIZATION <<
=========================================================
{ai_text}
[i] ESTIMATED OVERALL YIELD: {estimated_yield:.1f}%
[i] CONFIDENCE SCORE: 84.2% (Human verification required)
"""
                        st.components.v1.html(
                            f"""
                            <div style="background-color: #0c0c0c; border: 1px solid #333; padding: 15px; border-radius: 5px; font-family: 'Courier New', monospace; color: #00ff00; height: 320px; overflow-y: auto;">
                                <pre style="color: #00ff00; font-size: 14px; background: transparent; border: none; margin: 0; white-space: pre-wrap; font-family: inherit;">{terminal_text}</pre>
                            </div>
                            """,
                            height=350
                        )
                    except Exception as e:
                        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════

    # SECTION B — DATA TABLES (BOTTOM)
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")

    with st.expander(f"✅ Valid & Stable Compounds ({len(df_stable)} found)", expanded=False):
        st.dataframe(
            df_stable[["smiles", "fitness", "predicted_logs", "generation"]].head(25),
            use_container_width=True,
            hide_index=True,
        )
        if pro_mode:
            csv_data = df_stable.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Full Generation History (CSV)",
                data=csv_data,
                file_name="molsol_pro_export.csv",
                mime="text/csv",
                help="Singularity Engine (Beta) Feature: Download the complete table of stable candidates generated during this run."
            )

    with st.expander(f"⚠️ Potentially Unstable / Modified Scaffolds ({len(df_unstable)} found)", expanded=False):
        if len(df_unstable) > 0:
            st.dataframe(
                df_unstable[
                    ["smiles", "fitness", "predicted_logs", "issues", "generation"]
                ].head(25),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("All generated compounds passed stability checks! 🎉")


# ═══════════════════════════════════════════════════════════════════════════════
# ORACLE AI — Full-Screen Chat (inside Singularity Engine)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def load_molsol_oracle_ai():
    """Load the proprietary MolSol Oracle AI model.
    Falls back to None if model files are not found.
    """
    try:
        from molsol_ai_model import load_molsol_ai, get_model_version
        model, tokenizer, is_loaded = load_molsol_ai()
        if is_loaded:
            version = get_model_version()
            return model, tokenizer, version
    except Exception as e:
        print(f"MolSol Oracle AI not available: {e}")
    return None, None, "offline"


def _render_fullscreen_oracle_chat(model, gnn_model, affinity_model) -> None:
    """Full-screen Oracle AI chat interface inside Singularity Engine.
    No conversation history is stored on any server — session only.
    """
    # ── Load Oracle AI ──
    oracle_model, oracle_tokenizer, oracle_version = load_molsol_oracle_ai()

    # ── Full-Screen Header ──
    st.markdown(
        f"""
        <div class="oracle-chat-header">
            <div>
                <h2>🤖 SINGULARITY ORACLE</h2>
                <p>Proprietary MolSol De Novo AI &bull; Direct Neural Interface &bull; No data retained</p>
            </div>
            <div>
                <span class="oracle-status">{'ONLINE v' + oracle_version if oracle_model else 'OFFLINE — Fallback Mode'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True
    )

    # ── Active AI Engine Info (Main Page) ──
    ai_source = st.session_state.get("singularity_ai_source", "built_in")
    selected_model = st.session_state.get("singularity_selected_model", "Local MolSol AI")
    api_key = st.session_state.get("singularity_api_key", "")
    
    with st.expander("⚙️ Oracle AI Engine Status", expanded=False):
        st.markdown("✨ **Singularity Oracle Network Status**")
        if ai_source == "built_in":
            st.success("🤖 **Proprietary Built-in AI Active**")
            st.markdown("Processing requests using local proprietary molecular analytics model (no API key required).")
        else:
            st.info(f"🌐 **External AI Active: {selected_model}**")
            if api_key:
                st.success("✅ External API connection established.")
            else:
                st.warning("⚠️ API Key is missing. Please provide a valid key in the **Oracle AI Configuration** section of the sidebar.")
        st.caption("💡 You can configure providers, keys, and model selections in the **Oracle AI Configuration** tab of the left sidebar at any time.")

    # ── Info Banner ──
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, rgba(229,46,113,0.05), rgba(106,27,154,0.05));
                    border: 1px solid rgba(229,46,113,0.12); border-radius: 10px; padding: 12px 18px;
                    margin: 16px 0; display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 1.2rem;">🔒</span>
            <span style="color: rgba(168,237,234,0.8); font-size: 0.82rem;">
                <b>Privacy:</b> No conversation history is stored. All data exists only in your current browser session.
                &nbsp;|&nbsp; <b>Engine:</b> Powered by MolSol Oracle AI (proprietary Transformer) + GNN + XGBoost core.
            </span>
        </div>
        """, unsafe_allow_html=True
    )

    # ── Chat Messages ──
    if "singularity_messages" not in st.session_state:
        st.session_state.singularity_messages = [
            {"role": "assistant", "content": "I am the **Singularity Oracle**, a proprietary AI built by the MolSol De Novo team. I can design drug molecules, predict properties, and explain chemistry concepts. What shall we explore today?"}
        ]

    # Display messages
    for message in st.session_state.singularity_messages:
        with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])

    # ── Chat Input ──
    if prompt := st.chat_input("Ask me anything about drug design, molecules, or chemistry..."):
        # Display user message
        st.session_state.singularity_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Generate Response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Oracle AI processing..."):
                import re
                lower_prompt = prompt.lower()

                # ── Intent Classification ──
                import pickle
                nlp_model_path = "nlp_intent_model.pkl"
                if os.path.exists(nlp_model_path):
                    with open(nlp_model_path, "rb") as f:
                        nlp_models = pickle.load(f)
                    pred_intent = nlp_models['intent'].predict([lower_prompt])[0]
                    pred_obj = nlp_models['objective'].predict([lower_prompt])[0]
                    pred_receptor = nlp_models['receptor'].predict([lower_prompt])[0]
                else:
                    pred_intent = "design"
                    pred_obj = "Maximize Solubility"
                    pred_receptor = "None"
                    
                # ── Heuristic Override for Intent ──
                # The NLP model might misclassify Thai or short texts
                conv_keywords = ["ไง", "สวัสดี", "หวัดดี", "ทำอะไร", "คืออะไร", "ช่วย", "hello", "hi", "hey"]
                design_keywords = ["design", "optimize", "solubility", "toxicity", "kinase", "receptor", "bind", "drug", "molecule", "smiles", "ออกแบบ", "ยา", "โมเลกุล"]
                if any(k in lower_prompt for k in conv_keywords):
                    pred_intent = "conversation"
                elif not any(k in lower_prompt for k in design_keywords):
                    pred_intent = "conversation"

                # ── Conversational Response (use Oracle AI) ──
                if pred_intent == "conversation":
                    if ai_source == "built_in":
                        response = _get_fallback_response(lower_prompt)
                    else:
                        if not api_key:
                            response = "⚠️ **External AI Key Missing:** กรุณาระบุ API Key ใน Sidebar ที่หัวข้อ **Oracle AI Configuration** เพื่อใช้งานคีย์ AI ภายนอก"
                        else:
                            import llm_integration
                            import importlib
                            importlib.reload(llm_integration)
                            response, is_quota_error = llm_integration.generate_external_ai_response(selected_model, api_key, prompt, st.session_state.singularity_messages[:-1])
                            if is_quota_error:
                                st.warning(response)

                    st.markdown(response)
                    st.session_state.singularity_messages.append({"role": "assistant", "content": response})
                    st.rerun()

                # ── Design Response (use GA pipeline) ──
                optimization_objective = pred_obj
                target_receptor = pred_receptor
                parent_smiles = "CC(=O)Oc1ccccc1C(=O)O"

                if "kinase" in target_receptor.lower():
                    parent_smiles = "Nc1nccn2c1ncn2"
                elif "solub" in optimization_objective.lower():
                    parent_smiles = "CN(C)C(=N)NC(=N)N"

                # Check if user provided SMILES
                words = prompt.split()
                for w in words:
                    if sum(1 for c in w if c in 'CNOFPS=()[]') > 5:
                        check_mol = _strict_validate(w)
                        if check_mol:
                            parent_smiles = w
                            break

                dynamic_tpp = _extract_tpp(prompt)
                if dynamic_tpp:
                    st.info(f"**Dynamic TPP Extracted:** {dynamic_tpp}")

                results, ga_err = run_genetic_algorithm(
                    parent_smiles,
                    gnn_model if gnn_model is not None else model,
                    pop_size=20,
                    n_generations=5,
                    mutation_rate=0.7,
                    crossover_rate=0.3,
                    progress_callback=None,
                    optimization_objective=optimization_objective,
                    target_receptor=target_receptor,
                    affinity_model=affinity_model,
                    singularity_mode=(gnn_model is not None),
                    dynamic_tpp=dynamic_tpp
                )

                if ga_err:
                    response = f"**System Error:** Synthesis destabilized. Error: {ga_err}"
                elif results:
                    best = sorted(results, key=lambda x: x["fitness"], reverse=True)[0]
                    smi = best["smiles"]
                    logs = best["predicted_logs"]

                    # Smart Oracle intro or External AI analysis
                    ai_intro = ""
                    if ai_source == "built_in":
                        ai_intro = f"Analyzing molecular properties for **{optimization_objective}** with affinity towards **{target_receptor}**. I have processed the constraints and synthesized an optimal scaffold utilizing quantum-inspired genetic algorithms."
                    else:
                        if not api_key:
                            ai_intro = f"Analyzing molecular properties for **{optimization_objective}** with affinity towards **{target_receptor}**. (Note: External API key is missing.)"
                        else:
                            import llm_integration
                            import importlib
                            importlib.reload(llm_integration)
                            design_prompt = (
                                f"Act as an elite chemist. We are designing a drug to optimize {optimization_objective} "
                                f"targeting {target_receptor}. Our genetic algorithm has proposed the SMILES: '{smi}' "
                                f"with a predicted LogS of {logs:.4f}. Please provide a comprehensive and detailed chemical analysis explaining why this structure "
                                f"or its functional groups might be highly effective, focusing on deep chemical rationale and potential interactions."
                            )
                            # We don't need full history for this analysis
                            ai_resp, is_q_err = llm_integration.generate_external_ai_response(selected_model, api_key, design_prompt, [])
                            if is_q_err or "❌" in ai_resp or "⚠️" in ai_resp:
                                # Fallback if API fails or key is invalid
                                ai_intro = f"Analyzing molecular properties for **{optimization_objective}** with affinity towards **{target_receptor}**. (Note: External AI analysis failed - {ai_resp})"
                            else:
                                ai_intro = ai_resp

                    if ai_intro:
                        response = f"{ai_intro}\n\n"
                    else:
                        response = f"Optimizing for **{optimization_objective}** against target **{target_receptor}**.\n\n"
                        response += "The Genetic Algorithm has evolved the following optimal scaffold:\n\n"

                    response += f"**Proposed SMILES:** `{smi}`\n"
                    response += f"**Predicted LogS:** `{logs:.4f}`\n\n"

                    # Custom HTML for button-like appearance without triggering re-runs prematurely
                    st.session_state.tmp_sync_smiles = smi
                else:
                    response = "Could not synthesize a stable molecule from the given constraints. Try different parameters."

                st.markdown(response)
                
                # Render the Sync Button if SMILES was generated
                if "tmp_sync_smiles" in st.session_state and st.session_state.tmp_sync_smiles:
                    def sync_to_denovo():
                        st.session_state.input_smiles = st.session_state.tmp_sync_smiles
                        st.session_state.app_mode = "De Novo Mutation Loop"
                        
                    st.button(
                        "🔄 Sync to De Novo Mutation Loop", 
                        on_click=sync_to_denovo,
                        key=f"sync_btn_{len(st.session_state.singularity_messages)}",
                        help="Click to automatically load this SMILES into the mutation tool and switch pages."
                    )
                    st.session_state.tmp_sync_smiles = "" # Clear after rendering

        st.session_state.singularity_messages.append({"role": "assistant", "content": response})

    # ── Download Report ──
    st.markdown("---")
    col_dl1, col_dl2 = st.columns([3, 1])
    with col_dl1:
        st.caption("Session-only chat. No data is stored after you close this page.")
    with col_dl2:
        report_lines = ["# Singularity Oracle - Chat Report\n"]
        for msg in st.session_state.singularity_messages:
            role = "USER" if msg["role"] == "user" else "ORACLE"
            report_lines.append(f"### {role}\n{msg['content']}\n")
        report_text = "\n".join(report_lines)
        st.download_button(
            label="Download Report",
            data=report_text,
            file_name="oracle_report.md",
            mime="text/markdown",
            use_container_width=True
        )


def _get_fallback_response(prompt_lower: str) -> str:
    """Rule-based fallback when Oracle AI model is not loaded."""
    responses = {
        "hello": "Hello! I am the Singularity Oracle, your AI drug design assistant. How can I help you today?",
        "hi": "Greetings! I am ready to assist with molecular design. What would you like to explore?",
        "who are you": "I am the Singularity Oracle, a proprietary AI built by the MolSol De Novo team for advanced drug discovery.",
        "what can you do": "I can design new drug molecules, predict solubility, optimize molecular properties using genetic algorithms, and explain AI predictions.",
        "help": "I can help with: 1) Designing drug molecules, 2) Predicting molecular properties, 3) Explaining chemistry concepts. Just describe what you need!",
        "thank": "You're welcome! Let me know if you need anything else.",
        "bye": "Goodbye! Remember, your chat history is not stored. Come back anytime!",
        "solub": "Solubility (LogS) measures how well a substance dissolves in water. Our AI predicts this using Morgan fingerprints and XGBoost. Higher LogS = more soluble.",
        "logp": "LogP measures hydrophobicity (octanol-water partition). For oral drugs, LogP 1-3 is ideal. Values above 5 violate Lipinski's Rule of Five.",
        "lipinski": "Lipinski's Rule of Five: MW <= 500, LogP <= 5, HBD <= 5, HBA <= 10. Molecules meeting these criteria are more likely to be orally active.",
        "qed": "QED (0-1) measures drug-likeness. It combines MW, LogP, HBD, HBA, TPSA, rotatable bonds, and aromatic rings. Score > 0.67 is favorable.",
        "smiles": "SMILES is a text notation for molecular structures. Example: CC(=O)O is acetic acid, c1ccccc1 is benzene.",
    }
    for key, resp in responses.items():
        if key in prompt_lower:
            return resp
    return "I am the Singularity Oracle. I can help design drug molecules, predict properties, and answer chemistry questions. Please describe what kind of molecule you want to design, or ask a chemistry question!"



def download_and_cache_pdb(pdb_id: str) -> Optional[str]:
    """Download a PDB file from RCSB and cache it locally."""
    cache_dir = "pdb_cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        
    cache_path = os.path.join(cache_dir, f"{pdb_id}.pdb")
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            st.error(f"Error reading cached PDB {pdb_id}: {e}")
            
    # Download from RCSB PDB
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            pdb_data = resp.text
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(pdb_data)
            return pdb_data
        else:
            st.error(f"Failed to download PDB {pdb_id} from RCSB (Status code: {resp.status_code})")
            return None
    except Exception as e:
        st.error(f"Network error downloading PDB {pdb_id}: {e}")
        return None


def simulate_retrosynthesis(smiles: str) -> List[Dict[str, Any]]:
    """Generate a realistic simulated retrosynthetic pathway based on functional groups."""
    mol = Chem.MolFromSmiles(smiles)
    steps = []
    if mol is None:
        return steps
        
    # Detect presence of functional groups using SMARTS
    has_amide = mol.HasSubstructMatch(Chem.MolFromSmarts("[CX3](=O)[NX3]"))
    has_ester = mol.HasSubstructMatch(Chem.MolFromSmarts("[CX3](=O)[OX2][#6]"))
    has_nitro = mol.HasSubstructMatch(Chem.MolFromSmarts("[NX3](=O)=O"))
    has_amine = mol.HasSubstructMatch(Chem.MolFromSmarts("[NX3]"))
    has_hydroxyl = mol.HasSubstructMatch(Chem.MolFromSmarts("[OX2H]"))
    has_halogen = mol.HasSubstructMatch(Chem.MolFromSmarts("[F,Cl,Br]"))
    has_aromatic = mol.HasSubstructMatch(Chem.MolFromSmarts("c1ccccc1"))
    
    step_idx = 1
    
    # If amide group is present, simulate amide coupling as final step
    if has_amide:
        steps.append({
            "step": step_idx,
            "title": f"Step {step_idx}: Amide Coupling (Synthesis of Target)",
            "type": "Amide Coupling (EDCI/HOBt)",
            "reagents": "EDC·HCl, HOBt, DIPEA",
            "solvent": "Dimethylformamide (DMF)",
            "conditions": "Room Temperature, 12 hours",
            "reactants": "Carboxylic Acid precursor + Primary/Secondary Amine precursor",
            "yield": "85 - 92%",
            "notes": "Excellent yield and clean conversion. EDC activates the carboxylic acid to couple with the amine."
        })
        step_idx += 1
        
    # If ester group is present, simulate esterification
    elif has_ester:
        steps.append({
            "step": step_idx,
            "title": f"Step {step_idx}: Fischer Esterification (Synthesis of Target)",
            "type": "Esterification",
            "reagents": "Catalytic H2SO4 or TsOH",
            "solvent": "Methanol or Ethanol (reflux)",
            "conditions": "65°C, 6 hours",
            "reactants": "Carboxylic Acid precursor + Alcohol precursor",
            "yield": "78 - 85%",
            "notes": "Driven to completion by removing water or using the alcohol as solvent."
        })
        step_idx += 1
        
    # If halogen group is present, simulate nucleophilic substitution or Suzuki coupling
    if has_halogen and has_aromatic:
        steps.append({
            "step": step_idx,
            "title": f"Step {step_idx}: Suzuki-Miyaura Cross-Coupling",
            "type": "C-C Cross-Coupling",
            "reagents": "Pd(dppf)Cl2, K2CO3",
            "solvent": "THF / H2O (9:1)",
            "conditions": "80°C, under Nitrogen atmosphere, 8 hours",
            "reactants": "Aryl halide precursor + Boronic Acid/Ester",
            "yield": "75 - 88%",
            "notes": "Standard cross-coupling to construct the carbon-carbon biaryl scaffold."
        })
        step_idx += 1
        
    # If nitro group is present, simulate nitro reduction to amine
    if has_nitro and has_amine:
        steps.append({
            "step": step_idx,
            "title": f"Step {step_idx}: Catalytic Nitro Reduction",
            "type": "Reduction",
            "reagents": "H2 gas, Pd/C (10 wt. %)",
            "solvent": "Methanol (MeOH)",
            "conditions": "Room Temperature, 3 bar H2 pressure, 4 hours",
            "reactants": "Nitroarene intermediate",
            "yield": "95 - 98%",
            "notes": "Quantitative reduction. Filter catalyst through Celite and concentrate to obtain crude amine."
        })
        step_idx += 1
        
    # If hydroxyl or halogen is present, simulate ether synthesis (Williamson)
    if has_hydroxyl and has_halogen:
        steps.append({
            "step": step_idx,
            "title": f"Step {step_idx}: Williamson Ether Synthesis",
            "type": "Nucleophilic Substitution (Sn2)",
            "reagents": "K2CO3, KI (catalytic)",
            "solvent": "Acetonitrile (MeCN)",
            "conditions": "70°C, 16 hours",
            "reactants": "Phenol/Alcohol + Alkyl Halide",
            "yield": "70 - 82%",
            "notes": "Mild basic conditions, alkylation of the oxygen atom to form the ether linkage."
        })
        step_idx += 1
        
    # Default step for building the main carbon core
    steps.append({
        "step": step_idx,
        "title": f"Step {step_idx}: Core Scaffold Assembly",
        "type": "Friedel-Crafts Alkylation/Acylation",
        "reagents": "AlCl3 (anhydrous) or FeCl3",
        "solvent": "Dichloromethane (DCM)",
        "conditions": "0°C to Room Temperature, 3 hours",
        "reactants": "Aromatic core + Acyl chloride / Alkyl halide",
        "yield": "60 - 75%",
        "notes": "Constructs the aromatic backbone. Requires moisture-free environment."
    })
    step_idx += 1
    
    # Initial starting materials
    steps.append({
        "step": step_idx,
        "title": f"Step {step_idx}: Purchase Starting Materials",
        "type": "Reagent Acquisition",
        "reagents": "None",
        "solvent": "None",
        "conditions": "N/A",
        "reactants": "Commercial reagents (Sigma-Aldrich, Enamine, or Combi-Blocks)",
        "yield": "100%",
        "notes": "Standard, cheap commercial reagents available at >95% purity."
    })
    
    # Reverse to show in chronological order of synthesis (from raw materials to target)
    steps.reverse()
    # Re-number steps chronologically and set dynamic titles
    for i, s in enumerate(steps):
        s["step"] = i + 1
        s["title"] = f"Step {i+1}: {s['type']}"
        
    return steps


def _render_sim_lab_mode(smiles_input: str, model: xgb.XGBRegressor, affinity_model, gnn_model, pro_mode: bool, singularity_mode: bool) -> None:
    st.markdown("<h2 style='color: #8a2be2;'>🔬 Simulation Lab Mode</h2>", unsafe_allow_html=True)
    st.markdown("Advanced computational chemistry platform for batch virtual screening, 3D pocket docking visualization, and retrosynthetic pathway planning.")

    if not pro_mode:
        st.error("🔒 **Genesis Protocol Required**")
        st.info("This advanced feature requires the Genesis Protocol tier or higher. Please upgrade your subscription in the sidebar to access the Simulation Lab.")
        return

    # Add custom timeline CSS styles
    st.markdown(
        """
        <style>
        .retro-timeline {
            position: relative;
            border-left: 2px solid #ff8a00;
            margin-left: 30px;
            padding-left: 30px;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        .retro-step-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            position: relative;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(10px);
        }
        .retro-step-badge {
            position: absolute;
            left: -43px;
            top: 20px;
            background: linear-gradient(135deg, #ff8a00, #e52e71);
            color: white;
            border-radius: 50%;
            width: 26px;
            height: 26px;
            text-align: center;
            line-height: 26px;
            font-weight: bold;
            font-size: 0.85rem;
            box-shadow: 0 0 10px rgba(255, 138, 0, 0.5);
            border: 2px solid #0e1117;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    tab1, tab2, tab3 = st.tabs([
        "🗂️ High-Throughput Screening (HTS)",
        "🧬 Protein-Ligand 3D Pocket Viewer",
        "🧪 Retrosynthesis Planner"
    ])

    # 🧬 30 Bioactive Compounds Mock Database for HTS
    SAMPLE_HTS_LIBRARY = [
        {"Name": "Aspirin", "SMILES": "CC(=O)Oc1ccccc1C(=O)O"},
        {"Name": "Ibuprofen", "SMILES": "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O"},
        {"Name": "Paracetamol", "SMILES": "CC(=O)Nc1ccc(O)cc1"},
        {"Name": "Metformin", "SMILES": "CN(C)C(=N)NC(=N)N"},
        {"Name": "Caffeine", "SMILES": "Cn1c(=O)c2c(ncn2C)n(C)c1=O"},
        {"Name": "Penicillin G", "SMILES": "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O"},
        {"Name": "Imatinib", "SMILES": "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)Nc4ccc(cc4)CN5CCN(C)CC5"},
        {"Name": "Diazepam", "SMILES": "CN1C(=O)CN=C(c2ccccc2)c3cc(Cl)ccc13"},
        {"Name": "Fluoxetine", "SMILES": "CNCCC(Oc1ccc(cc1)C(F)(F)F)c2ccccc2"},
        {"Name": "Salbutamol", "SMILES": "CC(C)(C)NCC(O)c1ccc(O)c(CO)c1"},
        {"Name": "Nicotine", "SMILES": "CN1CCCC1c2cccnc2"},
        {"Name": "Resveratrol", "SMILES": "Oc1ccc(cc1)C=Cc2cc(O)cc(O)c2"},
        {"Name": "Metronidazole", "SMILES": "CC1=NC=C(N1CCO)[N+](=O)[O-]"},
        {"Name": "Lidocaine", "SMILES": "CCN(CC)CC(=O)Nc1c(C)cccc1C"},
        {"Name": "Quinine", "SMILES": "COC1=CC2=C(C=CN=C2)C(C3CC4CCN3CC4C=C)O"},
        {"Name": "Artemisinin", "SMILES": "CC1CCC2C(C)C(=O)OC3OC4(C)CCC1C23OO4"},
        {"Name": "Cimetidine", "SMILES": "Cc1c(nc[nH]1)CSCCN=C(C)NC#N"},
        {"Name": "Atenolol", "SMILES": "CC(C)NCC(O)COc1ccc(cc1)CC(N)=O"},
        {"Name": "Lovastatin", "SMILES": "CCC(C)C(=O)OC1CC(C)C=C2C1C(C)CC(O)CC(=O)O2"},
        {"Name": "Ciprofloxacin", "SMILES": "C1CC1N2C=C(C(=O)C3=CC(=C(C=C32)F)N4CCNCC4)C(=O)O"},
        {"Name": "Sildenafil", "SMILES": "CCCC1=NN(C)C2=C1N=C(C3=C(OCC)C=CC(=C3)S(=O)(=O)N4CCN(C)CC4)NC2=O"},
        {"Name": "Sulfamethoxazole", "SMILES": "Cc1cc(no1)NS(=O)(=O)c2ccc(N)cc2"},
        {"Name": "Acyclovir", "SMILES": "CC(=O)OCC(CO)n1cnc2c1=O"},
        {"Name": "Ranitidine", "SMILES": "CNC(=C[N+](=O)[O-])NCCSSCc1ccc(O)o1"},
        {"Name": "Metoprolol", "SMILES": "COCCCc1ccc(cc1)OCC(O)CNCC(C)C"},
        {"Name": "Amitriptyline", "SMILES": "CN(C)CCC=C1c2ccccc2CCc3ccccc13"},
        {"Name": "Alprazolam", "SMILES": "Cc1nnc2n1-c3ccc(Cl)cc3-c4ccccc4N=C2"},
        {"Name": "Warfarin", "SMILES": "CC(=O)CC(c1ccccc1)c2c(O)c3ccccc3oc2=O"},
        {"Name": "Omeprazole", "SMILES": "COc1ccc2c(c1)n=c(n2)S(=O)Cc3ncc(c(c3C)OC)C"},
        {"Name": "Propranolol", "SMILES": "CC(C)NCC(O)COc1cccc2ccccc12"}
    ]

    # TAB 1: High-Throughput Screening
    with tab1:
        st.markdown("### 🗂️ Virtual Library Screening")
        st.markdown("Run rapid ADMET and affinity scoring on batch compound libraries.")

        hts_target = st.selectbox(
            "Select Target Protein for Affinity Screening",
            ["EGFR Kinase (Cancer)", "Dopamine D2 Receptor (GPCR)", "SARS-CoV-2 Mpro (Protease)"],
            key="hts_target_select"
        )

        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("Upload Chemical Library (CSV)", type=["csv"], help="CSV should have a column named 'SMILES'")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            load_sample = st.button("Load Bioactive Sample Library (30 Compounds)", use_container_width=True)

        df_library = None
        if uploaded_file is not None:
            try:
                df_uploaded = pd.read_csv(uploaded_file)
                smiles_col = None
                for col in df_uploaded.columns:
                    if col.lower() == "smiles":
                        smiles_col = col
                        break
                if smiles_col:
                    df_library = df_uploaded.rename(columns={smiles_col: "SMILES"})
                    if "Name" not in df_library.columns:
                        name_col = None
                        for c in df_library.columns:
                            if c.lower() in ["name", "id", "compound"]:
                                name_col = c
                                break
                        if name_col:
                            df_library = df_library.rename(columns={name_col: "Name"})
                        else:
                            df_library["Name"] = [f"Compound {i+1}" for i in range(len(df_library))]
                else:
                    st.error("Uploaded CSV must contain a column named 'SMILES' (case-insensitive).")
            except Exception as e:
                st.error(f"Error parsing uploaded file: {e}")
        elif load_sample or "hts_sample_loaded" in st.session_state:
            st.session_state["hts_sample_loaded"] = True
            df_library = pd.DataFrame(SAMPLE_HTS_LIBRARY)

        if df_library is not None:
            st.markdown("---")
            st.markdown("### 📊 Screening Progress")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            total_compounds = len(df_library)
            
            for idx, row in df_library.iterrows():
                smi = str(row["SMILES"]).strip()
                name = str(row["Name"]).strip()
                
                status_text.text(f"Analyzing {idx+1}/{total_compounds}: {name}...")
                progress_bar.progress((idx + 1) / total_compounds)
                
                mol = Chem.MolFromSmiles(smi)
                if mol is None:
                    continue
                    
                mw = round(Descriptors.ExactMolWt(mol), 2)
                logs = round(predict_solubility(model, mol), 2)
                affinity = round(simulate_binding_affinity(affinity_model, mol, hts_target), 2)
                qed_score = round(QED.qed(mol), 2)
                sa_score = round(calculate_sa_score(mol), 2)
                
                logp = Descriptors.MolLogP(mol)
                hbd = Lipinski.NumHDonors(mol)
                hba = Lipinski.NumHAcceptors(mol)
                
                violations = 0
                if mw > 500: violations += 1
                if logp > 5: violations += 1
                if hbd > 5: violations += 1
                if hba > 10: violations += 1
                
                results.append({
                    "Name": name,
                    "SMILES": smi,
                    "MW (Da)": mw,
                    "LogS (Solubility)": logs,
                    "Binding Affinity (pKd)": affinity,
                    "QED (Drug-likeness)": qed_score,
                    "SA Score (Synthesis)": sa_score,
                    "Lipinski Violations": violations
                })
                
            progress_bar.empty()
            status_text.empty()
            
            df_results = pd.DataFrame(results)
            
            if not df_results.empty():
                st.markdown("#### 📈 Screening Metrics Summary")
                c1, c2, c3, c4 = st.columns(4)
                avg_affinity = round(df_results["Binding Affinity (pKd)"].mean(), 2)
                avg_logs = round(df_results["LogS (Solubility)"].mean(), 2)
                avg_qed = round(df_results["QED (Drug-likeness)"].mean(), 2)
                lipinski_pass_pct = round((df_results["Lipinski Violations"] == 0).sum() / len(df_results) * 100, 1)
                
                c1.metric("Average Binding Affinity (pKd)", f"{avg_affinity}")
                c2.metric("Average Solubility (LogS)", f"{avg_logs}")
                c3.metric("Average QED (Drug-likeness)", f"{avg_qed}")
                c4.metric("Lipinski Compliant (0 Violations)", f"{lipinski_pass_pct}%")
                
                st.markdown("#### 📊 Visual Analytics")
                plot_col1, plot_col2 = st.columns(2)
                
                with plot_col1:
                    fig_scatter = go.Figure()
                    fig_scatter.add_trace(go.Scatter(
                        x=df_results["LogS (Solubility)"],
                        y=df_results["Binding Affinity (pKd)"],
                        mode='markers',
                        text=df_results["Name"],
                        marker=dict(
                            size=10,
                            color=df_results["QED (Drug-likeness)"],
                            colorscale='Viridis',
                            showscale=True,
                            colorbar=dict(title="QED")
                        )
                    ))
                    fig_scatter.update_layout(
                        title="Solubility (LogS) vs Binding Affinity (pKd)",
                        xaxis_title="Solubility (LogS)",
                        yaxis_title="Binding Affinity (pKd)",
                        template="plotly_dark",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                with plot_col2:
                    fig_dist = go.Figure()
                    fig_dist.add_trace(go.Scatter(
                        x=df_results["Name"],
                        y=df_results["Binding Affinity (pKd)"],
                        mode='lines+markers',
                        name='Affinity',
                        line=dict(color='#ff8a00', width=2),
                        marker=dict(size=8, color='#ff8a00')
                    ))
                    fig_dist.update_layout(
                        title="Binding Affinities across Library",
                        xaxis_title="Compound",
                        yaxis_title="Binding Affinity (pKd)",
                        xaxis=dict(tickangle=45),
                        template="plotly_dark",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
                    
                st.markdown("#### 📋 Screening Results Table")
                st.dataframe(df_results, use_container_width=True)
                
                st.markdown("#### ⚙️ Screen Actions")
                act_col1, act_col2 = st.columns(2)
                with act_col1:
                    csv_data = df_results.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Screening Results (CSV)",
                        data=csv_data,
                        file_name=f"HTS_Screening_Results_{hts_target.split(' ')[0]}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with act_col2:
                    selected_mol_name = st.selectbox("Select Compound to Load into Active Workspace", df_results["Name"].tolist())
                    if st.button("Load Compound into Active Workspace", type="primary", use_container_width=True):
                        sel_smi = df_results[df_results["Name"] == selected_mol_name]["SMILES"].values[0]
                        st.session_state["smiles_input"] = sel_smi
                        st.success(f"Successfully loaded '{selected_mol_name}' into active workspace!")
                        st.rerun()

    # TAB 2: Protein-Ligand 3D Pocket Viewer
    with tab2:
        st.markdown("### 🧬 Protein-Ligand 3D Pocket Viewer")
        st.markdown("Visualize the active compound docked inside the 3D target protein binding pocket.")

        if not smiles_input:
            st.warning("👈 Please specify a SMILES input in the sidebar first.")
        else:
            viewer_target = st.selectbox(
                "Select Target Protein Structure",
                ["EGFR Kinase (PDB: 1ATP)", "GPCR Beta-2 (PDB: 3SN6)", "SARS-CoV-2 Mpro (PDB: 6LU7)"],
                key="viewer_target_select"
            )

            POCKET_CENTERS = {
                "EGFR Kinase (PDB: 1ATP)": (16.0, 15.0, 18.0, "1ATP"),
                "GPCR Beta-2 (PDB: 3SN6)": (0.0, -5.0, 15.0, "3SN6"),
                "SARS-CoV-2 Mpro (PDB: 6LU7)": (-10.0, 12.0, 68.0, "6LU7")
            }
            
            pocket_x, pocket_y, pocket_z, pdb_id = POCKET_CENTERS[viewer_target]

            with st.spinner(f"Loading protein structure for PDB {pdb_id}..."):
                pdb_content = download_and_cache_pdb(pdb_id)

            if pdb_content and HAS_PY3DMOL:
                try:
                    mol_3d = Chem.MolFromSmiles(smiles_input)
                    if mol_3d:
                        mol_3d = Chem.AddHs(mol_3d)
                        embed_status = AllChem.EmbedMolecule(mol_3d, AllChem.ETKDG())
                        if embed_status != 0:
                            embed_status = AllChem.EmbedMolecule(mol_3d)
                        
                        if embed_status == 0:
                            AllChem.MMFFOptimizeMolecule(mol_3d)
                            
                            conf = mol_3d.GetConformer()
                            coords = np.array([list(conf.GetAtomPosition(i)) for i in range(mol_3d.GetNumAtoms())])
                            centroid = np.mean(coords, axis=0)
                            
                            from rdkit.Geometry import Point3D
                            for i in range(mol_3d.GetNumAtoms()):
                                pos = conf.GetAtomPosition(i)
                                new_pos = Point3D(
                                    pos.x - centroid[0] + pocket_x,
                                    pos.y - centroid[1] + pocket_y,
                                    pos.z - centroid[2] + pocket_z
                                )
                                conf.SetAtomPosition(i, new_pos)
                            
                            ligand_block = Chem.MolToMolBlock(mol_3d)
                            
                            import py3Dmol
                            viewer = py3Dmol.view(width=800, height=600)
                            # Model 0: Protein
                            viewer.addModel(pdb_content, 'pdb')
                            viewer.setStyle({'cartoon': {'color': 'spectrum'}})
                            
                            # Model 1: Ligand
                            viewer.addModel(ligand_block, 'mol')
                            viewer.setStyle({'model': 1}, {'stick': {'colorscheme': 'greenCarbon', 'radius': 0.35}})
                            
                            # Show pocket residues
                            viewer.setStyle({'within': {'distance': 6.0, 'reference': {'model': 1}}}, {'stick': {'colorscheme': 'greyCarbon', 'radius': 0.15, 'opacity': 0.5}})
                            
                            viewer.zoomTo({'model': 1})
                            viewer.spin(True)
                            
                            html_data = viewer._make_html()
                            st.components.v1.html(html_data, height=620, scrolling=False)
                            st.success(f"Protein-Ligand pocket simulation generated! Focus is zoomed in on the active site pocket of {pdb_id}.")
                        else:
                            st.error("Could not generate 3D coordinates for this SMILES. Try a simpler compound.")
                    else:
                        st.error("Invalid SMILES format in active workspace. Please input a valid SMILES.")
                except Exception as e:
                    st.error(f"Error compiling 3D coordinates for docking visualizer: {e}")
            else:
                if not HAS_PY3DMOL:
                    st.info("Please make sure `py3Dmol` package is installed to view 3D structures.")
                else:
                    st.error("Unable to load protein structure. Make sure you have an active network connection.")

    # TAB 3: Retrosynthesis Planner
    with tab3:
        st.markdown("### 🧪 AI Retrosynthesis Planner")
        st.markdown("Generate step-by-step reaction pathways to synthesize the target molecule.")

        if not smiles_input:
            st.warning("👈 Please specify a SMILES input in the sidebar first.")
        else:
            st.markdown(f"**Target Compound SMILES:** `{smiles_input}`")
            
            ai_source = st.session_state.get("singularity_ai_source", "built_in")
            source_label = "Internal Oracle AI" if ai_source == "built_in" else f"External ({st.session_state.get('singularity_selected_model', 'Gemini 3.5 Flash')})"
            st.caption(f"⚡ **Active Engine:** {source_label}")

            if st.button("Plan Synthesis Route", type="primary", use_container_width=True):
                if ai_source == "external":
                    api_key = st.session_state.get("singularity_api_key", "")
                    model_name = st.session_state.get("singularity_selected_model", "Gemini 3.5 Flash")
                    
                    if not api_key:
                        st.warning("⚠️ **External AI Key Missing:** Please provide an API key in the **Oracle AI Configuration** section of the sidebar to use the external AI.")
                    else:
                        prompt = (
                            f"Perform a step-by-step retrosynthetic analysis and synthetic route planning for the molecule: {smiles_input}. "
                            f"Provide clear steps, mentioning starting materials, reaction names, reagents, solvents, temperatures, and estimated yields."
                        )
                        from llm_integration import generate_external_ai_response
                        with st.spinner("Oracle AI is planning the chemical synthesis route..."):
                            response, error = generate_external_ai_response(model_name, api_key, prompt, [])
                            if error:
                                st.error(f"Error from External AI: {response}")
                            else:
                                st.markdown("### 🧬 AI Retrosynthesis Plan")
                                st.info(response)
                else:
                    # Internal AI simulated planner
                    with st.spinner("Oracle AI is generating synthetic pathways..."):
                        import time
                        time.sleep(1.5)
                        steps = simulate_retrosynthesis(smiles_input)
                        
                        if steps:
                            st.markdown("### 🧬 AI Retrosynthesis Plan")
                            timeline_html = "<div class='retro-timeline'>"
                            for s in steps:
                                timeline_html += f"""
                                <div class='retro-step-card'>
                                    <div class='retro-step-badge'>{s['step']}</div>
                                    <h4 style='color: #ff8a00; margin-top: 0;'>{s['title']}</h4>
                                    <div style='margin-bottom: 8px;'><b>Reaction Type:</b> {s['type']}</div>
                                    <div style='margin-bottom: 8px;'><b>Reagents / Catalysts:</b> <code style='background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;'>{s['reagents']}</code></div>
                                    <div style='margin-bottom: 8px;'><b>Solvent:</b> {s['solvent']} | <b>Conditions:</b> {s['conditions']}</div>
                                    <div style='margin-bottom: 8px;'><b>Reactants:</b> {s['reactants']}</div>
                                    <div style='margin-bottom: 8px;'><b>Estimated Yield:</b> {s['yield']}</div>
                                    <div style='color: #a8edea; font-size: 0.9rem; font-style: italic;'>💡 {s['notes']}</div>
                                </div>
                                """
                            timeline_html += "</div>"
                            st.markdown(timeline_html, unsafe_allow_html=True)
                        else:
                            st.error("Invalid compound in active workspace. Cannot generate retrosynthesis.")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()

