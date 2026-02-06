# 诗韵画境 - 单文件 EXE 构建脚本
# 将所有资源打包进单个 EXE 文件，可直接分发运行

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  诗韵画境 - 单文件 EXE 构建脚本"        -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# 错误时停止
$ErrorActionPreference = "Stop"

# 清理旧的构建文件
Write-Host "[1/5] 清理旧的构建文件..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist, publish -ErrorAction SilentlyContinue
Write-Host "✓ 清理完成" -ForegroundColor Green
Write-Host ""

# 安装 PyInstaller
Write-Host "[2/5] 检查 PyInstaller..." -ForegroundColor Yellow
try {
    $pyinstaller = pip show pyinstaller 2>$null
    if (-not $pyinstaller) {
        Write-Host "  正在安装 PyInstaller..." -ForegroundColor Gray
        pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
    }
    Write-Host "✓ PyInstaller 已就绪" -ForegroundColor Green
} catch {
    Write-Host "✗ PyInstaller 安装失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 执行打包
Write-Host "[3/5] 开始打包..." -ForegroundColor Yellow
Write-Host "  这可能需要几分钟，请耐心等待..." -ForegroundColor Gray
Write-Host ""

pyinstaller --clean --noconfirm PoetryToImage.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 打包失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ 打包完成" -ForegroundColor Green
Write-Host ""

# 创建发布目录
Write-Host "[4/5] 准备发布文件..." -ForegroundColor Yellow
$publishDir = "publish"
New-Item -ItemType Directory -Force -Path $publishDir | Out-Null

# 复制 EXE 到发布目录
Copy-Item -Force dist\PoetryToImage.exe $publishDir\

# 创建使用说明文件
$readme = @"
诗韵画境 v1.0.0
===============

使用说明：
1. 双击 PoetryToImage.exe 启动应用
2. 首次运行时需要配置 API 密钥
3. 配置完成后即可开始使用

系统要求：
- Windows 10/11 (64位)
- 无需安装 Python

配置文件位置：
~\.guui_config.json (C:\Users\你的用户名\.guui_config.json)

日志文件位置：
程序目录\logs\

更多信息请访问：https://github.com/AlphaLins/gushi-workflow2
"@

$readme | Out-File -FilePath "$publishDir\README.txt" -Encoding UTF8

Write-Host "✓ 发布文件已准备" -ForegroundColor Green
Write-Host ""

# 显示结果
Write-Host "[5/5] 完成！" -ForegroundColor Green
Write-Host ""

$exeSize = (Get-Item "$publishDir\PoetryToImage.exe").Length / 1MB
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  打包成功！"                              -ForegroundColor Green
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "输出位置: $publishDir\PoetryToImage.exe" -ForegroundColor White
Write-Host "文件大小: $($exeSize.ToString('F2')) MB" -ForegroundColor White
Write-Host ""
Write-Host "分发方式：" -ForegroundColor Yellow
Write-Host "  将 $publishDir 文件夹压缩为 ZIP 后分发" -ForegroundColor Gray
Write-Host ""
