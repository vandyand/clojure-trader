#!/usr/bin/env python3
"""
Script to fix import paths after refactoring.
Updates all 'from rl.' imports to 'from trading_systems.rl.'
"""

import os
import re
import sys
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix import statements in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix from rl. imports
        content = re.sub(r'from rl\.', 'from trading_systems.rl.', content)
        content = re.sub(r'import rl\.', 'import trading_systems.rl.', content)
        
        # Fix sys.path.append references
        content = re.sub(
            r'sys\.path\.append\(.*?rl.*?\)',
            'sys.path.append(str(Path(__file__).resolve().parent.parent / "trading_systems" / "rl"))',
            content
        )
        
        # Write back the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Fixed imports in: {file_path}")
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

def main():
    """Main function to fix imports in all Python files."""
    # Get the project root
    project_root = Path(__file__).resolve().parent.parent
    
    # Files to fix (relative to project root)
    files_to_fix = [
        "scripts/analyze_forex_features.py",
        "scripts/analyze_usd_chf_volume.py",
        "scripts/compare_positions.py",
        "scripts/run_trading_system.py",
        "scripts/ingest_all_etfs.py",
        "scripts/check_features.py",
        "scripts/test_position_logic.py",
        "scripts/ingest_all_top20_full_history.py",
        "scripts/check_usd_chf.py",
        "scripts/ingest_all_top20.py"
    ]
    
    for file_path in files_to_fix:
        full_path = project_root / file_path
        if full_path.exists():
            fix_imports_in_file(full_path)
        else:
            print(f"File not found: {full_path}")

if __name__ == "__main__":
    main() 