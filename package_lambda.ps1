# Lambda コンソールのランタイムとアーキテクチャに合わせる。
$LambdaPython = "3.14"
$LambdaArch = "x86_64"

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$platform = switch ($LambdaArch) {
    "x86_64" { "manylinux2014_x86_64" }
    "arm64" { "manylinux2014_aarch64" }
    default { throw "アーキテクチャは x86_64 か arm64 を指定します: $LambdaArch" }
}
$abi = "cp" + ($LambdaPython -replace "\.", "")

$build = Join-Path $PSScriptRoot "build"
$zipPath = Join-Path $PSScriptRoot "function.zip"
$sources = @(
    "lambda_function.py",
    "Actions.py",
    "CronAction.py",
    "ReplyAction.py",
    "decos.py",
    "message.py"
)

if (Test-Path $build) {
    Remove-Item -Recurse -Force $build
}
New-Item -ItemType Directory -Path $build | Out-Null

& py -m pip install -r requirements.txt -t $build `
    --platform $platform `
    --implementation cp `
    --python-version $LambdaPython `
    --abi $abi `
    --only-binary=:all:
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

foreach ($name in $sources) {
    Copy-Item -Path (Join-Path $PSScriptRoot $name) -Destination $build
}

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open(
    $zipPath,
    [System.IO.Compression.ZipArchiveMode]::Create
)
try {
    $buildFull = (Resolve-Path $build).Path
    Get-ChildItem -Path $build -Recurse -File |
        Where-Object { $_.FullName -notmatch "\\__pycache__\\" -and $_.Extension -ne ".pyc" } |
        ForEach-Object {
            $relative = $_.FullName.Substring($buildFull.Length).TrimStart("\", "/").Replace("\", "/")
            [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $_.FullName,
                $relative
            )
        }
}
finally {
    $archive.Dispose()
}

Write-Host "wrote $zipPath"
