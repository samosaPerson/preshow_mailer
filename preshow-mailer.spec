# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['dashboard.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('src/templates', 'src/templates'), ('data/examples', 'data/examples')],
    hiddenimports=[],
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
    name='preshow-mailer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='preshow-mailer',
)
app = BUNDLE(
    coll,
    name='preshow-mailer.app',
    icon=None,
    bundle_identifier=None,
)
