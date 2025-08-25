from typing import Dict, List

import streamlit as st
import os
import yaml

from clients.uc_client import UcClient
from entities.features import Feature
from entities.tables import Table
from utils.auth import get_user_access_token

INTERNAL_SCHEMAS = {"information_schema"}


class CachedUcData:
    def __init__(self):
        # Reuse uc client
        if "uc_client" not in st.session_state:
            st.session_state.uc_client = UcClient(get_user_access_token())
        # Load and cache catalogs allowlist
        # the cache only contains names of allowlisted catalogs. In order to access data from the catalogs, the app will use the caller's read access tokens.
        if "catalogs_allowlist" not in st.session_state:
            st.session_state.catalogs_allowlist = self._load_catalogs_allowlist_from_env()

    @staticmethod
    def get_tables(catalog_name: str, schema_name: str) -> List[Table]:
        return [
            Table(uc_table=t)
            for t in st.session_state.uc_client.get_tables(
                catalog_name=catalog_name, schema_name=schema_name
            )
        ]

    @staticmethod
    def get_features(tables: List[Table]) -> Dict[str, List[Feature]]:
        """Returns a dictionary of features for each table"""
        features: Dict[str, List[Feature]] = {}
        for t in tables:
            tab = st.session_state.uc_client.get_table(full_name=t.full_name())
            if tab.table_constraints:
                for tc in tab.table_constraints:
                    if tc.primary_key_constraint:
                        all_pks = tc.primary_key_constraint.child_columns
                        ts = tc.primary_key_constraint.timeseries_columns or []
                        pks = [pk for pk in all_pks if pk not in ts]
                        these_features = [
                            Feature(name=c.name, table=t, pks=pks, ts=ts)
                            for c in tab.columns
                            if c.name not in all_pks
                        ]
                        features[t.name()] = these_features
                        break
        return features

    @staticmethod
    def get_catalogs() -> List[str]:
        catalogs_allowlist = st.session_state.get("catalogs_allowlist")
        # if allowlist is not empty, return the allowlisted catalogs
        if catalogs_allowlist:
            return catalogs_allowlist
        # else return all catalogs available to the user
        return [c.name for c in st.session_state.uc_client.get_catalogs()]

    @staticmethod
    def get_schemas(catalog_name: str) -> List[str]:
        # skip internal schemas
        return [
            s.name
            for s in st.session_state.uc_client.get_schemas(catalog_name=catalog_name)
            if s.name not in INTERNAL_SCHEMAS
        ]

    def _load_catalogs_allowlist_from_env(self) -> List[str]:
        env_path = os.getenv("UC_CATALOGS_ALLOWLIST")
        if env_path:
            try:
                with open(env_path) as f:
                    data = yaml.safe_load(f)
                if isinstance(data, list) and all(
                    isinstance(item, str) for item in data
                ):
                    return data
            except Exception:
                st.error(f"Error loading catalogs allowlist from {env_path}")
        return []
