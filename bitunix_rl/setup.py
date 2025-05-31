from setuptools import setup, find_packages

setup(
    name="bitunix-rl",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "sqlalchemy",
        "python-dotenv",
    ],
    python_requires=">=3.8",
) 