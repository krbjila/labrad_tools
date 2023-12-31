import influxdb_client_3
import json
import pandas as pd

with open("C:\\Users\\Ye Lab\\Desktop\\labrad_tools\\log\\secrets.json", "r") as f:
    secrets = json.load(f)

token = secrets["INFLUXDB_TOKEN"]
url = secrets["INFLUXDB_URL"]

client = influxdb_client_3.InfluxDBClient3(
    token=token, host=url, org="krb", database="log"
)
queries = [
    'from(bucket: "log") |> range(start: -7d) |> filter(fn: (r) => r._measurement == "wavemeter" and r._field == "freq" and r.laser == "Rb Repump")',
    'from(bucket: "log") |> range(start: -7d) |> filter(fn: (r) => r._measurement == "bmp390" and r._field == "value" and r.sensor == "pressure")',
    'from(bucket: "log") |> range(start: -7d) |> filter(fn: (r) => r._measurement == "temperature" and r._field == "temp" and r.sensor == "x1B20 Room")',
    'from(bucket: "log") |> range(start: -7d) |> filter(fn: (r) => r._measurement == "temperature" and r._field == "humidity" and r.sensor == "x1B20 Room")',
]

dfs = []
for query in queries:
    result = client.query_api().query(query)
    dfs.append(pd.DataFrame(result))

df = pd.concat(dfs, axis=1)

df.to_csv("C:\\Users\\Ye Lab\\Desktop\\labrad_tools\\log\\data.csv")
