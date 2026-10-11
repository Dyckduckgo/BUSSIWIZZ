# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for AI Stock Research.
Builds standalone Windows application with all assets, modules, and security exclusions.
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
project_root = os.path.abspath(os.path.dirname(__file__))

# Data folders to bundle (excluding sensitive files, database files, and local logs)
datas = [
    (os.path.join(project_root, 'assets'), 'assets'),
    (os.path.join(project_root, 'ui'), 'ui'),
    (os.path.join(project_root, 'config'), 'config'),
    (os.path.join(project_root, 'agents'), 'agents'),
    (os.path.join(project_root, 'database'), 'database'),
    (os.path.join(project_root, 'storage'), 'storage'),
    (os.path.join(project_root, 'services'), 'services'),
    (os.path.join(project_root, 'tools'), 'tools'),
]

# Hidden imports for dynamic reflection and SQLite support
hiddenimports = [
    'flet',
    'flet_desktop',
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
    'pydantic',
    'yfinance',
    'groq',
    'requests',
    'platformdirs',
    'sqlite3',
    'config.app_config',
    'agents.orchestrator',
    'agents.verifier',
    'agents.analyst',
    'agents.web_agent',
    'agents.financial_agent',
    'agents.sec_agent',
    'agents.rd_agent',
    'agents.models',
    'database.db',
    'database.models',
    'database.repository',
    'storage.db',
    'services.research_service',
    'financial_data',
    'env_bootstrap',
    'orchestrator',
]

# Explicit exclusions to ensure NO secrets, caches, or test databases are packaged
excludes = [
    'tests',
    'data',
    '.env',
    '.env.local',
    '.git',
    '.pytest_cache',
]

a = Analysis(
    ['app.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI Stock Research',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'assets', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI Stock Research',
)
