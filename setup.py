from setuptools import setup, find_packages

setup(
    name="bitunix_rl",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "requests",
        "python-dotenv",
        "gymnasium",
        "stable-baselines3",
        "torch",
        "matplotlib",
        "seaborn",
        "tqdm",
        "scikit-learn",
        "joblib",
        "optuna",
        "wandb"
    ],
    python_requires=">=3.8",
) 