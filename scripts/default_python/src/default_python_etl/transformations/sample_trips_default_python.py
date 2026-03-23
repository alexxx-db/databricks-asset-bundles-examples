from pyspark import pipelines as dp

# This file defines a sample transformation.
# Edit the sample below or add new transformations
# using "+ Add" in the file browser.


@dp.table
def sample_trips_default_python():
    return spark.read.table("samples.nyctaxi.trips")
