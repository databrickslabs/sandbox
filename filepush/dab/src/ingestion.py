import dlt
from utils import tablemanager

table_configs = tablemanager.get_configs()

for table_config in table_configs:
  tablemanager.validate_config(table_config)
  table_name = table_config['name']
  table_volume_path = tablemanager.get_table_volume_path(table_name)
  @dlt.table(
    name = table_name,
    comment = "File push created table",
    table_properties = {"filepush.table_volume_path_data": tablemanager.get_table_volume_path(table_name)}
  )
  def create_table():
      reader = spark.readStream.format("cloudFiles")
      reader = tablemanager.apply_table_config(reader, table_config)
      return reader.load(table_volume_path)