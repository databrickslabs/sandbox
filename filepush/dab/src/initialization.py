import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--catalog_name", type=str, required=True)
parser.add_argument("--schema_name", type=str, required=True)
args = parser.parse_args()

print(f"Catalog: {args.catalog_name}")
print(f"Schema: {args.schema_name}")