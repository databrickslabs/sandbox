# Databricks notebook source
# MAGIC %md This notebook contains code that allows to generate Plant UML schema from the Databricks database(s).  The generated file could be transformed into desired format by selecting necessary formats in "Generate image" dropdown, or by executing `%sh java -jar plantuml.jar -t<format> <file_name.puml>`. You can upgrade version of PlantUML by modifying `plantum_download_link` variable below.

# COMMAND ----------

plantum_download_link = "https://github.com/plantuml/plantuml/releases/download/v1.2022.2/plantuml-pdf-1.2022.2.jar"

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.utils import AnalysisException
from pyspark.sql.types import *
import sys
import requests
import os
import tempfile

# COMMAND ----------

# dbutils.widgets.removeAll()
dbutils.widgets.text("name_offset", "3", "Offset for names")
dbutils.widgets.text("pad_offset", "2", "Offset for padding")
dbutils.widgets.dropdown("include_temp", "No", ["Yes", "No"], "Include temp tables/views")
dbutils.widgets.multiselect("generate_image", "", ["", "PNG", "SVG", "PDF"], "Generate image")
dbutils.widgets.text("output_path", "/tmp/db_schema.puml", "Output path on DBFS")
dbutils.widgets.text("databases", "", "Databases to process (comma-separated, empty - all)")
#dbutils.widgets.text("", "", "")

# COMMAND ----------

name_offset = int(dbutils.widgets.get("name_offset"))
pad_offset = int(dbutils.widgets.get("pad_offset"))
include_temp = dbutils.widgets.get("include_temp").lower() == "yes"
enable_hive_support = False
generate_image = dbutils.widgets.get("generate_image").lower()
output_path = dbutils.widgets.get("output_path")
t = dbutils.widgets.get("databases")
if len(t.strip()) == 0:
    databases = [db[0] for db in spark.sql("show databases").collect()]
else:
    databases = [d.strip() for d in t.split(",")]
# dbutils.widgets.get("")

# COMMAND ----------

def is_struct_type(typ: object) -> bool:
    return isinstance(typ, dict) and typ['type'] == 'struct'


def maybe_get_field(obj: object, name: str, default: object) -> object:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default

# COMMAND ----------

def format_structfield(type_val: object, padding: int, isNullable: bool = False) -> str:
    if isinstance(type_val, str):
        type_string = type_val
    elif isinstance(type_val, dict):
        sub_type = type_val['type']
        if sub_type == 'array':
            type_string = "array< "
            element_type = type_val['elementType']
            is_struct = is_struct_type(element_type)
            if is_struct:
                type_string += "\n"
                padding += pad_offset
                type_string += (" " * padding)

            type_string += format_structfield(element_type, padding, type_val.get('containsNull', False))
            if is_struct:
                type_string += "\n"
                padding -= pad_offset
                type_string += (" " * (padding - pad_offset))

            type_string += " >"
        elif sub_type == 'map':
            # TODO: fix it - need to find the example of output
            type_string = "map< "
            element_type = type_val['keyType']
            is_struct = is_struct_type(element_type)
            if is_struct:
                type_string += "\n"
                type_string += (" " * padding)
                padding += pad_offset

            type_string += format_structfield(element_type, padding)
            if is_struct:
                padding -= pad_offset
            type_string += ", "

            element_type = type_val['valueType']
            is_struct = is_struct_type(element_type)
            if is_struct:
                type_string += "\n"
                type_string += (" " * padding)
                padding += pad_offset
            type_string += format_structfield(element_type, padding, type_val.get('valueContainsNull', False))
            if is_struct:
                type_string += "\n"
                padding -= pad_offset
                type_string += (" " * (padding - pad_offset))

            type_string += " >"
        elif sub_type == 'struct':
            pad_str = (" " * (padding + pad_offset))
            type_string = "struct<\n"
            for field in type_val['fields']:
                fname = field['name']
                type_string += pad_str + fname + " : "
                type_string += format_structfield(field['type'], padding + len(fname) + name_offset + pad_offset,
                                                  field.get('nullable', False))
                type_string += "\n"

            type_string += (" " * padding) + ">"
        else:
            raise Exception(f'Unknown subtype: {sub_type}')
    else:
        raise Exception(f'Unknown type: {type_val}')

    if isNullable:
        type_string += ' ?'
    return type_string

