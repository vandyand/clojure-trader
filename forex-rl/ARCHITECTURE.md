# Forex RL Trading System - Architecture Document

## 🏗️ System Architecture Overview

This document describes the detailed architecture of the Forex RL Trading System, including component design, data flow, and integration patterns.

---

## 📊 High-Level Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Forex RL Trading System                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Data     │  │   Model     │  │  Trading    │             │
│  │   Layer     │  │   Layer     │  │   Layer     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │                 │                 │                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ OANDA API   │  │ RL Agent    │  │ Position    │             │
│  │ Feature Eng │  │ Neural Net  │  │ Manager     │             │
│  │ Validation  │  │ Reward Func │  │ Risk Mgmt   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Monitoring  │  │   Logging   │  │   Config    │             │
│  │ & Alerting  │  │ & Metrics   │  │ Management  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   OANDA     │    │  Feature    │    │    RL       │    │  Position   │
│    API      │───▶│ Engineering │───▶│   Model     │───▶│  Execution  │
│             │    │             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Data     │    │   Feature   │    │   Action    │    │   Trade     │
│ Validation  │    │ Validation  │    │ Validation  │    │ Execution   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## 🔧 Component Architecture

### 1. Data Layer

#### 1.1 OANDA API Client

```python
class OandaDataClient:
    """
    Handles all interactions with OANDA API
    - Historical data fetching
    - Real-time price streaming
    - Account information
    - Order execution
    """

    Components:
    ├── Authentication Manager
    ├── Rate Limiter
    ├── Connection Pool
    ├── Error Handler
    └── Response Parser
```

#### 1.2 Feature Engineering Pipeline

```python
class FibonacciFeatureEngineer:
    """
    Transforms raw price data into 240-dimensional feature vectors
    - Fibonacci-based price ratios
    - Rolling window calculations
    - Normalization and scaling
    """

    Components:
    ├── Price Ratio Calculator
    ├── Rolling Window Manager
    ├── Normalization Engine
    └── Feature Validator
```

#### 1.3 Data Validation System

```python
class DataValidator:
    """
    Ensures data quality and consistency
    - Missing data detection
    - Outlier identification
    - Schema validation
    """

    Components:
    ├── Schema Validator
    ├── Quality Checker
    ├── Outlier Detector
    └── Completeness Monitor
```

### 2. Model Layer

#### 2.1 Neural Network Architecture

```python
class ForexRLNetwork(nn.Module):
    """
    Deep neural network: 240 → 512 → 256 → 128 → 20
    - Batch normalization
    - Dropout regularization
    - ReLU activation
    """

    Layers:
    ├── Input Layer (240 → 512)
    ├── Hidden Layer 1 (512 → 256)
    ├── Hidden Layer 2 (256 → 128)
    └── Output Layer (128 → 20)

    Features:
    ├── Batch Normalization
    ├── Dropout (0.1)
    ├── Weight Initialization
    └── Gradient Clipping
```

#### 2.2 RL Agent System

```python
class PPOAgent:
    """
    Proximal Policy Optimization agent
    - Policy network (actor)
    - Value network (critic)
    - Experience buffer
    """

    Components:
    ├── Policy Network
    ├── Value Network
    ├── Experience Buffer
    ├── Advantage Calculator
    └── Loss Functions
```

#### 2.3 Reward Function

```python
class RewardCalculator:
    """
    Multi-component reward system from reward-info.md
    - Position normalization
    - Entropy penalty
    - Differential Sharpe Ratio
    - Confidence weighting
    """

    Components:
    ├── Position Normalizer
    ├── Entropy Calculator
    ├── DSR Calculator
    ├── Confidence Weighter
    └── Reward Clipper
```

### 3. Trading Layer

#### 3.1 Position Manager

```python
class PositionManager:
    """
    Manages trading positions and portfolio state
    - Position tracking
    - Risk calculations
    - Portfolio optimization
    """

    Components:
    ├── Position Tracker
    ├── Risk Calculator
    ├── Portfolio Optimizer
    └── Exposure Monitor
```

#### 3.2 Risk Management System

```python
class RiskManager:
    """
    Implements risk controls and limits
    - Position size limits
    - Drawdown protection
    - Correlation monitoring
    """

    Components:
    ├── Position Sizer
    ├── Drawdown Monitor
    ├── Correlation Tracker
    └── Limit Enforcer
```

