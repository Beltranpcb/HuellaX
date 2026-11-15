# Arranca HuellaX en Windows (equivalente a ./start.sh + ./scripts/serve_cover.sh).
#
# Uso, desde la raíz del repositorio:
#   .\start.cmd                     (recomendado: evita el bloqueo de scripts de PowerShell)
#   powershell -ExecutionPolicy Bypass -File .\start.ps1 [-NoOptional] [-NoBrowser]
#
# Servicios:
#   BD 8797 · MoveScope 8790 · Sky View 8830 · Página de entrada 8840   (siempre)
#   AnyField C 8798      (opcional: si existe su base de datos)
#   Catálogo B 8799      (opcional: si existe var\star_catalog.sqlite)
#
# Registros y PID en %TEMP%\huellax. No escribe nada dentro del repositorio.
# Para pararlo: .\stop.cmd
[CmdletBinding()]
param(
    [switch]$NoOptional,  # no arrancar B ni C
    [switch]$NoBrowser    # no abrir el navegador al terminar
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$SystemRoot = Join-Path $Root 'system'
$StateDir = Join-Path $env:TEMP 'huellax'
$PidFile = Join-Path $StateDir 'pids.json'

function Fail([string]$msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# --- Python -----------------------------------------------------------------
# Se prueban todos los intérpretes del PATH (un .venv activado, el de python.org, el lanzador
# "py"...) y se usa el primero que de verdad puede ejecutar HuellaX. No basta con "import PIL":
# un entorno roto puede tener la carpeta PIL vacía y fallar después en "from PIL import Image".
# En Windows 11 "python" puede ser además el alias de la Microsoft Store, que no hace nada.
# Solo comillas simples: PowerShell 5.1 elimina las dobles al pasar argumentos a programas.
$CheckScript = @'
import sys
if sys.version_info < (3, 9):
    raise SystemExit('Python %d.%d: hace falta 3.9 o superior' % sys.version_info[:2])
try:
    import numpy, sqlite3, http.server
    from PIL import Image
except Exception as exc:
    raise SystemExit('%s: %s' % (type(exc).__name__, exc))
print(sys.executable)
'@

function Get-PythonCandidates {
    $seen = @{}
    $list = @()
    foreach ($name in 'python', 'python3') {
        foreach ($cmd in @(Get-Command $name -All -CommandType Application -ErrorAction SilentlyContinue)) {
            if (-not $seen.ContainsKey($cmd.Source)) { $seen[$cmd.Source] = 1; $list += , @($cmd.Source) }
        }
    }
    if (Get-Command 'py' -ErrorAction SilentlyContinue) { $list += , @('py', '-3') }
    return $list
}

$Python = $null
$rejected = @()
foreach ($cand in Get-PythonCandidates) {
    $exe, $pre = $cand[0], @($cand | Select-Object -Skip 1)
    try {
        # En PowerShell 5.1, 2>&1 con ErrorActionPreference=Stop lanza excepción: se aísla.
        $out = & { $ErrorActionPreference = 'Continue'; & $exe @($pre + @('-c', $CheckScript)) 2>&1 }
    } catch { continue }
    $text = (@($out) | ForEach-Object { "$_" }) -join ' '
    if ($LASTEXITCODE -eq 0 -and $text -and (Test-Path $text.Trim())) { $Python = $text.Trim(); break }
    if ($text -and $exe -notlike '*WindowsApps*') { $rejected += "$exe -> $($text.Trim())" }
}

foreach ($r in $rejected) { Write-Host "Aviso: se descarta $r" -ForegroundColor DarkYellow }
if (-not $Python) {
    $msg = 'No hay ningún Python 3.9+ con numpy y Pillow funcionando.'
    if ($rejected) {
        $msg += "`n       Si usas un entorno virtual roto, recréalo o instala las dependencias:"
        $msg += "`n       python -m pip install --force-reinstall numpy pillow"
    } else {
        $msg += "`n       Instala Python desde https://www.python.org/downloads/ (marca `"Add python.exe to PATH`")"
        $msg += "`n       y después: python -m pip install numpy pillow"
    }
    Fail $msg
}
if ($rejected) { Write-Host "Se usa en su lugar: $Python" -ForegroundColor DarkYellow }

# --- Localizar los servicios dentro del submódulo ----------------------------
# Se buscan por su contenido para no depender de los nombres de carpeta del submódulo.
if (-not (Test-Path (Join-Path $SystemRoot '*'))) {
    Fail "El submódulo system\ está vacío. Ejecuta:`n       git submodule sync`n       git submodule update --init --recursive"
}
$SysDir = Get-ChildItem $SystemRoot -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName 'app\server.py') } | Select-Object -First 1
if (-not $SysDir) { Fail 'No se encuentra app\server.py dentro de system\.' }
$Children = Get-ChildItem $SysDir.FullName -Directory

$DbDir = $Children | Where-Object {
    (Test-Path (Join-Path $_.FullName 'cli.py')) -and (Test-Path (Join-Path $_.FullName 'var\catalog.sqlite'))
} | Select-Object -First 1
if (-not $DbDir) { Fail 'No se encuentra la base de datos (cli.py + var\catalog.sqlite).' }

$ViewDir = $Children | Where-Object {
    (Test-Path (Join-Path $_.FullName 'index.html')) -and (Test-Path (Join-Path $_.FullName 'vendor'))
} | Select-Object -First 1
if (-not $ViewDir) { Fail 'No se encuentra Sky View (index.html + vendor\).' }

