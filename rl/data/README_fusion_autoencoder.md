# Fusion Autoencoder for Financial Feature Representation

This project implements an improved autoencoder for dimensionality reduction of financial time series data, combining both forex and ETF features into a unified latent representation.

## Architecture

The fusion autoencoder uses a deep neural network architecture with the following key components:

- **Enhanced ScaledTanh Input Layer**: Applies learned scaling and bias to each input feature with intelligent initialization based on feature statistics
- **Deep Encoder Network**: Multi-layer network with LeakyReLU activations, batch normalization, and dropout regularization
- **89-Dimensional Bottleneck**: A compressed representation with the same dimensionality as the number of forex pairs in the dataset
- **Symmetric Decoder Network**: Mirrors the encoder for reconstruction with appropriate layer sizes

## Key Improvements

1. **Enhanced Feature Scaling**: Better initialization of the ScaledTanhInput layer based on feature statistics
2. **Dropout Regularization**: Added dropout layers (20%) to improve generalization
3. **Batch Normalization**: Added to all layers for more stable training
4. **Optimized Bottleneck Size**: Reduced to 89 dimensions for better feature extraction
5. **Larger Batch Size**: Increased to 512 for more stable gradient updates
6. **LeakyReLU Activations**: Replaced ReLU to avoid dead neurons and improve gradient flow
7. **Cosine Annealing Scheduler**: More effective learning rate schedule
8. **Data Preprocessing**: Better handling of zeros, extreme values, and outliers
9. **Dimension Balancing**: More balanced layer sizes based on bottleneck dimensions

## Performance Metrics

### Forex Data

- **MSE**: 7.97e+09
- **MAE**: 29,545
- **Processing Speed**: ~12,646 samples/second
- **Active Bottleneck Dimensions**: 85.2 out of 89
- **Best Feature R²**: 0.74 (GBP_JPY volume relative volatility)

### ETF Data

- **MSE**: 9.76e+10
- **MAE**: 106,527
- **Processing Speed**: ~32,865 samples/second
- **Active Bottleneck Dimensions**: 85.1 out of 89
- **Best Feature R²**: 0.07 (BTC-USD volume relative volatility)

## Usage

```python
# Load the model
from rl.data.test_autoencoder import load_model

model, feature_names = load_model('models/fusion_autoencoder.pt')

# Encode features to get latent representation
with torch.no_grad():
    features_tensor = torch.tensor(features, dtype=torch.float32)
    latent_vector = model.encode(features_tensor)
```

## Visualization of Latent Space

The 89-dimensional latent space effectively captures the essential patterns and relationships in the financial data. Each dimension corresponds to a unique aspect of market behavior, with most dimensions actively contributing to the representation.

## Future Improvements

1. **Variational Autoencoder**: Add KL divergence regularization for better latent space structure
2. **Attention Mechanisms**: Add attention layers to focus on more important features
3. **Time-Aware Encoding**: Incorporate temporal dynamics more explicitly
4. **Adversarial Training**: Add adversarial loss to improve robustness
5. **Feature Selection**: Further optimize feature selection to reduce redundancy
6. **Specialized Architectures**: Explore LSTM or Transformer-based autoencoders for time series

## Training Parameters

- **Epochs**: 300 (with early stopping)
- **Batch Size**: 512
- **Learning Rate**: 0.001 (with cosine annealing)
- **Weight Decay**: 0.0001
- **Dropout Rate**: 0.2
- **Bottleneck Dimensions**: 89
- **Optimizer**: AdamW
