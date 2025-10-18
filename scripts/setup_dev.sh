#!/bin/bash
# Development setup script for ha-mashov

set -e

echo "🔧 Setting up Mashov integration development environment..."

# Check Python version
python_version=$(python3 --version | awk '{print $2}')
required_version="3.11"

echo "📋 Python version: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Run initial checks
echo "✅ Running initial checks..."
ruff check .
ruff format --check .

echo "🧪 Running tests..."
pytest

echo "✨ Development environment ready!"
echo ""
echo "Next steps:"
echo "  - Run tests: pytest"
echo "  - Lint code: ruff check ."
echo "  - Format code: ruff format ."
echo "  - Start HA: Use VS Code Dev Container or manual setup"