$AnyfieldDir = $Children | Where-Object { $_.Name -eq 'anyfield' -and (Test-Path (Join-Path $_.FullName 'server.py')) } |
    Select-Object -First 1
$CatalogDb = Join-Path $DbDir.FullName 'var\star_catalog.sqlite'
$MainDb = Join-Path $DbDir.FullName 'var\catalog.sqlite'

# --- Servicios ----------------------------------------------------------------
$services = @(
    @{ Name = 'bd'; Label = 'Base de datos'; Port = 8797; Dir = $DbDir.FullName
       Args = @('cli.py', 'serve', '--port', '8797') }
    @{ Name = 'movescope'; Label = 'MoveScope'; Port = 8790; Dir = $SystemRoot
       Args = @((Join-Path $SysDir.FullName 'app\server.py'), '--port', '8790', '--host', '127.0.0.1') }
    @{ Name = 'skyview'; Label = 'Sky View'; Port = 8830; Dir = $ViewDir.FullName
       Args = @('-m', 'http.server', '8830', '--bind', '127.0.0.1') }
    @{ Name = 'entrada'; Label = 'Página de entrada'; Port = 8840; Dir = $Root
       Args = @('-m', 'http.server', '8840', '--bind', '127.0.0.1') }
)
$skipped = @()
if (-not $NoOptional) {
    if ($AnyfieldDir) {
        $sidecar = Join-Path $AnyfieldDir.FullName 'var\anyfield.sqlite'
        New-Item -ItemType Directory -Force (Split-Path $sidecar) | Out-Null
        $services += @{ Name = 'anyfield'; Label = 'AnyField C'; Port = 8798; Dir = $AnyfieldDir.FullName
            Args = @('server.py', '--host', '127.0.0.1', '--port', '8798', '--db', $MainDb,
                     '--sidecar', $sidecar, '--blob-root', (Join-Path $DbDir.FullName 'var\blobs')) }
    } else { $skipped += 'AnyField C (8798): no está en el submódulo' }
    if (Test-Path $CatalogDb) {
        $services += @{ Name = 'catalogo'; Label = 'Catálogo B'; Port = 8799; Dir = $DbDir.FullName
            Args = @('catalog_server.py', '--port', '8799', '--host', '127.0.0.1') }
    } else { $skipped += 'Catálogo B (8799): falta var\star_catalog.sqlite; la identificación en catálogo saldrá "no disponible"' }
}

function Test-PortBusy([int]$port) {
    [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

$busy = $services | Where-Object { Test-PortBusy $_.Port }
if ($busy) {
    $list = ($busy | ForEach-Object { "$($_.Label) ($($_.Port))" }) -join ', '
    Fail "Puertos ya en uso: $list.`n       Si es una ejecución anterior de HuellaX, páralo primero con .\stop.cmd"
}

New-Item -ItemType Directory -Force $StateDir | Out-Null
# Salida en UTF-8: el submódulo imprime texto no ASCII y la consola de Windows fallaría al redirigirlo.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'

Write-Host "Python: $Python"
$pids = @{}
foreach ($s in $services) {
    $log = Join-Path $StateDir "$($s.Name).log"
    $quoted = $s.Args | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }
    $p = Start-Process -FilePath $Python -ArgumentList $quoted -WorkingDirectory $s.Dir `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" -WindowStyle Hidden -PassThru
    $pids[$s.Name] = $p.Id
    Write-Host ("Arrancando {0,-18} puerto {1}  (PID {2})" -f $s.Label, $s.Port, $p.Id)
}
$pids | ConvertTo-Json | Set-Content -Encoding UTF8 $PidFile

# --- Comprobar que responden ---------------------------------------------------
function Test-Http([int]$port) {
    try {
        Invoke-WebRequest "http://127.0.0.1:$port/" -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        # Cualquier respuesta HTTP (404, 503...) significa que el servidor está escuchando.
        return [bool]$_.Exception.Response
    }
}

$failed = @()
foreach ($s in $services) {
    $ok = $false
    for ($i = 0; $i -lt 60 -and -not $ok; $i++) {
        $ok = Test-Http $s.Port
        if (-not $ok) {
            if (-not (Get-Process -Id $pids[$s.Name] -ErrorAction SilentlyContinue)) { break }  # ya murió
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $ok) { $failed += $s }
}

if ($failed) {
    foreach ($s in $failed) {
        Write-Host "ERROR: $($s.Label) no responde en el puerto $($s.Port)." -ForegroundColor Red
        $err = Join-Path $StateDir "$($s.Name).log.err"
        if (Test-Path $err) { Get-Content $err -Tail 8 -Encoding UTF8 | ForEach-Object { Write-Host "       $_" } }
    }
    Write-Host 'Parando lo que se haya arrancado...'
    & (Join-Path $Root 'stop.ps1')
    exit 1
}

Write-Host ''
Write-Host 'HuellaX en marcha:' -ForegroundColor Green
Write-Host '  Página de entrada:  http://127.0.0.1:8840/'
Write-Host '  Sky View:           http://127.0.0.1:8830/'
Write-Host '  MoveScope:          http://127.0.0.1:8790/'
foreach ($s in $services | Where-Object { $_.Port -in 8798, 8799 }) {
    Write-Host ("  {0,-19} http://127.0.0.1:{1}/" -f ($s.Label + ':'), $s.Port)
}
foreach ($m in $skipped) { Write-Host "  (sin arrancar) $m" -ForegroundColor DarkYellow }
Write-Host "  Registros:          $StateDir"
Write-Host ''
Write-Host 'Para pararlo: .\stop.cmd'

if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:8840/' }
