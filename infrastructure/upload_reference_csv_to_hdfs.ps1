param(
    [string]$HdfsPath = "/data/trips/reference",
    [string]$CsvPath = (Join-Path $PSScriptRoot "..\rwanda_public_transport_delays.csv")
)

$hdfs = "C:\hadoop\bin\hdfs.cmd"
$env:HADOOP_CONF_DIR = Join-Path $PSScriptRoot "hadoop-conf"
if (-not (Test-Path $hdfs)) { throw "HDFS command not found at $hdfs" }
if (-not (Test-Path $CsvPath)) { throw "CSV not found: $CsvPath" }

& $hdfs dfs -mkdir -p $HdfsPath
if ($LASTEXITCODE -ne 0) { throw "Could not create HDFS path $HdfsPath" }
& $hdfs dfs -put -f $CsvPath $HdfsPath
if ($LASTEXITCODE -ne 0) { throw "Could not upload the CSV to HDFS" }
& $hdfs dfs -ls $HdfsPath
