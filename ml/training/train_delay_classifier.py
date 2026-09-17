"""Train a Spark MLlib delay classifier from the project's HDFS trip data."""
import argparse
import json
import os
from pathlib import Path

from pyspark.ml import Pipeline
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml.feature import OneHotEncoder, StringIndexer, VectorAssembler
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

DEFAULT_INPUT = "hdfs://localhost:9000/data/trips/reference/rwanda_public_transport_delays.csv"
DEFAULT_MODEL = "hdfs://localhost:9000/models/kigali_delay_classifier"
DEFAULT_METRICS = "hdfs://localhost:9000/analytics/model_metrics"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CATEGORICAL = ["transport_type", "route_id", "origin_district", "destination_district", "weather_condition", "event_type", "season"]
NUMERIC = ["distance_km", "fare_rwf", "passengers_carried", "temperature_C", "humidity_percent", "wind_speed_kmh", "precipitation_mm", "event_attendance_est", "traffic_congestion_index", "holiday", "peak_hour", "weekday"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--model-output", default=DEFAULT_MODEL)
    parser.add_argument("--metrics-output", default=DEFAULT_METRICS)
    options = parser.parse_args()

    os.environ.setdefault("HADOOP_CONF_DIR", str(PROJECT_ROOT / "infrastructure" / "hadoop-conf"))
    spark = SparkSession.builder.appName("KigaliDelayClassifierTraining").getOrCreate()
    raw = spark.read.option("header", True).option("inferSchema", True).csv(options.input)
    data = raw.select(*CATEGORICAL, *NUMERIC, col("delayed").cast("double").alias("label")).dropna()
    if data.select("label").distinct().count() < 2:
        raise ValueError("Training data must contain both delayed=0 and delayed=1.")

    indexers = [StringIndexer(inputCol=name, outputCol=f"{name}_idx", handleInvalid="keep") for name in CATEGORICAL]
    encoder = OneHotEncoder(inputCols=[f"{name}_idx" for name in CATEGORICAL], outputCols=[f"{name}_vec" for name in CATEGORICAL])
    assembler = VectorAssembler(inputCols=NUMERIC + [f"{name}_vec" for name in CATEGORICAL], outputCol="features")
    classifier = RandomForestClassifier(labelCol="label", featuresCol="features", numTrees=100, maxDepth=10, seed=42)
    pipeline = Pipeline(stages=indexers + [encoder, assembler, classifier])
    train, test = data.randomSplit([0.8, 0.2], seed=42)
    model = pipeline.fit(train)
    predictions = model.transform(test)
    metrics = {
        "auc": BinaryClassificationEvaluator(labelCol="label", rawPredictionCol="rawPrediction").evaluate(predictions),
        "accuracy": MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy").evaluate(predictions),
        "f1": MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="f1").evaluate(predictions),
        "training_rows": train.count(), "test_rows": test.count(),
    }
    model.write().overwrite().save(options.model_output)
    spark.createDataFrame([(json.dumps(metrics),)], ["value"]).write.mode("overwrite").text(options.metrics_output)
    print(json.dumps(metrics, indent=2))
    spark.stop()


if __name__ == "__main__":
    main()
