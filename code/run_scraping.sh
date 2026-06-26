#!/bin/bash

# ============================================================================
# run_scraping.sh - Run complete scraping pipeline
# ============================================================================

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🚀 COMPLETE SCRAPING PIPELINE"
echo "════════════════════════════════════════════════════════════════════════════════"

# Check API key
if [ -z "$MP_API_KEY" ]; then
    echo "❌ MP_API_KEY not set!"
    echo ""
    echo "Set it with:"
    echo "  export MP_API_KEY='your_api_key_here'"
    echo ""
    exit 1
fi

echo ""
echo "✅ MP_API_KEY is set"
echo ""

# Create data directory
mkdir -p data

# Run pipeline
echo "🔄 Starting scraping pipeline..."
echo ""

python screaping.py

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "✅ PIPELINE COMPLETE!"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Output files:"
ls -lh data/0* data/*.pkl 2>/dev/null || echo "  (files not created yet)"
echo ""
echo "Next steps:"
echo "1. Check data/07_ml_ready.csv - your ML-ready dataset"
echo "2. Use data/scaler.pkl and data/pca.pkl for inference"
echo "3. Train your DNN model on this data!"
echo ""
