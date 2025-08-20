from collections import defaultdict
from typing import Dict, List, Optional

from entities.features import SelectableFeature


def generate_create_training_set_code(
    features_by_table: Dict[str, List[SelectableFeature]]
) -> str:

    return f"""from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup

feature_lookups = [{_generate_feature_lookups_code(features_by_table)}
]

fe = FeatureEngineeringClient()

training_set = fe.create_training_set(
  df=training_df, # ⚠️ Make sure this is your labeled DataFrame!
  feature_lookups=feature_lookups,
  label='label' # 🏷️ Replace 'label' with your actual label column name
)
"""


def generate_create_feature_spec_code(
    features_by_table: Dict[str, List[SelectableFeature]]
) -> str:

    return f"""from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup
features = [{_generate_feature_lookups_code(features_by_table)}
]

fe = FeatureEngineeringClient()

# Create a `FeatureSpec` with the features defined above.
# The `FeatureSpec` can be accessed in Unity Catalog as a function.
# They can be used to create training sets or feature serving endpoints
fe.create_feature_spec(
  name="<catalog>.<schema>.<feature_spec_name>", # 📚 Replace with your actual catalog, schema, and feature spec name
  features=features,
)
"""


def _generate_feature_lookups_code(
    features_by_table: Dict[str, List[SelectableFeature]]
) -> str:

    primary_keys_by_table = {}
    timeseries_columns_by_table = {}
    features_names_by_table = defaultdict(list)

    # Group features by table
    for table_name, features in features_by_table.items():
        features_names_by_table[table_name] = [
            feature.feature.name for feature in features
        ]
        primary_keys_by_table[table_name] = features[0].feature.pks if features else []
        timeseries_columns_by_table[table_name] = (
            features[0].feature.ts if features and features[0].feature.ts else None
        )

    feature_lookup_codes = [
        _generate_feature_lookup_code(
            table_name,
            primary_keys_by_table[table_name],
            features_names_by_table[table_name],
            timeseries_columns_by_table[table_name],
        )
        for table_name in features_by_table
    ]
    return ",".join(feature_lookup_codes)


def _generate_feature_lookup_code(
    table_name: str,
    primary_keys: List[str],
    features_by_table: List[str],
    timeseries_columns: Optional[str] = None,
) -> str:
    return (
        f"""
    FeatureLookup(
        table_name="{table_name}",
        feature_names={features_by_table},
        lookup_keys={primary_keys}, # 🔑 Replace with your actual lookup keys if needed
    )"""
        if not timeseries_columns
        else f"""
    FeatureLookup(
        table_name="{table_name}",
        feature_names={features_by_table},
        lookup_keys={primary_keys}, # 🔑 Replace with your actual lookup keys if needed
        timeseries_columns='{timeseries_columns[0]}' # ⏱️ Replace with your actual timeseries columns if needed
    )"""
    )
