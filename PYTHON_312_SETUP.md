
# Python 3.12 Setup Guide for Auction Automation System

## Overview

This guide addresses Python 3.12 compatibility issues in the auction automation system, particularly the `AttributeError: module 'pkgutil' has no attribute 'ImpImporter'` error.

## Quick Setup for Python 3.12

### Method 1: Use Python 3.12 Specific Requirements (Recommended)

```bash
# Create a virtual environment
python3.12 -m venv venv_py312
source venv_py312/bin/activate  # On Windows: venv_py312\Scripts\activate

# Upgrade pip and setuptools first
pip install --upgrade pip setuptools

# Install Python 3.12 compatible packages
pip install -r requirements-py312.txt
```

### Method 2: Alternative Installation with Conda

```bash
# Create conda environment with Python 3.12
conda create -n auction_py312 python=3.12
conda activate auction_py312

# Install packages via conda-forge when possible
conda install -c conda-forge numpy>=1.26.0 pandas scikit-learn opencv pillow
conda install -c conda-forge tensorflow pytorch torchvision

# Install remaining packages via pip
pip install -r requirements-py312.txt
```

## Key Changes for Python 3.12 Compatibility

### Critical Updates Made:

1. **NumPy**: Updated from 1.25.2 to >=1.26.0
   - **Reason**: NumPy 1.25.2 and earlier versions fail with Python 3.12 due to `pkgutil.ImpImporter` deprecation
   - **Fix**: NumPy 1.26.0+ uses Meson build system, avoiding the deprecated `setuptools`/`pkg_resources` dependency

2. **Pillow**: Updated from 10.1.0 to >=10.1.0
   - **Reason**: Pillow 10.1.0+ officially supports Python 3.12
   - **Note**: Earlier versions may work but aren't officially tested

3. **Playwright**: Updated from 1.40.0 to >=1.39.0
   - **Reason**: Playwright 1.39.0+ includes `greenlet` 3.0.0 compatibility for Python 3.12
   - **Note**: Earlier versions fail due to `greenlet` C API incompatibility

4. **Removed asyncio**: 
   - **Reason**: `asyncio` is built into Python 3.12, external package causes conflicts

## Troubleshooting Common Issues

### Issue 1: `pkgutil.ImpImporter` Error
```
AttributeError: module 'pkgutil' has no attribute 'ImpImporter'
```
**Solution**: Ensure NumPy >= 1.26.0 and upgrade setuptools:
```bash
pip install --upgrade setuptools
pip install "numpy>=1.26.0"
```

### Issue 2: PyTorch Installation Issues
PyTorch 2.1.1 may not have official Python 3.12 wheels. Options:
```bash
# Option A: Use nightly builds
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cpu

# Option B: Use conda
conda install pytorch torchvision -c pytorch-nightly

# Option C: Downgrade to Python 3.11 for this project
```

### Issue 3: 32-bit Windows Compatibility
Some packages (like Pandas 2.1.3) lack 32-bit Python 3.12 wheels.
**Solution**: Use 64-bit Python 3.12 or downgrade to Python 3.11.

### Issue 4: Selenium-Wire Issues
If using `selenium-wire`, you may need to downgrade `blinker`:
```bash
pip uninstall blinker selenium-wire -y
pip install blinker==1.7.0
pip install selenium-wire
```

## Verification Steps

After installation, verify your setup:

```python
import sys
print(f"Python version: {sys.version}")

# Test critical packages
import numpy as np
print(f"NumPy version: {np.__version__}")

import pandas as pd
print(f"Pandas version: {pd.__version__}")

import sklearn
print(f"Scikit-learn version: {sklearn.__version__}")

import cv2
print(f"OpenCV version: {cv2.__version__}")

import PIL
print(f"Pillow version: {PIL.__version__}")

print("✅ All critical packages loaded successfully!")
```

## Alternative Solutions

### If You Can't Upgrade Dependencies:

1. **Use Python 3.11**: Most stable option for this project
   ```bash
   pyenv install 3.11.6
   pyenv local 3.11.6
   pip install -r requirements.txt
   ```

2. **Use Docker**: Containerize with Python 3.11
   ```dockerfile
   FROM python:3.11-slim
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   ```

3. **Use Virtual Environment Manager**: 
   ```bash
   # With pyenv
   pyenv install 3.11.6
   pyenv virtualenv 3.11.6 auction-system
   pyenv activate auction-system
   ```

## Support and Resources

- [NumPy Python 3.12 Support Issue](https://github.com/numpy/numpy/issues/23808)
- [Playwright Python 3.12 Support](https://github.com/microsoft/playwright-python/issues/2096)
- [TensorFlow Installation Guide](https://www.tensorflow.org/install/pip)
- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)

## Last Updated
July 13, 2025 - Updated for latest package versions and Python 3.12 compatibility.
