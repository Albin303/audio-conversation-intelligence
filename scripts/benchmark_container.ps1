param(
    [Parameter(Mandatory=$true)][string]$ImageName,
    [Parameter(Mandatory=$true)][string]$ContainerName,
    [int]$DurationSeconds = 30,
    [int]$PollIntervalSeconds = 1,
    [int]$HealthTimeoutSeconds = 60
)

function Get-ContainerHealthStatus($name) {
    $inspect = docker inspect $name --format '{{json .State}}' 2>$null | ConvertFrom-Json
    if (-not $inspect) { return $null }
    if ($inspect.Health) { return $inspect.Health.Status }
    return $inspect.Status
}

$startTime = Get-Date
Write-Output "Starting container $ContainerName from image $ImageName"
docker rm -f $ContainerName 2>$null | Out-Null
$cid = docker run -d --name $ContainerName $ImageName
if (-not $cid) { Write-Error "Failed to start container"; exit 2 }

# Wait for container to be running
$running = $false
$waitStart = Get-Date
while (((Get-Date) - $waitStart).TotalSeconds -lt $HealthTimeoutSeconds) {
    $state = (docker inspect $ContainerName --format '{{.State.Status}}') -as [string]
    if ($state -eq 'running') { $running = $true; break }
    Start-Sleep -Seconds 1
}

if (-not $running) { Write-Error "Container did not enter running state within timeout"; docker logs $ContainerName; exit 3 }

# If container has healthcheck, wait for healthy
$healthStart = Get-Date
$healthy = $false
$hasHealth = (docker inspect $ContainerName --format '{{.State.Health}}') -ne "<no value>"
if ($hasHealth) {
    while (((Get-Date) - $healthStart).TotalSeconds -lt $HealthTimeoutSeconds) {
        $h = Get-ContainerHealthStatus $ContainerName
        if ($h -eq 'healthy') { $healthy = $true; break }
        if ($h -eq 'unhealthy') { break }
        Start-Sleep -Seconds 1
    }
} else {
    # no healthcheck; consider running state as healthy for timing purposes
    $healthy = $true
}

$startupTimeSec = (Get-Date -Date (Get-Date)) - $startTime
# record the time when healthy or running
$readyTime = if ($healthy) { (Get-Date) } else { (Get-Date) }
$startupElapsed = ($readyTime - $startTime).TotalSeconds

Write-Output "Container started. Sampling resources for $DurationSeconds seconds..."

$cpuMax = 0.0
$memMaxBytes = 0

for ($i=0; $i -lt $DurationSeconds; $i++) {
    $stat = docker stats --no-stream --format '{{.CPUPerc}}|{{.MemUsage}}' $ContainerName 2>$null
    if ($stat) {
        $parts = $stat -split '\|'
        $cpuStr = $parts[0].TrimEnd('%')
        [double]$cpuVal = 0
        if ([double]::TryParse($cpuStr, [ref]$cpuVal)) { if ($cpuVal -gt $cpuMax) { $cpuMax = $cpuVal } }
        $memStr = $parts[1]
        # memStr like '12.34MiB / 1.944GiB'
        $memUsed = $memStr -split '/' | Select-Object -First 1
        $memUsed = $memUsed.Trim()
        function Convert-MemToBytes($s) {
            if ($s -match '([0-9\.]+)\s*(KiB|MiB|GiB|B)') {
                $v = [double]$matches[1]
                switch ($matches[2]) {
                    'B' { return [int64]$v }
                    'KiB' { return [int64]($v * 1024) }
                    'MiB' { return [int64]($v * 1024 * 1024) }
                    'GiB' { return [int64]($v * 1024 * 1024 * 1024) }
                }
            }
            return 0
        }
        $bytes = Convert-MemToBytes $memUsed
        if ($bytes -gt $memMaxBytes) { $memMaxBytes = $bytes }
    }
    Start-Sleep -Seconds $PollIntervalSeconds
}

# collect final logs
$logs = docker logs --tail 200 $ContainerName 2>$null

$result = [PSCustomObject]@{
    Image = $ImageName
    Container = $ContainerName
    StartupSeconds = [math]::Round($startupElapsed,3)
    Healthy = $healthy
    CpuMaxPercent = [math]::Round($cpuMax,3)
    MemMaxBytes = $memMaxBytes
    Logs = $logs
}

$json = $result | ConvertTo-Json -Depth 4
Write-Output $json

docker rm -f $ContainerName | Out-Null

return 0
