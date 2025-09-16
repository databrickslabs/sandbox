from pyspark.sql.streaming import DataStreamReader

def apply_table_config(reader: DataStreamReader, table_config: dict) -> DataStreamReader:
  fmt = table_config.get("format")
  assert fmt is not None, f"format is required for table {table_config.get('name')}"
  reader = reader.option("cloudFiles.format", fmt)

  # format-specific options
  fmt_opts = table_config.get("format_options", {})
  for k, v in fmt_opts.items():
    reader = reader.option(k, v)
  
  # schema hints
  schema_hints = table_config.get("schema_hints")
  if schema_hints:
    reader = reader.option("cloudFiles.schemaHints", schema_hints)

  return reader