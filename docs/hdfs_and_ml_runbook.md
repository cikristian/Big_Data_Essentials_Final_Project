# HDFS ingestion and Spark MLlib training

HDFS is configured at `hdfs://localhost:9000`. The old system-wide NameNode
directory is locked by a different Windows account, so this project uses its
own clean NameNode and DataNode data directories under `infrastructure`.

From the project root, configure Hadoop to use the project-owned config and
format the new, empty filesystem **once**:

```powershell
$env:HADOOP_CONF_DIR = "$PWD\infrastructure\hadoop-conf"
C:\hadoop\bin\hdfs.cmd namenode -format
```

Open two additional PowerShell terminals, set `HADOOP_CONF_DIR` in each, and
run one daemon in each terminal:

```powershell
$env:HADOOP_CONF_DIR = "C:\Users\Christian\OneDrive\Desktop\AUCA_Masters\BigData_Essentials\Big_Data_Essentials_Final_Project\infrastructure\hadoop-conf"
C:\hadoop\bin\hdfs.cmd namenode
```

```powershell
$env:HADOOP_CONF_DIR = "C:\Users\Christian\OneDrive\Desktop\AUCA_Masters\BigData_Essentials\Big_Data_Essentials_Final_Project\infrastructure\hadoop-conf"
C:\hadoop\bin\hdfs.cmd datanode
```

In a third terminal with the same `HADOOP_CONF_DIR`, verify one live DataNode:

```powershell
C:\hadoop\bin\hdfs.cmd dfsadmin -report
```

The HDFS NameNode browser is `http://localhost:9870`.

Upload the CSV to the historical store:

```powershell
.\infrastructure\upload_reference_csv_to_hdfs.ps1
```

Train from HDFS—not the local CSV—with Spark MLlib:

```powershell
C:\Spark_set_up\spark-4.2.0\bin\spark-submit.cmd .\ml\training\train_delay_classifier.py
```

The job uses only features available at planning/dispatch time. It deliberately
excludes actual arrival/departure delay to prevent target leakage. It saves the
pipeline model in `/models/kigali_delay_classifier` and AUC, accuracy, F1, and
row counts in `/analytics/model_metrics`.

The dashboard predictions page reads the metrics from
`data/model_metrics.json`. Copy the resulting values into that file using the
fields `auc`, `accuracy`, `f1`, `training_rows`, and `test_rows`. The page
displays AUC, accuracy, and F1 as percentages. Alternatively, set
`MODEL_METRICS_JSON` to a local metrics JSON path before starting Django.
