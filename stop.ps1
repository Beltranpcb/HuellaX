# Para los servicios de HuellaX arrancados con start.ps1 (Windows; equivalente a ./stop.sh).
#
# Uso, desde la raíz del repositorio:
#   .\stop.cmd
#   powershell -ExecutionPolicy Bypass -File .\stop.ps1 [-Force]
#
# Sin -Force solo para los procesos cuyos PID guardó start.ps1.
# Con -Force también para procesos de Python que sigan escuchando en los puertos de HuellaX
# (por ejemplo, si se arrancaron a mano o se perdió el archivo de PID).
[CmdletBinding()]
param([switch]$Force)

$StateDir = Join-Path $env:TEMP 'huellax'
$PidFile = Join-Path $StateDir 'pids.json'
$Ports = 8790, 8797, 8798, 8799, 8830, 8840

$stopped = 0
if (Test-Path $PidFile) {
    $pids = Get-Content $PidFile -Raw | ConvertFrom-Json
    foreach ($prop in $pids.PSObject.Properties) {
        $proc = Get-Process -Id $prop.Value -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -like 'python*') {
            Stop-Process -Id $prop.Value -Force -ErrorAction SilentlyContinue
            Write-Host ("Parado {0,-10} (PID {1})" -f $prop.Name, $prop.Value)
            $stopped++
        } else {
            Write-Host ("{0,-10} ya no estaba en marcha" -f $prop.Name)
        }
    }
    Remove-Item $PidFile -Force
} else {
    Write-Host 'No hay servicios registrados por start.ps1.'
}

# Lo que siga escuchando en los puertos de HuellaX
Start-Sleep -Milliseconds 300
$left = foreach ($port in $Ports) {
    foreach ($c in @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) { [pscustomobject]@{ Port = $port; Id = $proc.Id; Name = $proc.ProcessName } }
    }
}
if ($left) {
    if ($Force) {
        foreach ($l in $left | Where-Object { $_.Name -like 'python*' }) {
            Stop-Process -Id $l.Id -Force -ErrorAction SilentlyContinue
            Write-Host "Parado $($l.Name) en el puerto $($l.Port) (PID $($l.Id))"
            $stopped++
        }
        foreach ($l in $left | Where-Object { $_.Name -notlike 'python*' }) {
            Write-Host "No se para $($l.Name) en el puerto $($l.Port) (PID $($l.Id)): no es Python." -ForegroundColor DarkYellow
        }
    } else {
        Write-Host ''
        Write-Host 'Siguen ocupados estos puertos de HuellaX:' -ForegroundColor DarkYellow
        foreach ($l in $left) { Write-Host "  puerto $($l.Port): $($l.Name) (PID $($l.Id))" }
        Write-Host 'Si son de HuellaX, páralos con: .\stop.cmd -Force'
    }
}

if ($stopped -gt 0) { Write-Host 'HuellaX detenido.' -ForegroundColor Green }
