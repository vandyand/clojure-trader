# Model Files Documentation

## Autoencoder Models

- `fusion_autoencoder.pt`: The main fusion autoencoder model used by the RL trading system. This model compresses market features into a lower-dimensional representation.
  - Location: `models/fusion_autoencoder.pt`
  - Purpose: Feature compression and dimensionality reduction for the RL trading system
  - Last Updated: [Current Date]

## RL Model Checkpoints

- `rl_a2c_checkpoint.pt`: The main A2C (Advantage Actor-Critic) model checkpoint

  - Location: `models/rl_a2c_checkpoint.pt`
  - Purpose: Contains the trained RL policy and value networks
  - Last Updated: [Current Date]

- `rl_policy.pt`: The policy network weights
  - Location: `models/rl_policy.pt`
  - Purpose: Contains the trained policy network
  - Last Updated: [Current Date]

## Training Checkpoints

- `checkpoint_epoch_*.pt`: Training checkpoints saved every 10 epochs
  - Location: `models/checkpoint_epoch_*.pt`
  - Purpose: Intermediate training states for recovery and evaluation
  - Last Updated: [Current Date]

## Visualization

- `position_heatmap.png`: Position heatmap visualization
  - Location: `models/position_heatmap.png`
  - Purpose: Visual representation of trading positions
  - Last Updated: [Current Date]

## Important Notes

1. The fusion autoencoder is critical for the RL trading system's operation
2. Always keep backups of these model files
3. When training new models, consider versioning them (e.g., `fusion_autoencoder_v2.pt`)
4. The RL system expects the autoencoder at `models/fusion_autoencoder.pt`
