$ErrorActionPreference = 'Stop'
$data = Join-Path $PSScriptRoot '..\data\demo.json'
if (Test-Path $data) { Remove-Item $data -Force }
Write-Output 'Demo state reset. Start the server to recreate data/demo.json from data/seed.json.'