#### 3.3 Order Execution Engine

```python
class OrderExecutor:
    """
    Executes trades through OANDA API
    - Order placement
    - Execution monitoring
    - Slippage tracking
    """

    Components:
    ├── Order Placer
    ├── Execution Monitor
    ├── Slippage Tracker
    └── Fill Reporter
```

---

## 🔄 Data Flow Patterns

### 1. Training Data Flow

```
Historical Data Request
         ↓
OANDA API Response (OHLCV)
         ↓
Data Validation & Cleaning
         ↓
Fibonacci Feature Calculation
         ↓
Feature Normalization
         ↓
240-Dimensional Feature Vector
         ↓
RL Training Environment
         ↓
Policy Network Forward Pass
         ↓
Action Sampling (20 positions)
         ↓
Reward Calculation
         ↓
Policy Gradient Update
```

### 2. Inference Data Flow

```
Real-time Price Request
         ↓
OANDA API Streaming
         ↓
Feature Engineering Pipeline
         ↓
240-Dimensional State Vector
         ↓
Trained Policy Network
         ↓
Position Recommendations (20)
         ↓
Risk Management Checks
         ↓
Position Sizing
         ↓
Order Execution
         ↓
Portfolio Update
```

### 3. Monitoring Data Flow

```
System Metrics Collection
         ↓
Performance Metrics Calculation
         ↓
Risk Metrics Assessment
         ↓
Alert Threshold Checking
         ↓
Notification System
         ↓
Dashboard Updates
         ↓
Log Aggregation
```

---

## 🏛️ Architectural Patterns

### 1. Layered Architecture

```
┌─────────────────────────────────────┐
│         Presentation Layer          │  ← Scripts, CLI, Notebooks
├─────────────────────────────────────┤
│          Business Layer             │  ← Trading Logic, RL Agent
├─────────────────────────────────────┤
│         Data Access Layer           │  ← OANDA API, Data Processing
├─────────────────────────────────────┤
│        Infrastructure Layer         │  ← Logging, Config, Monitoring
└─────────────────────────────────────┘
```

### 2. Pipeline Pattern

```
Data Source → Transformer → Validator → Processor → Output
     ↓             ↓           ↓           ↓         ↓
  OANDA API → Feature Eng → Validation → RL Model → Positions
```

### 3. Observer Pattern

```
Subject (Market Data) ──┐
                        ├─→ Observer 1 (Feature Engineer)
                        ├─→ Observer 2 (Risk Monitor)
                        └─→ Observer 3 (Performance Tracker)
```

### 4. Strategy Pattern

```
Context (RL Agent)
    ↓
Strategy Interface
    ├─→ PPO Strategy
    ├─→ A2C Strategy
    └─→ SAC Strategy
```

---

## 🔌 Integration Architecture

### 1. External Integrations

#### OANDA API Integration

```python
Integration Pattern: REST API + WebSocket
Authentication: OAuth2 Bearer Token
Rate Limiting: 100 requests/second
Error Handling: Exponential backoff
Data Format: JSON
```

#### Monitoring Integration

```python
Integration Pattern: Push Metrics
Protocols: HTTP/HTTPS
Formats: Prometheus metrics, JSON logs
Destinations: TensorBoard, Grafana, CloudWatch
```

### 2. Internal Communication

#### Inter-Component Communication

```python
Pattern: Event-Driven Architecture
Message Bus: In-memory queues
Event Types: DataReceived, ModelUpdated, PositionChanged
Serialization: JSON/Pickle
```

#### Configuration Management

```python
Pattern: Centralized Configuration
Format: YAML/JSON
Sources: Files, Environment Variables, Command Line
Validation: Schema-based validation
```

---

## 📦 Module Dependencies

### Dependency Graph

