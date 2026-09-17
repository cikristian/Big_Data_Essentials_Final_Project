# Kafka on native Windows: local development setup

This project uses Apache Kafka **4.3.1** for local native-Windows development.
It includes Windows `.bat` administration tools and requires **JDK 17 or
newer** for its broker and Kafka Connect.

## 1. Install a JDK and confirm it

In an elevated PowerShell window:

```powershell
winget install EclipseAdoptium.Temurin.17.JDK
```

Close and reopen PowerShell, then confirm the active JDK is 17 or newer:

```powershell
java -version
```

If it still reports Java 8, update `JAVA_HOME` and put `%JAVA_HOME%\bin` before
the legacy Oracle Java entry on `PATH`, then reopen PowerShell.

## 2. Kafka installation

Kafka is expected at `C:\kafka_2.13-4.3.1`. If it is already there, skip this
step. Otherwise download and extract it:

```powershell
Invoke-WebRequest "https://downloads.apache.org/kafka/4.3.1/kafka_2.13-4.3.1.tgz" -OutFile C:\kafka_2.13-4.3.1.tgz
tar -xf C:\kafka_2.13-4.3.1.tgz -C C:\
```

## 3. Initialize and start a single-node KRaft broker

Run these from a new PowerShell terminal. The terminal remains occupied while
the broker is running; leave it open.

```powershell
Set-Location C:\kafka_2.13-4.3.1
$clusterId = .\bin\windows\kafka-storage.bat random-uuid
.\bin\windows\kafka-storage.bat format --standalone -t $clusterId -c .\config\server.properties
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

Formatting is a first-time operation. Do not repeat it after data exists, since
it resets the broker log directory.

## 4. Create and inspect the topic

In another PowerShell terminal, from the project root:

```powershell
.\infrastructure\create_kafka_topic.ps1 -KafkaHome C:\kafka_2.13-4.3.1
```

The topic has six partitions. That is enough to demonstrate a consumer group
with multiple consumer instances and a rebalance. Replication factor is one
only because this local setup has one broker; production would use three
brokers and a replication factor of three.

## 5. Start Django and publish test messages

```powershell
Set-Location "C:\Users\Christian\OneDrive\Desktop\AUCA_Masters\BigData_Essentials\Big_Data_Essentials_Final_Project"
.\.venv\Scripts\python.exe .\dashboard\manage.py runserver
```

In a separate terminal:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/trips/publish/ -ContentType "application/json" -Body '{"count": 10}'
```

The response reports the topic partition and offset acknowledged for every
message. Inspect the topic with:

```powershell
C:\kafka_2.13-4.3.1\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic kigali-trip-events --from-beginning --property print.key=true
```
