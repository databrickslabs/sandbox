import dlt
from utils import tablemanager

table_configs = tablemanager.get_configs()

for table_config in table_configs:
  tablemanager.validate_config(table_config)
  table_name = table_config['name']
  table_volume_path = tablemanager.get_table_volume_path(table_name)

  dlt.create_streaming_table(
    name = table_name,
    comment = "File push created table",
    table_properties = {"filepush.table_volume_path_data": tablemanager.get_table_volume_path(table_name)}
  )
  if not tablemanager.has_data_file(table_name) and not tablemanager.is_table_created(table_name):
    @dlt.append_flow(target = table_name)
    def noop_to_table():
      return tablemanager.get_placeholder_stream(spark.readStream)
  else:
    @dlt.append_flow(target = table_name)
    def append_to_table():
      reader = spark.readStream.format("cloudFiles")
      reader = tablemanager.apply_table_config(reader, table_config)
      return reader.load(table_volume_path)
