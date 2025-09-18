import dlt
from utils import tablemanager

table_configs = tablemanager.get_configs()

for table_config in table_configs:
  table_name = table_config['name']
  table_volume_path = tablemanager.get_table_volume_path(table_name)

  dlt.create_streaming_table(
    name = table_name,
    comment = "File push created table",
    table_properties = {"filepush.table_volume_path_data": table_volume_path}
  )
  @dlt.append_flow(
    target = table_name,
    name = table_name
  )
  def append_to_table():
    reader = spark.readStream.format("cloudFiles")
    reader = tablemanager.apply_table_config(reader, table_config)
    if not tablemanager.has_data_file(table_name):
      reader.schema("_rescued_data STRING") # Use _rescued_data as placeholder
    return reader.load(table_volume_path)
