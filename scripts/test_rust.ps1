param(
    [switch]$VerboseCargo
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$preferredToolchainRoot = "D:\rustup\toolchains\stable-x86_64-pc-windows-msvc\bin"
$preferredCargoHome = "D:\cargo-home"
$preferredRustupHome = "D:\rustup"

if (Test-Path $preferredToolchainRoot) {
    $env:PATH = "$preferredToolchainRoot;$env:PATH"
    $env:RUSTC = Join-Path $preferredToolchainRoot "rustc.exe"
    if (Test-Path $preferredCargoHome) {
        $env:CARGO_HOME = $preferredCargoHome
    }
    if (Test-Path $preferredRustupHome) {
        $env:RUSTUP_HOME = $preferredRustupHome
    }
}

$cargoCommand = Get-Command cargo -ErrorAction Stop
$arguments = @("test", "--workspace")
if ($VerboseCargo) {
    $arguments += "--verbose"
}

Write-Host "Using cargo from $($cargoCommand.Source)"
& $cargoCommand.Source @arguments