```
scripts/
├── train.py
│   ├── training.trainer
│   ├── models.agent
│   └── data.data_fetcher
├── inference.py
│   ├── inference.predictor
│   ├── models.network
│   └── data.oanda_client
└── backtest.py
    ├── evaluation.backtester
    ├── models.agent
    └── data.data_fetcher

training/
├── trainer.py
│   ├── training.environment
│   ├── models.agent
│   └── training.utils
├── environment.py
│   ├── models.reward
│   ├── data.feature_engineer
│   └── config.settings
└── utils.py
    └── config.settings

models/
├── agent.py
│   ├── models.network
│   ├── models.reward
│   └── config.settings
├── network.py
│   └── config.settings
└── reward.py
    └── config.settings

data/
├── oanda_client.py
│   └── config.settings
├── feature_engineer.py
│   └── config.settings
└── data_validator.py
    └── config.settings
```

### Circular Dependency Prevention

```python
Dependency Rules:
1. Scripts can import from all modules
2. Training can import from models, data, config
3. Models can import from config only
4. Data can import from config only
5. Config has no dependencies
```

---

## 🔒 Security Architecture

### 1. Authentication & Authorization

```python
API Key Management:
├── Environment Variables
├── Secure Key Storage
├── Key Rotation
└── Access Logging

Authorization Levels:
├── Read-only (Market Data)
├── Trade Execution
└── Account Management
```

### 2. Data Security

```python
Data Protection:
├── Encryption at Rest
├── Encryption in Transit
├── Input Validation
└── Output Sanitization

Sensitive Data:
├── API Keys
├── Account Information
├── Trading Positions
└── Performance Metrics
```

### 3. Network Security

```python
Network Controls:
├── HTTPS/TLS 1.3
├── Certificate Validation
├── Rate Limiting
└── IP Whitelisting
```

---

## 📈 Scalability Architecture

### 1. Horizontal Scaling

```python
Scalable Components:
├── Data Fetching (Multiple API clients)
├── Feature Engineering (Parallel processing)
├── Model Inference (Model serving)
└── Monitoring (Distributed metrics)
```

### 2. Vertical Scaling

```python
Resource Optimization:
├── Memory Management
├── CPU Optimization
├── GPU Utilization
└── I/O Optimization
```

### 3. Caching Strategy

```python
Cache Layers:
├── API Response Cache (Redis)
├── Feature Cache (Memory)
├── Model Cache (Disk)
└── Configuration Cache (Memory)
```

---

## 🔧 Configuration Architecture

### Configuration Hierarchy

```python
Configuration Sources (Priority Order):
1. Command Line Arguments
2. Environment Variables
3. Configuration Files
4. Default Values

Configuration Categories:
├── Model Configuration
├── Training Configuration
├── Data Configuration
├── Trading Configuration
└── System Configuration
```

### Environment Management

```python
Environments:
├── Development
│   ├── Local data sources
│   ├── Mock APIs
│   └── Debug logging
├── Testing
│   ├── Test data sets
│   ├── Sandbox APIs
│   └── Comprehensive logging
└── Production
    ├── Live data sources
    ├── Production APIs
    └── Error logging
```

---

## 📊 Performance Architecture

### 1. Performance Monitoring

```python
Metrics Collection:
├── System Metrics (CPU, Memory, Disk)
├── Application Metrics (Latency, Throughput)
├── Business Metrics (Returns, Drawdown)
└── Custom Metrics (Model Performance)
```

### 2. Performance Optimization

```python
Optimization Strategies:
├── Algorithmic Optimization
├── Data Structure Optimization
├── Memory Pool Management
└── Asynchronous Processing
```

### 3. Bottleneck Identification

```python
Profiling Tools:
├── CPU Profiling
├── Memory Profiling
├── I/O Profiling
└── Network Profiling
```

---

## 🚀 Deployment Architecture

### 1. Containerization

```dockerfile
Container Strategy:
├── Base Image: python:3.9-slim
├── Multi-stage Build
├── Security Scanning
└── Size Optimization
```

### 2. Orchestration

```yaml
Kubernetes Deployment:
├── Deployment Manifests
├── Service Definitions
├── ConfigMaps
├── Secrets
└── Persistent Volumes
```

### 3. CI/CD Pipeline

```python
Pipeline Stages:
├── Code Quality Checks
├── Unit Testing
├── Integration Testing
├── Security Scanning
├── Performance Testing
├── Build & Package
└── Deploy & Monitor
```

---

This architecture document provides a comprehensive blueprint for implementing a robust, scalable, and maintainable Forex RL Trading System. Each component is designed to be modular, testable, and independently deployable while maintaining strong integration patterns.
