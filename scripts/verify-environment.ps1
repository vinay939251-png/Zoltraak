$ErrorActionPreference = 'SilentlyContinue'
Write-Output 'Agentic Collections Copilot — local environment'
foreach ($name in @('node','npm','python','docker','git')) {
  $command = Get-Command $name
  if ($command) { Write-Output "${name}: AVAILABLE ($($command.Source))" } else { Write-Output "${name}: UNAVAILABLE" }
}
Write-Output 'Application mode: plain-local synthetic DEMO'
Write-Output 'External integrations are disabled unless explicitly configured.'
