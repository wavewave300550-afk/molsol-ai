"""
🧠 MolSol Oracle AI — Proprietary Conversational AI Model
==========================================================
A custom Transformer-based Encoder-Decoder model trained from scratch
for chemistry / drug design Q&A.

Architecture:
  • Character-level tokenizer (no external tokenizer dependency)
  • Small Transformer Encoder-Decoder (~3M parameters)
  • Fully upgradeable: just swap the .pth + vocab files

Model Versions:
  v1 — Initial training on curated chemistry Q&A dataset

Author: MolSol De Novo Team (Proprietary)
"""

import os
import json
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, List, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# TOKENIZER
# ═══════════════════════════════════════════════════════════════════════════════

class MolSolTokenizer:
    """Character-level tokenizer with special tokens.
    
    Simple, robust, and doesn't depend on any external library.
    Upgrade path: switch to BPE or SentencePiece in v2.
    """
    
    PAD_TOKEN = "<PAD>"
    SOS_TOKEN = "<SOS>"
    EOS_TOKEN = "<EOS>"
    UNK_TOKEN = "<UNK>"
    
    def __init__(self):
        self.char2idx = {}
        self.idx2char = {}
        self.vocab_size = 0
    
    def build_vocab(self, texts: List[str]):
        """Build vocabulary from a list of text strings."""
        special = [self.PAD_TOKEN, self.SOS_TOKEN, self.EOS_TOKEN, self.UNK_TOKEN]
        chars = set()
        for text in texts:
            chars.update(text)
        
        all_tokens = special + sorted(list(chars))
        self.char2idx = {ch: i for i, ch in enumerate(all_tokens)}
        self.idx2char = {i: ch for ch, i in self.char2idx.items()}
        self.vocab_size = len(all_tokens)
    
    def encode(self, text: str, max_len: int = 256) -> List[int]:
        """Encode text to token IDs with SOS/EOS."""
        sos = self.char2idx[self.SOS_TOKEN]
        eos = self.char2idx[self.EOS_TOKEN]
        unk = self.char2idx[self.UNK_TOKEN]
        
        ids = [sos]
        for ch in text[:max_len - 2]:
            ids.append(self.char2idx.get(ch, unk))
        ids.append(eos)
        return ids
    
    def decode(self, ids: List[int]) -> str:
        """Decode token IDs back to text."""
        result = []
        for idx in ids:
            token = self.idx2char.get(idx, "")
            if token in (self.PAD_TOKEN, self.SOS_TOKEN):
                continue
            if token == self.EOS_TOKEN:
                break
            if token == self.UNK_TOKEN:
                result.append("?")
            else:
                result.append(token)
        return "".join(result)
    
    def pad_sequence(self, ids: List[int], max_len: int) -> List[int]:
        """Pad or truncate to max_len."""
        pad_id = self.char2idx[self.PAD_TOKEN]
        if len(ids) >= max_len:
            return ids[:max_len]
        return ids + [pad_id] * (max_len - len(ids))
    
    def save(self, path: str):
        """Save vocabulary to JSON."""
        data = {
            "char2idx": self.char2idx,
            "version": "v1"
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "MolSolTokenizer":
        """Load vocabulary from JSON."""
        tokenizer = cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tokenizer.char2idx = data["char2idx"]
        # Convert string keys back to int for idx2char
        tokenizer.idx2char = {int(v): k for k, v in tokenizer.char2idx.items()}
        tokenizer.vocab_size = len(tokenizer.char2idx)
        return tokenizer


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFORMER MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class PositionalEncoding(nn.Module):
    """Standard sinusoidal positional encoding."""
    
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class MolSolTransformer(nn.Module):
    """
    Custom Encoder-Decoder Transformer for MolSol Oracle AI.
    
    Architecture (v1 defaults — ~3M params):
      • Embedding dim: 128
      • 3 Encoder layers, 3 Decoder layers
      • 4 Attention heads
      • FFN dim: 512
    
    Upgrade path:
      • v2: Increase to 256 embed, 6 layers → ~12M params
      • v3: Add cross-attention to molecular features
    """
    
    def __init__(
        self,
        vocab_size: int,
        d_model: int = 128,
        nhead: int = 4,
        num_encoder_layers: int = 3,
        num_decoder_layers: int = 3,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        max_seq_len: int = 256,
    ):
        super().__init__()
        
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        
        # Shared embedding
        self.embedding = nn.Embedding(vocab_size, d_model, padding_idx=0)
        self.pos_encoder = PositionalEncoding(d_model, max_seq_len, dropout)
        
        # Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_encoder_layers)
        
        # Decoder
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=num_decoder_layers)
        
        # Output projection
        self.output_proj = nn.Linear(d_model, vocab_size)
        
        self._init_weights()
    
    def _init_weights(self):
        """Xavier uniform initialization for stable training."""
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)
    
    def _generate_square_subsequent_mask(self, sz: int, device: torch.device) -> torch.Tensor:
        """Generate causal mask for decoder."""
        mask = torch.triu(torch.ones(sz, sz, device=device), diagonal=1).bool()
        return mask
    
    def forward(
        self,
        src: torch.Tensor,         # (batch, src_len)
        tgt: torch.Tensor,         # (batch, tgt_len)
        src_pad_mask: Optional[torch.Tensor] = None,
        tgt_pad_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Forward pass for training."""
        # Embeddings
        src_emb = self.pos_encoder(self.embedding(src) * math.sqrt(self.d_model))
        tgt_emb = self.pos_encoder(self.embedding(tgt) * math.sqrt(self.d_model))
        
        # Causal mask for decoder
        tgt_mask = self._generate_square_subsequent_mask(tgt.size(1), tgt.device)
        
        # Encode
        memory = self.encoder(src_emb, src_key_padding_mask=src_pad_mask)
        
        # Decode
        output = self.decoder(
            tgt_emb, memory,
            tgt_mask=tgt_mask,
            tgt_key_padding_mask=tgt_pad_mask,
            memory_key_padding_mask=src_pad_mask,
        )
        
        # Project to vocab
        logits = self.output_proj(output)
        return logits
    
    @torch.no_grad()
    def generate(
        self,
        src: torch.Tensor,
        tokenizer: MolSolTokenizer,
        max_len: int = 200,
        temperature: float = 0.8,
        top_k: int = 40,
    ) -> str:
        """Auto-regressive generation (greedy with temperature + top-k)."""
        self.eval()
        device = src.device
        
        # Encode source
        src_emb = self.pos_encoder(self.embedding(src) * math.sqrt(self.d_model))
        memory = self.encoder(src_emb)
        
        # Start with SOS token
        sos_id = tokenizer.char2idx[tokenizer.SOS_TOKEN]
        eos_id = tokenizer.char2idx[tokenizer.EOS_TOKEN]
        
        generated = [sos_id]
        
        for _ in range(max_len):
            tgt_tensor = torch.tensor([generated], dtype=torch.long, device=device)
            tgt_emb = self.pos_encoder(self.embedding(tgt_tensor) * math.sqrt(self.d_model))
            tgt_mask = self._generate_square_subsequent_mask(tgt_tensor.size(1), device)
            
            output = self.decoder(tgt_emb, memory, tgt_mask=tgt_mask)
            logits = self.output_proj(output[:, -1, :])  # last token
            
            # Temperature scaling
            logits = logits / temperature
            
            # Top-k filtering
            if top_k > 0:
                top_k_vals, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                threshold = top_k_vals[:, -1].unsqueeze(-1)
                logits[logits < threshold] = float('-inf')
            
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, 1).item()
            
            if next_token == eos_id:
                break
            
            generated.append(next_token)
        
        return tokenizer.decode(generated)


# ═══════════════════════════════════════════════════════════════════════════════
# LOADING / INFERENCE API
# ═══════════════════════════════════════════════════════════════════════════════

# Model file paths (upgrade by replacing these files)
MODEL_WEIGHTS_PATH = "molsol_ai_v1.pth"
VOCAB_PATH = "molsol_vocab.json"
MODEL_CONFIG_PATH = "molsol_ai_config.json"

def get_model_version() -> str:
    """Return the current model version string."""
    if os.path.exists(MODEL_CONFIG_PATH):
        with open(MODEL_CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        return cfg.get("version", "v1.0")
    return "v1.0"


def load_molsol_ai(
    weights_path: str = MODEL_WEIGHTS_PATH,
    vocab_path: str = VOCAB_PATH,
    config_path: str = MODEL_CONFIG_PATH,
) -> Tuple[Optional[MolSolTransformer], Optional[MolSolTokenizer], bool]:
    """
    Load the MolSol Oracle AI model and tokenizer.
    
    Returns:
        (model, tokenizer, is_loaded)
    
    Upgrade instructions:
        1. Retrain with expanded dataset using train_molsol_ai.py
        2. Replace molsol_ai_v1.pth with the new weights
        3. Update molsol_ai_config.json version field
    """
    if not os.path.exists(weights_path) or not os.path.exists(vocab_path):
        return None, None, False
    
    try:
        # Load tokenizer
        tokenizer = MolSolTokenizer.load(vocab_path)
        
        # Load config
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        
        # Build model with saved config
        model = MolSolTransformer(
            vocab_size=tokenizer.vocab_size,
            d_model=config.get("d_model", 128),
            nhead=config.get("nhead", 4),
            num_encoder_layers=config.get("num_encoder_layers", 3),
            num_decoder_layers=config.get("num_decoder_layers", 3),
            dim_feedforward=config.get("dim_feedforward", 512),
            max_seq_len=config.get("max_seq_len", 256),
        )
        
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        state_dict = torch.load(weights_path, map_location=device)
        model.load_state_dict(state_dict)
        model.to(device)
        model.eval()
        
        return model, tokenizer, True
        
    except Exception as e:
        print(f"[MolSol AI] Failed to load model: {e}")
        return None, None, False


def generate_ai_response(
    prompt: str,
    model: MolSolTransformer,
    tokenizer: MolSolTokenizer,
    max_len: int = 200,
    temperature: float = 0.8,
) -> str:
    """Generate a response using the MolSol Oracle AI.
    
    This is the main inference entry point used by the chat UI.
    """
    device = next(model.parameters()).device
    
    # Encode the prompt
    src_ids = tokenizer.encode(prompt, max_len=256)
    src_tensor = torch.tensor([src_ids], dtype=torch.long, device=device)
    
    # Generate
    response = model.generate(
        src_tensor,
        tokenizer,
        max_len=max_len,
        temperature=temperature,
    )
    
    return response.strip()
