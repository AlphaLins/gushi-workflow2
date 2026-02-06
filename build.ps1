# Build script for PoetryToImage

Write-Host "Starting build process..." -ForegroundColor Green

# 1. Clean previous builds
if (Test-Path "dist") {
    Write-Host "Cleaning dist/..."
    Remove-Item "dist" -Recurse -Force
}
if (Test-Path "build") {
    Write-Host "Cleaning build/..."
    Remove-Item "build" -Recurse -Force
}

# 2. Run PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Cyan
try {
    pyinstaller --clean --noconfirm PoetryToImage.spec
} catch {
    Write-Error "PyInstaller failed. Please ensure 'pyinstaller' is installed (pip install pyinstaller)."
    exit 1
}

# 3. Check output
if (Test-Path "dist/PoetryToImage/PoetryToImage.exe") {
    Write-Host "Build successful!" -ForegroundColor Green
    
    # 4. Copy resources and config manually to ensure they exist
    Write-Host "Copying resources and config..." -ForegroundColor Cyan
    Copy-Item -Path "resources" -Destination "dist/PoetryToImage/resources" -Recurse -Force
    Copy-Item -Path "config" -Destination "dist/PoetryToImage/config" -Recurse -Force
    
    Write-Host "Executable is located at: dist/PoetryToImage/PoetryToImage.exe"
} else {
    Write-Error "Build failed: Executable not found."
    exit 1
}
