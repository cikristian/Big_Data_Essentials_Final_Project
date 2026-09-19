# Kigali Public Transport Delay Analytics Platform

This project is a Big Data Essentials final project that simulates a live transport intelligence pipeline for Kigali public transport. It combines a Django dashboard, synthetic trip event generation, Kafka streaming, MySQL persistence, HDFS storage, and Spark ML training to model and monitor transport delays in near-real time.

The system is designed to show how a modern data pipeline can ingest stream events, store them in a warehouse, and expose operational metrics through a web dashboard. It is intentionally built for local Windows development and demonstrates the end-to-end flow of a small but realistic data engineering project.

## Overview

The platform produces trip events from the historical Rwanda public transport CSV dataset, publishes them to Kafka, stores them in MySQL, and exposes dashboard metrics for delay monitoring and risk estimation. A separate Spark ML training job reads the reference dataset from HDFS and trains a delay classifier, showing how big data processing fits into the same project ecosystem.

## Architecture

The repository is organized around a few connected components:

- Generator: creates synthetic trip events based on the seed CSV distribution.
- Producer: publishes trip events to Kafka with route-based keys.
- Dashboard: Django app serving the operational UI and APIs.
- MySQL: stores operational trip events for dashboard queries and replay.
- Kafka: transports live trip events across the platform.
- HDFS: stores the historical/reference dataset and model training output.
- Spark: trains a delay prediction model with MLlib.

A simplified flow looks like this:

```text
CSV seed data
    |
    v
Trip generator --> Kafka topic --> Dashboard / MySQL sink
                              |
                              v
                          HDFS + Spark ML
```

## Main Features

- Synthetic trip event generation from the Rwanda transport dataset
- Kafka topic publishing with route-based key partitioning
- Django REST endpoint for publishing events
- MySQL operational storage for dashboard queries
- Delay risk estimation in the dashboard layer
- HDFS upload and Spark MLlib training workflow
- Local Windows tooling for Hadoop, Kafka, and Spark setup

## Project Structure

```text
Big_Data_Essentials_Final_Project/
├── README.md
├── requirements.txt
├── rwanda_public_transport_delays.csv
├── dashboard/
│   ├── config/
│   ├── manage.py
│   └── operations/
├── generator/
│   ├── README.md
│   └── trip_generator.py
├── producer/
│   ├── README.md
│   └── kafka_publisher.py
├── ml/
│   ├── scoring/
│   └── training/
│       └── train_delay_classifier.py
├── infrastructure/
│   ├── create_kafka_topic.ps1
│   ├── upload_reference_csv_to_hdfs.ps1
│   ├── hadoop-conf/
│   └── hdfs-data/
├── docs/
│   ├── hdfs_and_ml_runbook.md
│   └── kafka_windows_setup.md
├── data/
├── consumer/
├── spark/
├── tests/
└── ...
```

## Tech Stack

- Python 3.11+
- Django 5.2
- Django REST Framework
- Kafka + confluent-kafka
- MySQL
- Apache Hadoop HDFS
- Apache Spark MLlib
- PowerShell automation for local services

## Prerequisites

Before running the project, make sure the following are available on your Windows machine:



### Replicate existing SQLite data to MySQL

If the dashboard previously generated records while Django was using SQLite,
copy them into MySQL with:

```powershell
.\.venv\Scripts\python.exe .\dashboard\manage.py replicate_sqlite_to_mysql
```

The command reads `dashboard/db.sqlite3`, copies records in batches, and can be
run again safely. Stop the dashboard while running it if you need an exact
point-in-time copy.

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure MySQL

The Django app expects a MySQL database named `Rwanda_Public_Transport` by default. You can change the credentials using environment variables:

```powershell
$env:MYSQL_DATABASE = "Rwanda_Public_Transport"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = ""
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
```

These variables must be present in the same PowerShell session that starts
Django. Alternatively, copy `.env.example` to `.env` and update the password;
the project loads that file automatically. You may need to create the database
manually before first use.

The dashboard now uses MySQL for all runtime reads and writes. Restart Django
after creating or changing `.env` so it loads the MySQL credentials.

### 4. Start Kafka

