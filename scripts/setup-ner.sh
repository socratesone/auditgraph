#!/usr/bin/env bash
set -e
MODEL="${1:-en_core_web_sm}"
python -m spacy download "$MODEL"
echo "NER model '$MODEL' ready."
