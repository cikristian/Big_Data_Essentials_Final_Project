<#!
.SYNOPSIS
Creates and describes the project trip-event topic on a locally running broker.

.EXAMPLE
.\infrastructure\create_kafka_topic.ps1 -KafkaHome C:\kafka\kafka_2.13-3.9.1
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$KafkaHome,
    [string]$BootstrapServer = "localhost:9092",
    [int]$Partitions = 6
)

if (-not (Test-Path $KafkaHome -PathType Container)) {
    throw "KafkaHome does not exist: $KafkaHome. Extract Kafka first, then pass the directory containing bin\\windows\\kafka-topics.bat."
}

if ($Partitions -lt 2) {
    throw "Use at least two partitions so consumer rebalancing can be demonstrated."
}

$topicsCommand = Join-Path $KafkaHome "bin\windows\kafka-topics.bat"
if (-not (Test-Path $topicsCommand -PathType Leaf)) {
    throw "Kafka Windows topic tool not found: $topicsCommand"
}

& $topicsCommand --create --if-not-exists --topic kigali-trip-events `
    --bootstrap-server $BootstrapServer --partitions $Partitions --replication-factor 1
if ($LASTEXITCODE -ne 0) {
    throw "Kafka topic creation failed. Confirm the broker is running at $BootstrapServer."
}

& $topicsCommand --describe --topic kigali-trip-events --bootstrap-server $BootstrapServer
if ($LASTEXITCODE -ne 0) {
    throw "Kafka topic was created but could not be described."
}
