# -*- mode: python ; coding: utf-8 -*-
"""
诗韵画境 - PyInstaller 单文件打包配置
将所有资源打包进单个 EXE 文件，可直接分发运行
"""
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

import os
import PySide6

# 收集 setuptools 的所有数据文件 (包含 vendor 的 jaraco)
setuptools_datas = collect_data_files('setuptools')

# 强制收集所有 PySide6 组件
tmp_ret = collect_all('PySide6')
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = tmp_ret[0], tmp_ret[1], tmp_ret[2]

# [Fix] 手动将 PySide6 根目录下的 DLL (Qt6*.dll, shiboken6.dll) 复制到构建根目录
# 解决 "DLL load failed" 问题
pyside_root = os.path.dirname(PySide6.__file__)
extra_dlls = []
for f in os.listdir(pyside_root):
    if f.endswith('.dll'):
        extra_dlls.append((os.path.join(pyside_root, f), '.'))

pyside6_binaries += extra_dlls

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pyside6_binaries,
    datas=[
        ('resources', 'resources'),
        ('config/prompt_templates.json', 'config'),
    ] + setuptools_datas + pyside6_datas,
    hiddenimports=[
        'sqlite3',
        'PySide6.QtNetwork',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'engineio.async_drivers.threading',
        'api.video_client',
        'api.suno_client',
        'api.image_uploader',
        'jaraco.text',
    ] + pyside6_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tkinter',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 单文件 EXE 配置
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # 包含所有二进制文件
    a.zipfiles,
    a.datas,     # 包含所有数据文件
    [],
    name='PoetryToImage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                    # 使用 UPX 压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                   # 可添加: 'resources/icon.ico'
)

# 单文件模式不需要 COLLECT
# 所有内容已打包进单个 EXE
