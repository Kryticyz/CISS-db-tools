# Installation Guide

## Prerequisites

- **macOS** (Apple Silicon or Intel)
- **Conda/Miniconda/Mamba** - For package management
- **40 GB free disk space** - For data storage

## Quick Install

```bash
# Clone repository
git clone https://github.com/yourusername/plantnet.git
cd plantnet

# Create conda environment
conda env create -f environment.yml

# Activate environment
conda activate plantnet

# Install package
pip install -e .

# Verify installation
plantnet --version
```

## Detailed Installation Steps

### 1. Install Conda

If you don't have conda installed:

```bash
# Download Miniconda for macOS (Apple Silicon)
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
bash Miniconda3-latest-MacOSX-arm64.sh

# Or for Intel Macs
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh

# Follow the prompts and restart your terminal
```

Alternatively, install via Homebrew:
```bash
brew install --cask miniconda
```

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/plantnet.git
cd plantnet
```

### 3. Create Conda Environment

The `environment.yml` file specifies all dependencies including Python 3.11:

```bash
conda env create -f environment.yml
```

This will:
- Install Python 3.11 (for MPS stability)
- Install PyTorch, FAISS, and all scientific packages
- Resolve OpenMP library conflicts automatically
- Take 5-10 minutes depending on your internet connection

### 4. Activate the Environment

```bash
conda activate plantnet
```

You should see `(plantnet)` in your terminal prompt.

### 5. Install the PlantNet Package

Install in **editable mode** for development:

```bash
pip install -e .
```

Or install normally:

```bash
pip install .
```

### 6. Verify Installation

Test that everything works:

```bash
# Check version
plantnet --version

# Check available commands
plantnet --help

# Test Python import
python -c "import plantnet; print(plantnet.__version__)"

# Test CLI tools
plantnet-db-query --help
plantnet-deduplicate --help
```

## Why Conda?

### OpenMP Conflict Resolution

The previous pip installation had conflicts between multiple OpenMP libraries:
- **PyTorch**: Ships with `libomp.dylib`
- **NumPy**: Links to `libiomp5.dylib` (from Homebrew)
- **FAISS**: Bundles its own `libomp.dylib`

This caused the error:
```
OMP: Error #15: Initializing libomp.dylib, but found libomp.dylib already initialized.
```

**Conda solves this** by ensuring all packages use a single, shared OpenMP library from `conda-forge`.

### Python 3.11 for MPS Stability

Python 3.13 has stability issues with PyTorch's MPS (Metal Performance Shaders) backend on Apple Silicon, causing segmentation faults:

```
zsh: segmentation fault  python scripts/images/batch_generate_embeddings.py
```

**Conda environment pins Python 3.11**, which has mature, stable MPS support.

## Troubleshooting

### "conda: command not found"

**Problem**: Conda not in PATH  
**Solution**: Restart your terminal, or manually activate:
```bash
source ~/miniconda3/bin/activate
```

### "Solving environment: failed"

**Problem**: Conda can't resolve dependencies  
**Solution**: Use mamba (faster solver):
```bash
conda install -c conda-forge mamba
mamba env create -f environment.yml
```

### "FAISS not found" after installation

**Problem**: FAISS not installed correctly  
**Solution**: Reinstall FAISS:
```bash
conda install -c conda-forge faiss-cpu --force-reinstall
```

### "MPS backend failed" error

**Problem**: MPS issues (shouldn't happen with Python 3.11)  
**Solution**: Force CPU mode:
```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

### Package installation fails

**Problem**: Conflicting package versions  
**Solution**: Clean install:
```bash
conda env remove -n plantnet
conda env create -f environment.yml
conda activate plantnet
pip install -e . --no-cache-dir
```

### ImportError: No module named 'plantnet'

**Problem**: Package not installed  
**Solution**: Install in editable mode:
```bash
pip install -e .
```

Make sure you're in the repository root directory where `pyproject.toml` is located.

## Environment Management

### Activate/Deactivate

```bash
# Activate
conda activate plantnet

# Deactivate
conda deactivate
```

### Update Dependencies

If `environment.yml` changes:

```bash
conda env update -f environment.yml --prune
```

### Remove Environment

To completely remove the environment:

```bash
conda deactivate
conda env remove -n plantnet
```

### List Environments

```bash
conda env list
```

## Verification Checklist

After installation, verify these work:

- [ ] `conda activate plantnet` succeeds
- [ ] `python --version` shows 3.11.x
- [ ] `conda list | grep omp` shows only one OpenMP library
- [ ] `plantnet --version` shows version 1.0.0
- [ ] `python -c "import torch; print(torch.backends.mps.is_available())"` shows True (on Apple Silicon)
- [ ] `python -c "import faiss; print('FAISS OK')"` succeeds
- [ ] All CLI commands show help: `plantnet-deduplicate --help`

## Next Steps

Once installed, see:
- [Quick Start Guide](quickstart.md) - 5-minute tutorial
- [Database Guide](DATABASE_GUIDE.md) - SQLite database usage
- [README](../README.md) - Project overview and workflows

## Migrating from Pip

If you previously had a pip-based installation:

```bash
# Remove old virtual environment
rm -rf .venv/

# Follow installation steps above
conda env create -f environment.yml
conda activate plantnet
pip install -e .
```

Your data directory is unchanged, so all databases and images remain accessible.

## Development Installation

For developers contributing to the project:

```bash
# Clone and setup
git clone https://github.com/yourusername/plantnet.git
cd plantnet

# Create environment with dev tools
conda env create -f environment.yml

# Install in editable mode
conda activate plantnet
pip install -e ".[dev]"

# Verify dev tools
black --version
pytest --version
ruff --version
```

## System Requirements

- **OS**: macOS 10.15+ (Catalina or later)
- **Architecture**: Apple Silicon (M1/M2/M3) or Intel x86_64
- **RAM**: 8 GB minimum, 16 GB recommended
- **Disk**: 40 GB free space (13 GB images, 2.8 GB databases, rest for raw data)
- **Network**: Broadband for downloading GBIF data and images

## Optional: Faster Installs with Mamba

Mamba is a faster drop-in replacement for conda:

```bash
# Install mamba
conda install -c conda-forge mamba

# Use mamba instead of conda
mamba env create -f environment.yml
mamba activate plantnet
```

Mamba can be 10-20x faster at solving environments!

---

**Installation complete!** Proceed to the [Quick Start Guide](quickstart.md).
