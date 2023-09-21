import sys
import json
import happybase
from pyspark.sql import SparkSession
from pyspark.sql import DataFrame
from pyspark.sql.functions import *
from functools import reduce

#spark-submit --packages org.apache.spark:spark-avro_2.13:3.4.1 mean.py 17 240297 "ProvaAlgoritmo" "{'hPacketId': 117,'hPacketFieldId':118, 'hPacketFieldType':'number'}"

# Creazione Sessione Spark
spark = SparkSession.builder\
    .appName('HYOT_Neural_Network_train') \
    .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
    .enableHiveSupport() \
    .getOrCreate()

# Project ID
projectId = sys.argv[1]

# Algorithm ID
algorithmId = sys.argv[2]

# HProjectAlgorithm name
hProjectAlgorithmName = sys.argv[3]

# JobConfig
config_job_replaced = sys.argv[4].replace("'", "\"")  
jobConfig = json.loads(config_job_replaced)

# Retrieve information from updated JSON
# Get HPacket ID
hPacketId  = jobConfig["hPacketId"]

# Get first HPacketField ID
hPacketFieldId = jobConfig['hPacketFieldId']

# Get first HPacketField type
hPacketFieldType = jobConfig['hPacketFieldType']
hPacketFieldType = "double" if hPacketFieldType == "number" else hPacketFieldType

# Same name of script
outputName = "mean"

# HDFS path
#path_file = f"hdfs://localhost:8020/data/HPacket/{hPacketId}/20*" 
path_file = "C:/Users/alessio.serra/Desktop/ACSoftware/HyperIoT/test_caricamento_su_hyperIot/train.avro"

# TO CORRECT
df_list =[]
temp = spark.read.format("avro").load(path_file)
temp = temp.select(explode(map_values(temp.fields)).alias("hPacketField")).filter(col("hPacketField.id") == hPacketFieldId)
df_list.append(temp)

# Create merged dataframe
df_complete = reduce(DataFrame.union, df_list)

# Shuffle dataframe
df_complete = df_complete.orderBy(rand())

# Explode column FIELDS
value = df_complete.select(
    ("hPacketField.value.member0"),
    ("hPacketField.value.member1"),
    ("hPacketField.value.member2"),
    ("hPacketField.value.member3"),
    ("hPacketField.value.member4"),
    ("hPacketField.value.member5"),
    ("hPacketField.value.member6")) 

# Mean
output = value.select(coalesce(value.member0.cast("string"), value.member1.cast("string"),
                               value.member2.cast("string"), value.member3.cast("string"),
                               value.member4.cast("string"), value.member5.cast("string"),
                               value.member6.cast("string")).alias('value')).select(col("value").cast("double")).select(mean(col("value")))


# Write in Hbase
connection = happybase.Connection(host="localhost", port=9090, protocol="compact")
connection.open()
table_name = "algorithm" + "_" + algorithmId
connection.create_table(table_name, ({'value': dict()}))
HbaseTable = connection.table(table_name)

for row in output.collect():
    keyValue = projectId + "_" + hProjectAlgorithmName + "_" + ''
    columnFamily = 'value'
    max = str(row[0])
    column = outputName

    HbaseTable.put(keyValue.encode("utf-8"), {columnFamily.encode("utf-8") +":".encode("utf-8")+ column.encode("utf-8"): max.encode("utf-8")})

# Close all connections
connection.close()
spark.stop()