Follow the setup instructions in [docs/kafka_windows_setup.md](docs/kafka_windows_setup.md). This file includes the steps for installing Kafka, formatting the KRaft storage, and creating the topic used by the project.

### 5. Prepare HDFS and Spark

Use the runbook in [docs/hdfs_and_ml_runbook.md](docs/hdfs_and_ml_runbook.md) to configure local HDFS and train the delay classifier with Spark.

## Quick Start

### Start the Django dashboard

```powershell
Set-Location "C:\Users\Christian\OneDrive\Desktop\AUCA_Masters\BigData_Essentials\Big_Data_Essentials_Final_Project"
.\.venv\Scripts\python.exe .\dashboard\manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

### Publish sample trip events

In a separate PowerShell terminal:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/trips/publish/ -ContentType "application/json" -Body '{"count": 10}'
```

This generates trips from the CSV seed distribution, stores them in MySQL, and publishes them to the configured Kafka topic.

To generate events without Kafka and insert them directly into MySQL:

```powershell
.\.venv\Scripts\python.exe .\generator\trip_generator.py --rate 5 --count 10 --mysql
```

Run this in the same PowerShell session where the `MYSQL_*` variables from the
setup step are configured. The command rejects the SQLite fallback so records
cannot appear to succeed in the wrong database.

### Inspect the dashboard data

The main dashboard routes are:

- `/` — dashboard page
- `/api/dashboard-data/` — summary and event payloads
- `/api/preview-event/` — one generated preview event
- `/api/trips/publish/` — endpoint to publish trip events

## API Behavior

The producer endpoint accepts a JSON body with a `count` value from 1 to 1000:

```json
{"count": 25}
```

It performs the following actions:

- generates synthetic trip events
- persists them to the MySQL `transport_trip_events` table
- publishes each event to Kafka using `route_id` as the key
- returns the number of published messages and delivery metadata

## Data Model

The project uses a synthetic trip event schema modeled on real transport data, including fields such as:

- trip_id
- route_id
- transport_type
- origin/destination districts and stations
- coordinates
- schedule times and delays
- weather and traffic conditions
- holiday and peak-hour indicators
- delayed flag
- event_generated_at

## Generator

The generator is located in [generator/trip_generator.py](generator/trip_generator.py). It reads the CSV seed data and creates new trip records while preserving realistic correlations between route, weather, congestion, and delay patterns.

Example usage:

```powershell
.\.venv\Scripts\python.exe .\generator\trip_generator.py --rate 5 --count 10
.\.venv\Scripts\python.exe .\generator\trip_generator.py --rate 20 --count 100 --seed 42 --output .\data\sample_events.ndjson
```

## Kafka Producer

The Kafka publishing logic is in [producer/kafka_publisher.py](producer/kafka_publisher.py). The project uses keyed records with `route_id` so Kafka preserves per-route ordering while still allowing multiple routes to be processed in parallel.

## HDFS and ML Flow

The project includes a training workflow for Spark MLlib. The reference dataset is uploaded to HDFS and a delay classifier is trained from the historical trip data.

This flow is documented in:

- [docs/hdfs_and_ml_runbook.md](docs/hdfs_and_ml_runbook.md)
- [ml/training/train_delay_classifier.py](ml/training/train_delay_classifier.py)

## Documentation

The repo includes focused runbooks and setup notes:

- [docs/kafka_windows_setup.md](docs/kafka_windows_setup.md) — Kafka installation and setup on Windows
- [docs/hdfs_and_ml_runbook.md](docs/hdfs_and_ml_runbook.md) — HDFS and Spark ML pipeline
- [generator/README.md](generator/README.md) — generator behavior and usage
- [producer/README.md](producer/README.md) — Kafka producer endpoint details

## Notes

This project is a practical, local-development Big Data exercise. It is not intended to be a production-ready platform without additional hardening, monitoring, deployment automation, and security controls.

It is best used as a learning and demonstration project for:

- streaming architecture
- dashboard-backed analytics
- Kafka producer/consumer patterns
- HDFS + Spark data processing
- synthetic data generation and ML-based delay prediction

## License

This project is provided for educational and demonstration purposes within the Big Data Essentials course context.
