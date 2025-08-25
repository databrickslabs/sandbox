from typing import Dict, List

import pandas as pd
import streamlit as st

from entities.features import SelectableFeature


class SessionFeatures:
    @staticmethod
    def initialize_state():
        if "catalog" not in st.session_state:
            st.session_state.catalog = None
        if "schema" not in st.session_state:
            st.session_state.schema = None
        if "features" not in st.session_state:
            # features: Dict[str, Dict[str, Dict[str, List[SelectableFeature]]]] = {}
            # catalog_name -> schema_name -> table name -> list of features
            st.session_state.features = {}

    @staticmethod
    def current_catalog() -> str:
        return st.session_state.catalog

    @staticmethod
    def set_current_catalog(catalog: str) -> None:
        st.session_state.catalog = catalog

    @staticmethod
    def current_schema() -> str:
        return st.session_state.schema

    @staticmethod
    def set_current_schema(schema: str) -> None:
        st.session_state.schema = schema

    @staticmethod
    def update_saved_features(
        catalog: str, schema: str, features: Dict[str, List[SelectableFeature]]
    ) -> None:
        # Updates the saved features by table name for the given catalog and schema.
        if catalog not in st.session_state.features:
            st.session_state.features[catalog] = {}
        st.session_state.features[catalog][schema] = features

    @staticmethod
    def get_saved_features(
        catalog: str, schema: str
    ) -> Dict[str, List[SelectableFeature]]:
        # Returns the saved features by table name for the given catalog and schema.
        if catalog not in st.session_state.features:
            return None
        if schema not in st.session_state.features[catalog]:
            return None
        return st.session_state.features[catalog][schema]

    @staticmethod
    def total_selected_features() -> int:
        selected_features = 0
        for catalog_to_data in st.session_state.features.values():
            for table_to_data in catalog_to_data.values():
                for features in table_to_data.values():
                    selected_features += len(
                        list(filter(lambda f: f.selected, features))
                    )
        return selected_features

    @staticmethod
    def all_selected_features() -> Dict[str, Dict[str, Dict[str, List[str]]]]:
        """
        Retrieve all selected features organized in a nested dictionary structure.

        The return value is a dictionary with the following hierarchy:
        - Catalog (str): The top-level key representing the catalog name.
          - Schema (str): A nested key representing the schema name within the catalog.
            - Table (str): A nested key representing the table name within the schema.
              - Feature Names (List[str]): A list of feature names (strings) that are selected.

        Example:
        {
            "catalog1": {
                "schema1": {
                    "table1": ["feature1", "feature2"],
                    "table2": ["feature3"]
                },
                "schema2": {
                    "table3": ["feature4"]
                }
            },
            "catalog2": {
                "schema3": {
                    "table4": ["feature5", "feature6"]
                }
            }
        }

        Returns:
            Dict[str, Dict[str, Dict[str, List[str]]]]: A nested dictionary of selected features.
        """
        selected_features = {}
        for catalog, catalog_to_data in st.session_state.features.items():
            for schema, schema_to_data in catalog_to_data.items():
                for table, features in schema_to_data.items():
                    for feature in features:
                        if feature.selected:
                            # only create hierarchy if any feature is selected
                            if catalog not in selected_features:
                                selected_features[catalog] = {}
                            if schema not in selected_features[catalog]:
                                selected_features[catalog][schema] = {}
                            if table not in selected_features[catalog][schema]:
                                selected_features[catalog][schema][table] = []
                            selected_features[catalog][schema][table].append(
                                feature.feature.name
                            )
        return selected_features

    @staticmethod
    def get_all_selected_features_by_table() -> Dict[str, List[SelectableFeature]]:
        """
        Retrieve all selected features grouped by table.

        The return value is a dictionary where the keys are table full names and the values are lists of selected features.
        """

        selected_features_by_table = {}
        for catalog, catalog_to_data in st.session_state.features.items():
            for schema, schema_to_data in catalog_to_data.items():
                for table, features in schema_to_data.items():
                    selected_features = [f for f in features if f.selected]
                    if selected_features:
                        full_table_name = f"{catalog}.{schema}.{table}"
                        selected_features_by_table[full_table_name] = selected_features
        return selected_features_by_table
