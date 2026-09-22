param([switch]$BuildOnly)
Set-Location $PSScriptRoot
$gameArgs = @("-m", "pygbag", "--no_opt", "--template", "web-template.tmpl", "--title", "Flappy Bird Deluxe")
if ($BuildOnly) { $gameArgs += "--build" }
python @gameArgs .
