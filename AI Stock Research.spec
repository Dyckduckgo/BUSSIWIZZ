# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('ui', 'ui'), ('config', 'config'), ('agents', 'agents'), ('database', 'database'), ('storage', 'storage'), ('services', 'services'), ('tools', 'tools')],
    hiddenimports=['flet', 'flet_desktop', 'sqlalchemy', 'sqlalchemy.dialects.sqlite', 'pydantic', 'yfinance', 'groq', 'requests', 'platformdirs', 'sqlite3', 'config.app_config', 'agents.orchestrator', 'agents.verifier', 'agents.analyst', 'agents.web_agent', 'agents.financial_agent', 'agents.sec_agent', 'agents.rd_agent', 'agents.models', 'database.db', 'database.models', 'database.repository', 'storage.db', 'services.research_service', 'financial_data', 'env_bootstrap', 'orchestrator'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

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
    version='C:/Users/HP/AppData/Local/Temp/1f1a2ca9-a1f1-4404-8155-5729b65f8540',
    icon=['C:/Users/HP/Desktop/Sarth(DO NOT OPEN)/busswizz/assets/icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI Stock Research',
)
