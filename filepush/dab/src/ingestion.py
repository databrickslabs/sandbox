import dlt
from utils import tablemanager
from utils import formatmanager

def _make_append_flow(table_name, table_config, table_volume_path):
  def _body():
    reader = tablemanager.apply_table_config(spark.readStream, table_config)
    # use _rescued_data as placeholder when no data file is present
    if not tablemanager.has_data_file(table_name):
      reader = reader.schema("_rescued_data STRING")
    return reader.load(table_volume_path)

  # give the function a unique name (nice for logs / debug)
  _body.__name__ = f"append_{table_name.lower()}"

  # apply the decorator programmatically
  return dlt.append_flow(target=table_name, name=table_name)(_body)

table_configs = tablemanager.get_configs()

for cfg in table_configs:
  tablemanager.validate_config(cfg)
  tbl = cfg["name"]
  path = tablemanager.get_table_volume_path(tbl)
  expts = formatmanager.get_format_manager(cfg["format"]).expectations

  dlt.create_streaming_table(
    name=tbl,
    comment="File push created table",
    table_properties={"filepush.table_volume_path_data": path},
  )
  dlt.expect_all(expts)
  _make_append_flow(tbl, cfg, path)
