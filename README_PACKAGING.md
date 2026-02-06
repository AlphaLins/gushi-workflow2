# 打包指南 (Packaging Guide)

由于网络环境原因，自动安装打包工具失败。请按照以下步骤手动打包项目。

## 1. 安装 PyInstaller
请打开终端（CMD 或 PowerShell），运行以下命令安装 PyInstaller：

```powershell
pip install pyinstaller
```

如果下载速度慢，可以使用清华镜像：

```powershell
pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 2. 运行打包脚本
安装完成后，在项目根目录 (`G:\anime\Guui_software`) 运行以下命令：

```powershell
./build.ps1
```

或者手动运行 PyInstaller 命令：

```powershell
pyinstaller --clean --noconfirm PoetryToImage.spec
```

## 3. 查看结果
打包成功后，可执行文件位于 `dist/PoetryToImage/PoetryToImage.exe`。
你可以将 `dist/PoetryToImage` 整个文件夹复制到其他电脑上运行。

## 注意事项
- 如果遇到 `DLL load failed` 错误，通常是因为 PyInstaller 没有正确找到 Qt 的 DLL。打包程序通常能正确处理依赖，即使直接运行 `python main.py` 报错。
- 确保 `config` 和 `resources` 文件夹已正确包含（`build.ps1` 会自动处理）。

## 常见问题 (Troubleshooting)

### ImportError: DLL load failed while importing QtCore
如果在运行打包脚本或 `main.py` 时遇到此错误，说明 Python 环境中的 PySide6 安装已损坏或与系统 DLL 冲突。

**解决方法**：
1. 尝试强制重新安装 PySide6：
   ```powershell
   pip install --force-reinstall PySide6 -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```
2. 如果仍然失败，建议创建一个新的 Conda 环境进行打包：
   ```powershell
   conda create -n package_env python=3.10
   conda activate package_env
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
   ./build.ps1
   ```
