# Databricks notebook source

df = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.schemaLocation", "/tmp/autoloader/_checkpoint/my_stream")
    .load("/Volumes/main/raw/incoming")
)
