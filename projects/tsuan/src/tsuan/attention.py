"""Uncertainty-weighted attention mechanisms.

Implements:
- Uncertainty encoding (Eq 2): u_enc = MLP(u_mask)
- Dynamic temperature (Eq 3): λ = Softplus(MLP(h, u_enc))
- Intra-modal uncertainty-weighted attention (Eq 4)
- Cross-modal SAR→optical attention with physical penalty (Eq 5)
- Feature aggregation (Eq 6): z = z_intra + z_cross + h (residual)
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class UncertaintyEncoder(nn.Module):
    """Encode binary/probabilistic cloud mask into uncertainty embeddings (Eq 2).

    u_enc = MLP(u_mask)  ∈ R^{T×D×H'×W'}
    """

    def __init__(self, embed_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Conv2d(1, embed_dim // 4, kernel_size=1),
            nn.GELU(),
            nn.Conv2d(embed_dim // 4, embed_dim, kernel_size=1),
        )

    def forward(self, u_mask: torch.Tensor) -> torch.Tensor:
        """Encode uncertainty mask.

        Parameters
        ----------
        u_mask : Tensor of shape (B, T, 1, H', W')
            Per-pixel cloud probability or binary mask.

        Returns
        -------
        u_enc : Tensor of shape (B, T, D, H', W')
        """
        B, T = u_mask.shape[:2]
        u_flat = u_mask.reshape(B * T, *u_mask.shape[2:])
        u_enc = self.mlp(u_flat)
        _, D, Hp, Wp = u_enc.shape
        return u_enc.reshape(B, T, D, Hp, Wp)


class DynamicTemperature(nn.Module):
    """Dynamic attention temperature (Eq 3).

    λ = Softplus(MLP(cat(h, u_enc)))
    """

    def __init__(self, embed_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(2 * embed_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, 1),
            nn.Softplus(),
        )

    def forward(self, h: torch.Tensor, u_enc: torch.Tensor) -> torch.Tensor:
        """Compute per-pixel dynamic temperature.

        Parameters
        ----------
        h : Tensor of shape (B, T, D, H', W')
        u_enc : Tensor of shape (B, T, D, H', W')

        Returns
        -------
        lam : Tensor of shape (B, T, 1, H', W')
        """
        B, T, D, Hp, Wp = h.shape
        # Pool over spatial dims for per-timestep lambda, or compute per-pixel
        cat = torch.cat([h, u_enc], dim=2)  # (B, T, 2D, H', W')
        cat = cat.permute(0, 1, 3, 4, 2).reshape(B * T * Hp * Wp, 2 * D)
        lam = self.mlp(cat)  # (B*T*H'*W', 1)
        return lam.reshape(B, T, 1, Hp, Wp)


class IntraModalAttention(nn.Module):
    """Uncertainty-weighted self-attention within a single modality (Eq 4).

    score(i,j) = (q_i · k_j) / √D - λ_j · u_enc_j
    α = softmax(score)
    z_intra = Σ α_j · v_j
    """

    def __init__(self, embed_dim: int, num_heads: int = 8, dropout: float = 0.1):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        assert embed_dim % num_heads == 0

        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        h: torch.Tensor,
        u_enc: torch.Tensor,
        lam: torch.Tensor,
    ) -> torch.Tensor:
        """Compute intra-modal uncertainty-weighted attention.

        Parameters
        ----------
        h : Tensor of shape (B, T, D, H', W')
        u_enc : Tensor of shape (B, T, D, H', W')
        lam : Tensor of shape (B, T, 1, H', W')

        Returns
        -------
        z_intra : Tensor of shape (B, T, D, H', W')
        """
        B, T, D, Hp, Wp = h.shape
        S = Hp * Wp  # spatial tokens

        # Reshape: merge spatial into sequence, keep time as query axis
        # (B, T, D, H', W') → (B*S, T, D)
        h_seq = h.permute(0, 3, 4, 1, 2).reshape(B * S, T, D)
        u_seq = u_enc.permute(0, 3, 4, 1, 2).reshape(B * S, T, D)
        lam_seq = lam.permute(0, 3, 4, 1, 2).reshape(B * S, T, 1)

        # Project Q, K, V
        Q = self.q_proj(h_seq)  # (B*S, T, D)
        K = self.k_proj(h_seq)
        V = self.v_proj(h_seq)

        # Reshape for multi-head: (B*S, num_heads, T, head_dim)
        Q = Q.reshape(B * S, T, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.reshape(B * S, T, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.reshape(B * S, T, self.num_heads, self.head_dim).transpose(1, 2)

        # Scaled dot-product scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.head_dim**0.5)
        # (B*S, num_heads, T, T)

        # Uncertainty penalty: average u_enc over D, expand for heads
        u_penalty = u_seq.mean(dim=-1, keepdim=True)  # (B*S, T, 1)
        u_penalty = (lam_seq * u_penalty).squeeze(-1)  # (B*S, T)
        u_penalty = u_penalty.unsqueeze(1).unsqueeze(2)  # (B*S, 1, 1, T)
        scores = scores - u_penalty

        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, V)  # (B*S, num_heads, T, head_dim)
        out = out.transpose(1, 2).reshape(B * S, T, D)
        out = self.out_proj(out)

        # Reshape back: (B*S, T, D) → (B, T, D, H', W')
        return out.reshape(B, Hp, Wp, T, D).permute(0, 3, 4, 1, 2)


class CrossModalAttention(nn.Module):
    """SAR-guided cross-modal attention with physical penalty (Eq 5).

    Q from optical, K/V from SAR.
    score(i,j) = (q_opt_i · k_sar_j) / √D - γ · P_viol(j)
    z_cross = Σ α_j · v_sar_j
    """

    def __init__(
        self,
        embed_dim: int,
        num_heads: int = 8,
        dropout: float = 0.1,
        gamma: float = 0.1,
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.gamma = gamma

        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        self.dropout = nn.Dropout(dropout)

        # Physical violation detector: small CNN on SAR features
        self.pviol_net = nn.Sequential(
            nn.Linear(embed_dim, embed_dim // 4),
            nn.GELU(),
            nn.Linear(embed_dim // 4, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        h_opt: torch.Tensor,
        h_sar: torch.Tensor,
    ) -> torch.Tensor:
        """Cross-modal attention from optical queries to SAR keys/values.

        Parameters
        ----------
        h_opt : Tensor of shape (B, T, D, H', W')
        h_sar : Tensor of shape (B, T, D, H', W')

        Returns
        -------
        z_cross : Tensor of shape (B, T, D, H', W')
        """
        B, T, D, Hp, Wp = h_opt.shape
        S = Hp * Wp

        opt_seq = h_opt.permute(0, 3, 4, 1, 2).reshape(B * S, T, D)
        sar_seq = h_sar.permute(0, 3, 4, 1, 2).reshape(B * S, T, D)

        Q = self.q_proj(opt_seq)
        K = self.k_proj(sar_seq)
        V = self.v_proj(sar_seq)

        Q = Q.reshape(B * S, T, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.reshape(B * S, T, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.reshape(B * S, T, self.num_heads, self.head_dim).transpose(1, 2)

        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.head_dim**0.5)

        # Physical violation penalty
        p_viol = self.pviol_net(sar_seq)  # (B*S, T, 1)
        p_viol = p_viol.squeeze(-1).unsqueeze(1).unsqueeze(2)  # (B*S, 1, 1, T)
        scores = scores - self.gamma * p_viol

        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, V)
        out = out.transpose(1, 2).reshape(B * S, T, D)
        out = self.out_proj(out)

        return out.reshape(B, Hp, Wp, T, D).permute(0, 3, 4, 1, 2)


class TSUANAttentionBlock(nn.Module):
    """Full attention block: intra-modal + cross-modal + residual (Eq 6).

    z = z_intra + z_cross + h  (residual connection)
    """

    def __init__(
        self,
        embed_dim: int = 128,
        num_heads: int = 8,
        dropout: float = 0.1,
        gamma: float = 0.1,
    ):
        super().__init__()
        self.u_encoder = UncertaintyEncoder(embed_dim)
        self.dyn_temp = DynamicTemperature(embed_dim)
        self.intra_attn = IntraModalAttention(embed_dim, num_heads, dropout)
        self.cross_attn = CrossModalAttention(embed_dim, num_heads, dropout, gamma)
        self.norm1 = nn.LayerNorm(embed_dim)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 4),
            nn.GELU(),
            nn.Linear(embed_dim * 4, embed_dim),
            nn.Dropout(dropout),
        )

    def forward(
        self,
        h_opt: torch.Tensor,
        h_sar: torch.Tensor,
        u_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Forward pass through full attention block.

        Parameters
        ----------
        h_opt : Tensor (B, T, D, H', W')
        h_sar : Tensor (B, T, D, H', W')
        u_mask : Tensor (B, T, 1, H', W')

        Returns
        -------
        z : Tensor (B, T, D, H', W')
        """
        B, T, D, Hp, Wp = h_opt.shape

        # Uncertainty encoding & dynamic temperature
        u_enc = self.u_encoder(u_mask)
        lam = self.dyn_temp(h_opt, u_enc)

        # Intra-modal attention on optical stream
        z_intra = self.intra_attn(h_opt, u_enc, lam)

        # Cross-modal SAR → optical attention
        z_cross = self.cross_attn(h_opt, h_sar)

        # Feature aggregation with residual (Eq 6)
        z = z_intra + z_cross + h_opt

        # Layer norm + FFN (applied per-pixel)
        z_perm = z.permute(0, 1, 3, 4, 2)  # (B, T, H', W', D)
        z_perm = self.norm1(z_perm)
        z_ffn = self.ffn(z_perm)
        z_perm = self.norm2(z_perm + z_ffn)

        return z_perm.permute(0, 1, 4, 2, 3)  # (B, T, D, H', W')
