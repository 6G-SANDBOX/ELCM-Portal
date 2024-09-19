$python = $args[0]

try {
    $version = & $python --version
    Write-Output "Using $version"

    Write-Output "Creating Virtualenv..."
    & $python -m venv .\venv

    . .\venv\Scripts\Activate.ps1

    Write-Output "Installing requirements..."
    pip install -r .\requirements.txt
    pip install waitress

    Write-Output "Initializing database..."
    flask db upgrade

    Deactivate
}
catch {
    Write-Output "Could not obtain Python version, please check script parameter. Aborting."
}
