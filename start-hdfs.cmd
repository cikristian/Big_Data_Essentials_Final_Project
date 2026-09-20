@echo off
set "HADOOP_CONF_DIR=%~dp0infrastructure\hadoop-conf"

if not exist "C:\hadoop\bin\hdfs.cmd" (
    echo HDFS command not found at C:\hadoop\bin\hdfs.cmd
    exit /b 1
)

start "HDFS NameNode" cmd /k "set ""HADOOP_CONF_DIR=%HADOOP_CONF_DIR%"" && C:\hadoop\bin\hdfs.cmd namenode"
start "HDFS DataNode" cmd /k "set ""HADOOP_CONF_DIR=%HADOOP_CONF_DIR%"" && C:\hadoop\bin\hdfs.cmd datanode"

echo HDFS NameNode and DataNode windows started.
echo Verify with: C:\hadoop\bin\hdfs.cmd dfsadmin -report