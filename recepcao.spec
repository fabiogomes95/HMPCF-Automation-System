# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app_recepcao.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('web_recepcao/index.html', 'web_recepcao'),
        ('web_recepcao/style.css', 'web_recepcao'),
        ('web_recepcao/script.js', 'web_recepcao'),
        ('web_recepcao/logo.png', 'web_recepcao'),
        ('web_recepcao/assets/bootstrap.min.css', 'web_recepcao/assets'),
        ('web_recepcao/assets/bootstrap.bundle.min.js', 'web_recepcao/assets'),
        ('version.json', '.'),
    ],
    hiddenimports=[
        'eel',
        'gspread',
        'google.auth',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HMPCF_Recepcao',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/robo-icon.ico',
)
