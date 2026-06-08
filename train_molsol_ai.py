"""
🧠 MolSol Oracle AI — Training Script (v1)
============================================
Trains the custom MolSol Transformer from scratch on a curated
chemistry & drug design Q&A dataset.

Usage:
    python train_molsol_ai.py

Output:
    • molsol_ai_v1.pth      — Model weights
    • molsol_vocab.json      — Tokenizer vocabulary
    • molsol_ai_config.json  — Model configuration (for loading)

Upgrade Instructions:
    1. Add more Q&A pairs to the TRAINING_DATA list below
    2. Optionally increase model size in MODEL_CONFIG
    3. Re-run this script
    4. The app will automatically load the new model on next restart

Author: MolSol De Novo Team (Proprietary)
"""

import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from molsol_ai_model import MolSolTransformer, MolSolTokenizer

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL CONFIGURATION (change these to upgrade model capacity)
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_CONFIG = {
    "version": "v1.0",
    "d_model": 128,
    "nhead": 4,
    "num_encoder_layers": 3,
    "num_decoder_layers": 3,
    "dim_feedforward": 512,
    "max_seq_len": 256,
    "dropout": 0.1,
}

TRAINING_PARAMS = {
    "epochs": 1,
    "batch_size": 16,
    "learning_rate": 0.002,
    "weight_decay": 1e-5,
    "warmup_steps": 50,
    "seed": 42,
}

# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING DATASET — Curated Chemistry Q&A Pairs
# Format: (input_question, output_response)
# ═══════════════════════════════════════════════════════════════════════════════