# COMMAND ----------

def format_type_name(col_name: str, typ: StructField, isNullable: bool = False,
                     isPartition: bool = False, isBucket: bool = False) -> str:
    current_pad = len(col_name) + name_offset
    jsn = typ.jsonValue()
    type_string = format_structfield(jsn['type'], current_pad, isNullable)
    if isPartition:
        type_string += " (pk)"
    if isBucket:
        type_string += " (bk)"
    return type_string.replace('\n', '\\n')

# COMMAND ----------

def generate_plantuml_schema(spark: SparkSession, databases: list, file_name: str):
    with open(file_name, "w") as f:
        f.write("\n".join(["@startuml", "skinparam packageStyle rectangle",
                           "hide circle", "hide empty methods",
                           "skinparam defaultFontName Courier", "", ""]))

        for database_name in databases[:3]:
            print(f"processing database {database_name}")
            f.write(f'package "{database_name}" {{\n')
            tables = spark.sql(f"show tables in `{database_name}`")
            # TODO: allow to pass additional mapping between table and partition keys in it that aren't defined explicitly
            partition_keys = {}
            columns_mapping = {}
            for tbl in tables.collect():
                table_name = tbl["tableName"]
                db = tbl["database"]
                # TODO: we can try to parallelize this by running in the thread pool
                if include_temp or not tbl["isTemporary"]:  # include only not temporary tables
                    lines = []
                    try:
                        tmp_txt = ""
                        if tbl["isTemporary"]:
                            tmp_txt = "(temp)"
                        lines.append(f'class {table_name} {tmp_txt} {{')
                        cols = spark.catalog.listColumns(table_name, dbName=db)
                        # TODO: find the column with the longest name, and use it as offset for all?
                        # Pad actual column name to that length
                        column_names = []
                        columns = []
                        for cl in cols:
                            col_name = cl.name
                            column_names.append(col_name)
                            schema = spark.createDataFrame([], cl.dataType).schema[0]
                            is_partition = cl.isPartition
                            if is_partition:
                                if col_name in partition_keys:
                                    partition_keys[col_name].add(table_name)
                                else:
                                    partition_keys[col_name] = {table_name}
                            type_string = format_type_name(col_name, schema, cl.nullable,
                                                           is_partition, cl.isBucket)
                            columns.append({'name': col_name, 'is_pk': is_partition, 'type': type_string})

                        columns.sort(key=lambda col: (not col['is_pk'], col['name'].lower()))
                        for col in columns:
                            lines.append(f'{{field}} {col["name"]} : {col["type"]}')

                        lines.append('}\n')
                        f.write("\n".join(lines))
                        columns_mapping[table_name] = column_names
                    except AnalysisException as ex:
                        print(f"Error when trying to describe {tbl.database}.{table_name}: {ex}")

            links = set()
            for table_name, columns in columns_mapping.items():
                for col in columns:
                    for pkey_table in partition_keys.get(col, []):
                        if table_name != pkey_table:
                            links.add(f'{table_name} *.. {pkey_table}: {col}\n')

            for link in links:
                f.write(link)

            f.write("}\n\n")

        f.write("@enduml\n")

# COMMAND ----------

fd, tmp_name = tempfile.mkstemp()
os.close(fd)
generate_plantuml_schema(spark, databases, tmp_name)
dbutils.fs.cp(f"file:{tmp_name}", output_path)

# COMMAND ----------

if generate_image != "":
    os.system("apt-get -f install -y graphviz")
    plantuml_path = "/tmp/plantuml.jar"
    if not os.path.exists(plantuml_path):
        r = requests.get(plantum_download_link)
        with open(plantuml_path , 'wb') as file:
            file.write(r.content)
    for image_type in generate_image.split(","):
        os.system(f"""java -jar /tmp/plantuml.jar -t{image_type} {tmp_name}""")
        dbutils.fs.cp(f"file:{tmp_name}.{image_type}", output_path + "." + image_type)
