#Requires -Version 5.1
<#
.SYNOPSIS
    用 32 位 Python 3.8 打包「放学情况」，产物可在 Windows 7 SP1（32/64 位）运行。

.DESCRIPTION
    首次运行会自动下载并静默安装 Python 3.8.10（32 位，仅当前用户，无需管理员），
    然后在 .venv38-win7 虚拟环境里安装 PyInstaller 5.13.2 并打包。
    产物是单文件 exe，启动时会解压到系统临时目录。

.PARAMETER ReinstallPython
    重新下载并安装 32 位 Python 3.8.10。

.PARAMETER SkipTests
    跳过单元测试（不建议）。

.PARAMETER PythonDir
    已有 32 位 Python 3.8 的目录（默认 %LOCALAPPDATA%\Programs\Python\Python38-32）。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\build_x86.ps1
#>
[CmdletBinding()]
param(
    [switch]$ReinstallPython,
    [switch]$SkipTests,
    [string]$PythonDir = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# 有些环境会限制 %TEMP%，统一改用项目内的临时目录，pip / PyInstaller 都更稳
$buildTemp = Join-Path $root '.build-temp'
New-Item -ItemType Directory -Path $buildTemp -Force | Out-Null
$env:TEMP = $buildTemp
$env:TMP = $buildTemp

$pythonVersion = '3.8.10'
if ([string]::IsNullOrWhiteSpace($PythonDir)) {
    $PythonDir = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python38-32'
}
$python = Join-Path $PythonDir 'python.exe'

function Install-Python {
    $installer = Join-Path $env:TEMP ("python-$pythonVersion.exe")
    if (-not (Test-Path $installer)) {
        Write-Host "下载 Python $pythonVersion（32 位）..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion.exe" -OutFile $installer -UseBasicParsing
    }
    Write-Host "静默安装 Python $pythonVersion（32 位）到 $PythonDir ..."
    $arguments = @(
        '/quiet',
        'InstallAllUsers=0',
        "TargetDir=$PythonDir",
        'Include_test=0',
        'Include_tcltk=1',
        'Include_pip=1',
        'Include_doc=0',
        'Include_launcher=0',
        'PrependPath=0'
    )
    $process = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
    if (-not (Test-Path $python)) {
        throw "Python 安装失败（退出码 $($process.ExitCode)）。请手动安装 32 位 Python $pythonVersion 后用 -PythonDir 指定目录。"
    }
}

function Assert-Python32 {
    $probe = & $python -c "import sys, platform; print(sys.version_info[0], sys.version_info[1], platform.architecture()[0])"
    if ($LASTEXITCODE -ne 0) {
        throw "无法运行 $python"
    }
    $parts = ($probe -split '\s+')
    if ($parts.Count -lt 3) {
        throw "无法识别 Python 版本：$probe"
    }
    if ($parts[2] -ne '32bit') {
        throw "这个 Python 是 $($parts[2])，必须用 32 位 Python 才能打出兼容 32 位系统的 exe。"
    }
    if ($parts[0] -ne '3' -or $parts[1] -ne '8') {
        throw "这个 Python 是 $($parts[0]).$($parts[1])，Win7 版必须用 Python 3.8。"
    }
    Write-Host "使用 Python：$python（$($parts[0]).$($parts[1]) 32 位）"
}

if ($ReinstallPython -or -not (Test-Path $python)) {
    Install-Python
}
Assert-Python32

$venvDir = Join-Path $root '.venv38-win7'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host '创建 32 位虚拟环境 .venv38-win7 ...'
    & $python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw '创建虚拟环境失败'
    }
}

Write-Host '安装打包依赖 ...'
& $venvPython -m pip install --no-cache-dir --disable-pip-version-check --no-input -r (Join-Path $root 'requirements-win7.txt')
if ($LASTEXITCODE -ne 0) {
    throw '安装依赖失败'
}

if (-not $SkipTests) {
    Write-Host '运行单元测试 ...'
    & $venvPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw '单元测试失败，已停止打包'
    }
}

Write-Host '开始打包 ...'
# 先自己清理旧的 build 目录：PyInstaller 的 --clean 在个别机器上会因权限删不掉旧文件
Remove-Item (Join-Path $root 'build') -Recurse -Force -ErrorAction SilentlyContinue
& $venvPython -m PyInstaller --noconfirm over.spec
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller 打包失败'
}

$dist = Join-Path $root 'dist'
$targetDir = $dist
$exe = Join-Path $dist '放学情况.exe'
if (-not (Test-Path $exe)) {
    throw "没有找到打包结果：$exe"
}

Copy-Item (Join-Path $root 'xb.ico') $targetDir -Force
Copy-Item (Join-Path $root 'logo.png') $targetDir -Force
Copy-Item (Join-Path $root 'packaging\部署说明.txt') $targetDir -Force

$stream = [System.IO.File]::OpenRead($exe)
$reader = New-Object System.IO.BinaryReader($stream)
$stream.Position = 0x3C
$offset = $reader.ReadInt32()
$stream.Position = $offset + 4
$machine = $reader.ReadUInt16()
$reader.Close()
$stream.Close()
if ($machine -ne 0x14C) {
    throw ("打包结果不是 32 位 exe（PE machine=0x{0:X4}）" -f $machine)
}

$info = Get-Item $exe
Write-Host ''
Write-Host '打包完成：'
Write-Host ("  程序：{0}" -f $info.FullName)
Write-Host ("  大小：{0:N1} MB" -f ($info.Length / 1MB))
Write-Host '  架构：32 位（兼容 Win7 SP1 32/64 位）'
Write-Host '  形态：单文件版（启动时解压到系统临时目录，目标机 %TEMP% 必须可用）'
Write-Host '  同目录需要一起复制：xb.ico、logo.png、部署说明.txt'
exit 0