TRAINING_DATA = [
    # ── Greetings & Identity ──
    ("hello", "Hello! I am the Singularity Oracle, your AI drug design assistant. How can I help you today?"),
    ("hi", "Greetings! I am ready to assist with molecular design and analysis. What would you like to explore?"),
    ("hi there", "Hello! Welcome to the Singularity Oracle. I can help design molecules, predict properties, and optimize drug candidates."),
    ("hey", "Hey! Ready to dive into some molecular science? Tell me what you need."),
    ("good morning", "Good morning! The Singularity Oracle is online and ready. What molecular challenge shall we tackle?"),
    ("good evening", "Good evening! Let me know what molecular design tasks you have in mind."),
    
    # ── Identity Questions ──
    ("who are you", "I am the Singularity Oracle, a proprietary AI built by the MolSol De Novo team. I specialize in drug design, molecular optimization, and chemical property prediction."),
    ("what is your name", "My name is the Singularity Oracle. I am the AI core of the MolSol De Novo platform, designed for advanced drug discovery."),
    ("what can you do", "I can design new drug molecules, predict aqueous solubility, optimize molecular properties using genetic algorithms, analyze chemical structures, and explain AI predictions. All powered by our proprietary models."),
    ("tell me about yourself", "I am a proprietary AI system trained specifically for drug design and molecular optimization. I use Graph Neural Networks and XGBoost models to predict molecular properties and guide de novo drug design."),
    ("are you chatgpt", "No, I am not ChatGPT or any third-party AI. I am the Singularity Oracle, a proprietary AI built entirely by the MolSol De Novo team for drug discovery applications."),
    ("who made you", "I was created by the MolSol De Novo team. My architecture is a custom Transformer trained specifically for chemistry and drug design."),
    ("what model are you", "I am MolSol Oracle v1, a proprietary Transformer model trained from scratch on chemistry and pharmacology data. I am not based on any third-party language model."),
    
    # ── Solubility ──
    ("what is solubility", "Solubility is the ability of a substance to dissolve in a solvent. In drug design, aqueous solubility (LogS) is critical because drugs must dissolve in water to be absorbed by the body. Our AI predicts LogS using Morgan fingerprints and XGBoost."),
    ("explain logS", "LogS is the logarithm of aqueous solubility measured in mol/L. Higher LogS means more soluble. Classifications: LogS > -1 (highly soluble), -1 to -3 (moderate), -3 to -5 (slight), < -5 (poor). Our model predicts this from molecular structure."),
    ("how to improve solubility", "To improve aqueous solubility, consider: adding hydroxyl (-OH) or amine (-NH2) groups to increase polarity, reducing molecular weight and LogP, increasing hydrogen bond donors/acceptors, and avoiding large aromatic systems. Our GA optimizer can do this automatically."),
    ("what affects drug solubility", "Key factors affecting drug solubility include: molecular weight (lower is better), LogP (hydrophobicity), number of hydrogen bond donors and acceptors, TPSA (topological polar surface area), and the presence of ionizable groups. The Lipinski Rule of Five provides guidelines."),
    ("predict solubility", "I can predict aqueous solubility (LogS) using our XGBoost model trained on Morgan fingerprints. Enter a SMILES string in the Analyze mode, and I will calculate the predicted LogS along with functional group contributions via our XAI system."),
    
    # ── Drug Design ──
    ("design a drug", "I can help design drug candidates! Tell me your target properties: What receptor are you targeting? Do you need high solubility, low toxicity, or specific molecular weight? I will use our genetic algorithm to evolve optimal molecular scaffolds."),
    ("how does drug design work", "Our AI drug design pipeline works in 3 steps: 1) Start with a parent molecule (seed), 2) Apply genetic algorithm mutations (atom swaps, functional group additions), 3) Evaluate fitness using our ML models (solubility, QED, toxicity, binding). The best candidates are selected and evolved over multiple generations."),
    ("what is de novo design", "De novo drug design means creating new molecules from scratch rather than modifying existing ones. Our platform uses genetic algorithms to evolve molecular structures, guided by AI-predicted properties like solubility, drug-likeness (QED), and synthetic accessibility."),
    ("make a safe drug", "To design a safe drug candidate, I optimize for multiple objectives simultaneously: maximizing QED (drug-likeness), minimizing toxicity alerts (PAINS/BRENK filters), maintaining good solubility, and keeping synthetic accessibility low. Use the Safe Drug mode in De Novo mutation."),
    ("design a kinase inhibitor", "Kinase inhibitors typically feature a heterocyclic core (pyrimidine, purine, or quinazoline) that mimics ATP binding. I can seed the genetic algorithm with a purine scaffold and optimize for kinase binding affinity while maintaining drug-like properties."),
    
    # ── Molecular Properties ──
    ("what is LogP", "LogP is the partition coefficient between octanol and water. It measures hydrophobicity. A positive LogP means the molecule prefers organic solvents. For oral drugs, LogP between 1-3 is ideal. Values above 5 violate Lipinski's Rule of Five."),
    ("explain lipinski rule", "Lipinski's Rule of Five predicts oral bioavailability. A drug is likely orally active if: molecular weight <= 500, LogP <= 5, hydrogen bond donors <= 5, hydrogen bond acceptors <= 10. Violations reduce the chance of good absorption."),
    ("what is QED", "QED (Quantitative Estimate of Drug-likeness) is a score from 0 to 1 that measures how drug-like a molecule is. It combines multiple properties: molecular weight, LogP, HBD, HBA, TPSA, rotatable bonds, and aromatic rings. Higher QED means more drug-like. Score > 0.67 is favorable."),
    ("what is TPSA", "TPSA (Topological Polar Surface Area) measures the polar surface of a molecule in square angstroms. It correlates with drug absorption and blood-brain barrier penetration. TPSA < 140 is generally needed for oral absorption. TPSA < 90 suggests BBB penetration."),
    ("what are hydrogen bond donors", "Hydrogen bond donors (HBD) are atoms with hydrogen attached to electronegative atoms (N-H or O-H). They form hydrogen bonds with biological targets. Lipinski's rule limits HBD to 5 for oral drugs. Too many HBD can reduce membrane permeability."),
    ("what are hydrogen bond acceptors", "Hydrogen bond acceptors (HBA) are electronegative atoms (N, O) that can accept hydrogen bonds. They are important for drug-target interactions. Lipinski's rule limits HBA to 10 for oral drugs."),
    ("what is molecular weight", "Molecular weight is the mass of a molecule. For drugs, lower molecular weight generally means better absorption. Lipinski's Rule of Five recommends MW <= 500 Da for oral drugs. Very large molecules struggle to cross cell membranes."),
    ("what is SA score", "SA Score (Synthetic Accessibility Score) ranges from 1 to 10, where 1 means very easy to synthesize and 10 means practically impossible. Our AI considers SA Score during optimization to ensure designed molecules can actually be made in the lab."),
    
    # ── XAI / Explainability ──
    ("explain the XAI map", "The XAI (Explainable AI) map shows how each atom contributes to the predicted solubility. Blue regions increase solubility (polar groups like -OH, -NH2). Red regions decrease solubility (hydrophobic groups like aromatic rings, long carbon chains). White means neutral."),
    ("what does blue mean", "In our XAI atomic contribution map, blue indicates atoms that INCREASE aqueous solubility. These are typically polar groups: hydroxyl (-OH), amines (-NH2), carboxyl (-COOH). The bluer the atom, the stronger its positive effect on solubility."),
    ("what does red mean", "In our XAI atomic contribution map, red indicates atoms that DECREASE aqueous solubility. These are typically hydrophobic groups: aromatic rings, methyl/methylene chains, halogens. The redder the atom, the more it reduces water solubility."),
    ("how does the AI work", "Our AI uses multiple models: 1) XGBoost with 1024-bit Morgan fingerprints for solubility prediction, 2) Graph Neural Networks for molecular topology analysis, 3) Perturbation-based XAI for atom-level explanations, 4) Genetic algorithms for molecular optimization."),
    
    # ── Genetic Algorithm ──
    ("what is genetic algorithm", "A genetic algorithm (GA) is an optimization technique inspired by natural evolution. We start with a population of molecules, evaluate their fitness (solubility, QED, etc.), select the best, and apply mutations (atom swaps, group additions) and crossovers to create the next generation. Over many generations, molecules improve."),
    ("how does mutation work", "Molecular mutation in our GA includes: atom type swaps (e.g., C to N), adding functional groups (-OH, -NH2, -CH3), removing terminal atoms, and adding new bonds. Each mutation is validated for chemical stability before being accepted into the population."),
    ("what is crossover", "Crossover combines features from two parent molecules. We select atoms from one parent and swap their types with atoms from the second parent. This allows combining beneficial features from different molecular scaffolds."),
    ("optimize my molecule", "I can optimize your molecule! Enter a SMILES string as the parent seed, choose your optimization goal (solubility, safety, or toxicity), and run the De Novo mutation loop. The genetic algorithm will evolve improved variants over multiple generations."),
    
    # ── Chemistry Basics ──
    ("what is SMILES", "SMILES (Simplified Molecular Input Line Entry System) is a text notation for describing molecular structures. For example, CC(=O)O is acetic acid, c1ccccc1 is benzene. Our platform uses SMILES as the primary input format for molecular analysis."),
    ("what is aspirin", "Aspirin (acetylsalicylic acid) has the SMILES CC(=O)Oc1ccccc1C(=O)O. It contains a benzene ring, ester group, and carboxylic acid. It works as an anti-inflammatory by inhibiting cyclooxygenase enzymes. MW: 180.16, moderate solubility."),
    ("what is caffeine", "Caffeine has the SMILES Cn1c(=O)c2c(ncn2C)n(C)c1=O. It is a xanthine alkaloid with a purine-like bicyclic structure. It acts as an adenosine receptor antagonist. MW: 194.19, good aqueous solubility."),
    ("what is ibuprofen", "Ibuprofen has the SMILES CC(C)Cc1ccc(cc1)C(C)C(=O)O. It is an NSAID (non-steroidal anti-inflammatory drug) with a propionic acid group attached to a para-substituted benzene ring. MW: 206.28, moderate solubility."),
    ("what is paracetamol", "Paracetamol (acetaminophen) has the SMILES CC(=O)Nc1ccc(O)cc1. It contains a para-aminophenol core with an acetamide group. It is an analgesic and antipyretic. MW: 151.16, good aqueous solubility."),
    
    # ── Platform Features ──
    ("how to use this platform", "To use MolSol De Novo: 1) Enter a SMILES string or select a Quick Example, 2) Choose Analyze mode for property prediction or De Novo mode for molecular optimization, 3) Select your AI Compute Tier for different levels of analysis, 4) Review results including XAI maps and Lipinski analysis."),
    ("what are the tiers", "We have 3 tiers: Core Research (basic analysis with XGBoost), Genesis Protocol (advanced features with radar charts, 3D viewer, mutation highlighting), and Singularity Engine (full power with GNN, quantum metrics, and synthesis engine)."),
    ("what is singularity engine", "The Singularity Engine is our most advanced compute tier. It uses Graph Neural Networks for molecular analysis, provides quantum topology projection, 4D temporal binding simulation, automated chemical synthesis planning, and this AI chat interface."),
    
    # ── Error Handling / Fallback ──
    ("I dont understand", "No problem! I am here to help. You can ask me about: molecular properties, drug design, solubility prediction, or how to use this platform. Try asking something like 'design a safe drug' or 'what is LogP'."),
    ("help", "I can help you with: 1) Designing new drug molecules, 2) Predicting molecular properties, 3) Explaining AI predictions, 4) Understanding chemistry concepts. Just ask me a question in natural language!"),
    ("thank you", "You are welcome! If you need anything else, I am always here. Happy drug designing!"),
    ("thanks", "My pleasure! Let me know if you need further molecular analysis or optimization."),
    ("bye", "Goodbye! Remember, your chat history is not stored. Come back anytime for more drug design!"),
    ("goodbye", "Farewell! Your session data will not be retained. See you next time!"),
    
    # ── Advanced Chemistry ──
    ("what is a scaffold", "A Murcko scaffold is the core ring structure of a molecule after removing side chains. We use scaffolds to ensure genetic algorithm mutations maintain the essential structural framework of the parent molecule while optimizing peripheral groups."),
    ("what are PAINS filters", "PAINS (Pan-Assay Interference Compounds) filters identify molecular substructures that frequently give false positive results in biological assays. Our platform screens for PAINS patterns to avoid designing molecules with misleading activity profiles."),
    ("what is BRENK filter", "BRENK filters identify structural alerts for reactivity and toxicity. They flag potentially problematic substructures like Michael acceptors, epoxides, and other reactive groups. We use them alongside PAINS to assess compound safety."),
    ("what is morgan fingerprint", "Morgan fingerprints (also called circular fingerprints or ECFP) encode molecular structure as bit vectors. Each bit represents a specific atomic neighborhood within a given radius. We use 1024-bit Morgan fingerprints with radius 2 as input to our XGBoost solubility model."),
    ("what is GNN", "GNN (Graph Neural Network) treats molecules as graphs where atoms are nodes and bonds are edges. Unlike fingerprints, GNNs learn molecular representations through message passing between connected atoms. Our Singularity Engine uses GNNs for more accurate property prediction."),
    ("what is BRICS", "BRICS (Breaking of Retrosynthetically Interesting Chemical Substructures) is an algorithm that decomposes molecules at strategic bonds. We use BRICS in our Automated Chemical Synthesis Engine to plan retrosynthetic pathways for designed molecules."),
    
    # ── Molecular Optimization Context ──
    ("increase solubility of my drug", "To increase solubility: I will run the genetic algorithm with the Maximize Solubility objective. This adds polar groups (-OH, -NH2), reduces LogP, and increases TPSA. Enter your molecule as SMILES and switch to De Novo mode."),
    ("reduce toxicity", "To reduce toxicity: Use the Safe Drug optimization mode. The GA will penalize PAINS/BRENK toxic alerts while maintaining drug-likeness (QED). Molecules with zero toxicity alerts will be preferred during evolution."),
    ("make it more drug-like", "To improve drug-likeness: The GA optimizes QED score while respecting Lipinski's Rule of Five. This balances molecular weight, LogP, HBD, HBA, and TPSA. Use the Multi-Objective Safe Drug mode for best results."),
    ("how accurate is the prediction", "Our XGBoost solubility model achieves good accuracy on the Delaney dataset. However, predictions are approximate and should be validated experimentally. The GNN model in Singularity Engine provides improved accuracy through graph-level molecular understanding."),
]

