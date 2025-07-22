"""
Fusion Autoencoder for Unified Futures RL Trading System

Compresses 1,242 input features (300 Fibonacci + 782 ETF + 160 crypto technical)
to a 149-dimensional bottleneck representation for the RL policy network.

Features:
- Scaled Tanh inputs for improved stability
- LeakyReLU activation with BatchNorm
- Progressive compression: 1,242 → 621 → 310 → 149
- Robust initialization and regularization
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from typing import Tuple, Optional
import logging
from pathlib import Path

from constants import (
    TOTAL_INPUT_FEATURES, AUTOENCODER_BOTTLENECK_DIM
)

logger = logging.getLogger(__name__)

class ScaledTanhInput(nn.Module):
    """
    Scaled Tanh input layer for improved feature representation.
    Helps with gradient flow and provides bounded outputs.
    """
    
    def __init__(self, n_features: int):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(n_features))
        self.bias = nn.Parameter(torch.zeros(n_features))
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.scale * x + self.bias)

class FusionAutoencoder(nn.Module):
    """
    Fusion autoencoder that compresses multi-market features to a compact representation.
    
    Architecture:
    - Input: 1,242 features (300 Fibonacci + 782 ETF + 160 crypto technical)
    - Encoder: 1,242 → 621 → 310 → 149
    - Bottleneck: 149 dimensions (tanh activation)
    - Decoder: 149 → 310 → 621 → 1,242
    """
    
    def __init__(self, n_features: int = TOTAL_INPUT_FEATURES, 
                 bottleneck_dim: int = AUTOENCODER_BOTTLENECK_DIM):
        super().__init__()
        
        self.n_features = n_features
        self.bottleneck_dim = bottleneck_dim
        
        # Define layer sizes with progressive compression
        hidden_dim1 = n_features // 2      # 621
        hidden_dim2 = n_features // 4      # 310
        
        # Input scaling layer
        self.input_layer = ScaledTanhInput(n_features)
        
        # Encoder layers with LeakyReLU activation
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden_dim1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim1),
            nn.Dropout(0.1),
            
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim2),
            nn.Dropout(0.1),
            
            nn.Linear(hidden_dim2, bottleneck_dim),
            nn.Tanh(),  # Keep tanh in bottleneck for bounded representation
            nn.BatchNorm1d(bottleneck_dim)
        )
        
        # Decoder layers with LeakyReLU activation
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, hidden_dim2),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim2),
            nn.Dropout(0.1),
            
            nn.Linear(hidden_dim2, hidden_dim1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim1),
            nn.Dropout(0.1),
            
            nn.Linear(hidden_dim1, n_features)
        )
        
        # Initialize weights using He initialization
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights using He initialization for LeakyReLU."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the autoencoder.
        
        Args:
            x: Input features [batch_size, n_features]
            
        Returns:
            Reconstructed features [batch_size, n_features]
        """
        # Apply scaled tanh input transformation
        x = self.input_layer(x)
        
        # Encode
        z = self.encoder(x)
        
        # Decode
        return self.decoder(z)
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Encode input features to bottleneck representation.
        
        Args:
            x: Input features [batch_size, n_features]
            
        Returns:
            Bottleneck representation [batch_size, bottleneck_dim]
        """
        x = self.input_layer(x)
        return self.encoder(x)

class AutoencoderTrainer:
    """
    Trainer for the fusion autoencoder.
    """
    
    def __init__(self, 
                 n_features: int = TOTAL_INPUT_FEATURES,
                 bottleneck_dim: int = AUTOENCODER_BOTTLENECK_DIM,
                 learning_rate: float = 1e-3,
                 weight_decay: float = 1e-4):
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = FusionAutoencoder(n_features, bottleneck_dim).to(self.device)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), 
                                  lr=learning_rate, 
                                  weight_decay=weight_decay)
        
        logger.info(f"Autoencoder initialized on {self.device}")
        logger.info(f"Input features: {n_features}, Bottleneck: {bottleneck_dim}")
    
    def train_epoch(self, dataloader: DataLoader) -> float:
        """
        Train for one epoch.
        
        Args:
            dataloader: DataLoader with training data
            
        Returns:
            Average training loss
        """
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        for batch_features in dataloader:
            if isinstance(batch_features, (list, tuple)):
                batch_features = batch_features[0]
            
            batch_features = batch_features.to(self.device)
            
            # Forward pass
            reconstructed = self.model(batch_features)
            loss = self.criterion(reconstructed, batch_features)
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        return total_loss / num_batches if num_batches > 0 else 0.0
    
    def validate(self, dataloader: DataLoader) -> float:
        """
        Validate the autoencoder.
        
        Args:
            dataloader: DataLoader with validation data
            
        Returns:
            Average validation loss
        """
        self.model.eval()
        total_loss = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch_features in dataloader:
                if isinstance(batch_features, (list, tuple)):
                    batch_features = batch_features[0]
                
                batch_features = batch_features.to(self.device)
                
                # Forward pass
                reconstructed = self.model(batch_features)
                loss = self.criterion(reconstructed, batch_features)
                
                total_loss += loss.item()
                num_batches += 1
        
        return total_loss / num_batches if num_batches > 0 else 0.0
    
    def train(self, 
              train_features: np.ndarray,
              val_features: np.ndarray = None,
              n_epochs: int = 400,
              batch_size: int = 256,
              save_path: str = None) -> dict:
        """
        Train the autoencoder.
        
        Args:
            train_features: Training features [n_samples, n_features]
            val_features: Validation features [n_samples, n_features]
            n_epochs: Number of training epochs
            batch_size: Batch size
            save_path: Path to save the trained model
            
        Returns:
            Training history
        """
        # Prepare data
        train_tensor = torch.FloatTensor(train_features)
        train_dataset = TensorDataset(train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        if val_features is not None:
            val_tensor = torch.FloatTensor(val_features)
            val_dataset = TensorDataset(val_tensor)
            val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        # Training history
        history = {
            'train_loss': [],
            'val_loss': []
        }
        
        logger.info(f"Starting autoencoder training for {n_epochs} epochs")
        
        for epoch in range(n_epochs):
            # Train
            train_loss = self.train_epoch(train_loader)
            history['train_loss'].append(train_loss)
            
            # Validate
            if val_features is not None:
                val_loss = self.validate(val_loader)
                history['val_loss'].append(val_loss)
                
                if epoch % 50 == 0:
                    logger.info(f"Epoch {epoch}: Train Loss = {train_loss:.6f}, Val Loss = {val_loss:.6f}")
            else:
                if epoch % 50 == 0:
                    logger.info(f"Epoch {epoch}: Train Loss = {train_loss:.6f}")
        
        # Save model
        if save_path:
            self.save_model(save_path)
            logger.info(f"Model saved to {save_path}")
        
        return history
    
    def save_model(self, path: str):
        """Save the trained model."""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'n_features': self.model.n_features,
            'bottleneck_dim': self.model.bottleneck_dim
        }, path)
    
    def load_model(self, path: str):
        """Load a trained model."""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Model loaded from {path}")
    
    def encode_features(self, features: np.ndarray) -> np.ndarray:
        """
        Encode features to bottleneck representation.
        
        Args:
            features: Input features [n_samples, n_features]
            
        Returns:
            Bottleneck representation [n_samples, bottleneck_dim]
        """
        self.model.eval()
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).to(self.device)
            encoded = self.model.encode(features_tensor)
            return encoded.cpu().numpy()

def create_autoencoder_model(n_features: int = TOTAL_INPUT_FEATURES,
                           bottleneck_dim: int = AUTOENCODER_BOTTLENECK_DIM) -> FusionAutoencoder:
    """
    Create a fusion autoencoder model.
    
    Args:
        n_features: Number of input features
        bottleneck_dim: Bottleneck dimension
        
    Returns:
        FusionAutoencoder model
    """
    return FusionAutoencoder(n_features, bottleneck_dim)

def train_autoencoder(features: np.ndarray,
                     n_epochs: int = 400,
                     batch_size: int = 256,
                     learning_rate: float = 1e-3,
                     weight_decay: float = 1e-4,
                     save_path: str = None) -> Tuple[FusionAutoencoder, dict]:
    """
    Train a fusion autoencoder.
    
    Args:
        features: Input features [n_samples, n_features]
        n_epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        weight_decay: Weight decay
        save_path: Path to save the trained model
        
    Returns:
        Trained autoencoder and training history
    """
    # Split data for validation
    n_samples = len(features)
    split_idx = int(0.8 * n_samples)
    
    train_features = features[:split_idx]
    val_features = features[split_idx:]
    
    # Create trainer
    trainer = AutoencoderTrainer(
        n_features=features.shape[1],
        learning_rate=learning_rate,
        weight_decay=weight_decay
    )
    
    # Train
    history = trainer.train(
        train_features=train_features,
        val_features=val_features,
        n_epochs=n_epochs,
        batch_size=batch_size,
        save_path=save_path
    )
    
    return trainer.model, history 