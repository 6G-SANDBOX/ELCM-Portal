$port = if ($null -eq $args[0]) { "5000" } else { $args[0] }

Write-Host Starting Portal on port $port

Write-Host Preventive delay for ELCM ...
Start-Sleep -Seconds 5

& ./venv/Scripts/activate.ps1
& flask run --port=$port
& deactivate