# ═══════════════════════════════════════════════════════════════════════════════
# DATASET CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class QADataset(Dataset):
    """Simple Q&A dataset for training the Transformer."""
    
    def __init__(self, data, tokenizer, max_len=256):
        self.data = data
        self.tokenizer = tokenizer
        self.max_len = max_len
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        question, answer = self.data[idx]
        
        src = self.tokenizer.encode(question.lower(), max_len=self.max_len)
        tgt = self.tokenizer.encode(answer, max_len=self.max_len)
        
        src = self.tokenizer.pad_sequence(src, self.max_len)
        tgt = self.tokenizer.pad_sequence(tgt, self.max_len)
        
        return (
            torch.tensor(src, dtype=torch.long),
            torch.tensor(tgt, dtype=torch.long),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def train():
    print("=" * 60)
    print("🧠 MolSol Oracle AI — Training Pipeline v1")
    print("=" * 60)
    
    # Seed everything
    seed = TRAINING_PARAMS["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"📡 Device: {device}")
    print(f"📊 Training samples: {len(TRAINING_DATA)}")
    
    # ── Build Tokenizer ──
    print("\n🔤 Building tokenizer vocabulary...")
    tokenizer = MolSolTokenizer()
    all_texts = [q for q, a in TRAINING_DATA] + [a for q, a in TRAINING_DATA]
    tokenizer.build_vocab(all_texts)
    print(f"   Vocab size: {tokenizer.vocab_size}")
    
    # ── Create Dataset ──
    dataset = QADataset(TRAINING_DATA, tokenizer, max_len=MODEL_CONFIG["max_seq_len"])
    dataloader = DataLoader(
        dataset, 
        batch_size=TRAINING_PARAMS["batch_size"], 
        shuffle=True,
        drop_last=False,
    )
    
    # ── Build Model ──
    print(f"\n🏗️  Building MolSol Transformer...")
    model = MolSolTransformer(
        vocab_size=tokenizer.vocab_size,
        d_model=MODEL_CONFIG["d_model"],
        nhead=MODEL_CONFIG["nhead"],
        num_encoder_layers=MODEL_CONFIG["num_encoder_layers"],
        num_decoder_layers=MODEL_CONFIG["num_decoder_layers"],
        dim_feedforward=MODEL_CONFIG["dim_feedforward"],
        max_seq_len=MODEL_CONFIG["max_seq_len"],
        dropout=MODEL_CONFIG["dropout"],
    ).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"   Parameters: {n_params:,} (~{n_params/1e6:.1f}M)")
    
    # ── Optimizer & Loss ──
    optimizer = optim.AdamW(
        model.parameters(),
        lr=TRAINING_PARAMS["learning_rate"],
        weight_decay=TRAINING_PARAMS["weight_decay"],
    )
    
    # Cosine annealing scheduler
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, 
        T_max=TRAINING_PARAMS["epochs"],
        eta_min=1e-6,
    )
    
    pad_idx = tokenizer.char2idx[tokenizer.PAD_TOKEN]
    criterion = nn.CrossEntropyLoss(ignore_index=pad_idx)
    
    # ── Training ──
    print(f"\n🚀 Starting training for {TRAINING_PARAMS['epochs']} epochs...")
    print("-" * 60)
    
    best_loss = float('inf')
    
    for epoch in range(1, TRAINING_PARAMS["epochs"] + 1):
        model.train()
        total_loss = 0
        n_batches = 0
        
        for src, tgt in dataloader:
            src = src.to(device)
            tgt = tgt.to(device)
            
            # Teacher forcing: input is tgt[:-1], target is tgt[1:]
            tgt_input = tgt[:, :-1]
            tgt_output = tgt[:, 1:]
            
            # Padding masks
            src_pad_mask = (src == pad_idx)
            tgt_pad_mask = (tgt_input == pad_idx)
            
            # Forward
            logits = model(src, tgt_input, src_pad_mask, tgt_pad_mask)
            
            # Reshape for loss
            logits_flat = logits.reshape(-1, tokenizer.vocab_size)
            target_flat = tgt_output.reshape(-1)
            
            loss = criterion(logits_flat, target_flat)
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            total_loss += loss.item()
            n_batches += 1
        
        scheduler.step()
        avg_loss = total_loss / max(n_batches, 1)
        
        if avg_loss < best_loss:
            best_loss = avg_loss
        
        if epoch % 10 == 0 or epoch == 1:
            lr = optimizer.param_groups[0]['lr']
            print(f"   Epoch {epoch:4d}/{TRAINING_PARAMS['epochs']} | Loss: {avg_loss:.4f} | Best: {best_loss:.4f} | LR: {lr:.6f}")
    
    print("-" * 60)
    print(f"✅ Training complete! Best loss: {best_loss:.4f}")
    
    # ── Save Everything ──
    print("\n💾 Saving model artifacts...")
    
    # Save weights
    torch.save(model.state_dict(), "molsol_ai_v1.pth")
    print(f"   ✓ Weights: molsol_ai_v1.pth")
    
    # Save tokenizer
    tokenizer.save("molsol_vocab.json")
    print(f"   ✓ Vocabulary: molsol_vocab.json")
    
    # Save config
    config = {**MODEL_CONFIG, "vocab_size": tokenizer.vocab_size}
    with open("molsol_ai_config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"   ✓ Config: molsol_ai_config.json")
    
    # ── Quick Test ──
    print("\n🧪 Quick inference test...")
    model.eval()
    
    test_questions = [
        "hello",
        "what is solubility",
        "who are you",
        "design a drug",
    ]
    
    for q in test_questions:
        src_ids = tokenizer.encode(q.lower(), max_len=MODEL_CONFIG["max_seq_len"])
        src_tensor = torch.tensor([src_ids], dtype=torch.long, device=device)
        response = model.generate(src_tensor, tokenizer, max_len=150, temperature=0.7)
        print(f"   Q: {q}")
        print(f"   A: {response[:100]}...")
        print()
    
    print("=" * 60)
    print("🎉 MolSol Oracle AI v1 is ready!")
    print("   Place molsol_ai_v1.pth, molsol_vocab.json, and")
    print("   molsol_ai_config.json in the app directory.")
    print("=" * 60)


if __name__ == "__main__":
    train()
