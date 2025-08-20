from typing import Dict, List

import pandas as pd
import streamlit as st
import yaml

from entities.features import SelectableFeature
from services.caches import CachedUcData
from services.filters import FeatureFilters
from session_manager import SessionFeatures
from utils.code_gen import (
    generate_create_feature_spec_code,
    generate_create_training_set_code,
)
from databricks.sdk.errors import PermissionDenied

# Constants for dataframe columns
SELECTED_COLUMN = "Is Selected"
FEATURE_NAME = "Feature"
DESCRIPTION = "Description"
SCHEMA_COLUMN = "Schema Name"
TABLE_NAME = "Table Name"
PRIMARY_KEYS = "Primary Keys"
TIMESERIES_COLUMNS = "Timeseries Columns"

# Required scopes to use this app
REQUIRED_SCOPES = [
    "catalog.catalogs:read",
    "catalog.schemas:read",
    "catalog.tables:read",
]

SessionFeatures.initialize_state()


def create_features_dataframe(
    features: List[SelectableFeature], show_schema_column: bool = False
) -> pd.DataFrame:
    data = []
    for f in features:
        m_info = f.feature.get_materialized_info()
        # extract data in the required order
        row = (
            f.selected,
            f.feature.name,
            f.feature.description(),
            *((m_info.schema_name,) if show_schema_column else ()),
            m_info.table_name,
            ", ".join(m_info.primary_keys),
            ", ".join(m_info.timeseries_columns) if m_info.timeseries_columns else "",
        )
        data.append(tuple(row))
    non_editable_columns = (
        [FEATURE_NAME, DESCRIPTION]
        + ([SCHEMA_COLUMN] if show_schema_column else [])
        + [TABLE_NAME, PRIMARY_KEYS, TIMESERIES_COLUMNS]
    )
    columns = [SELECTED_COLUMN] + non_editable_columns
    return pd.DataFrame(data=data, columns=columns), non_editable_columns


filters = FeatureFilters()
uc_data = CachedUcData()

st.set_page_config(layout="wide")

try:
    # Reduce padding on the top of the page above the title.
    st.markdown(
        """
    <style>
        .block-container {
            padding-top: 1rem;
        }
        .stFormSubmitButton > button {
            min-width: auto;
            white-space: nowrap;
            width: 100%;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )
    st.title("Explore features from Unity Catalog")

    catalog_schema_choices, filter_selection = st.columns(
        [2, 3], gap="large", vertical_alignment="top"
    )
    with catalog_schema_choices:
        st.subheader("Select catalog and schema:")
        catalog_ui_col, schema_ui_col = st.columns(
            [1, 1], gap="large", vertical_alignment="top"
        )
        with catalog_ui_col:
            catalog = st.selectbox(
                label="Catalog", options=(uc_data.get_catalogs())
            )
        with schema_ui_col:
            # By default, search through all schemas in the catalog.
            # If a schema is selected, teh app will rerun and search only in that schema.
            schema = st.selectbox(
                label="Schema",
                options=uc_data.get_schemas(catalog),
                index=None,
                placeholder="All schemas",
            )
        with st.container():
            st.markdown("")
            search_msg = st.empty()
    with filter_selection:
        with st.expander("Filters"):
            st.subheader("Filter features:")
            with st.form("Filters", border=False):
                st.text_input(
                    label="by name",
                    key="name_filter",
                    placeholder="Enter partial feature name. For example: 'max' or '7_days'.",
                )
                st.text_input(
                    label="by table",
                    key="table_filter",
                    placeholder="Enter partial table name.",
                )
                st.text_input(
                    label="by description",
                    key="description_filter",
                    placeholder="Enter partial description",
                )
                b1, b2, _ = st.columns([0.18, 0.18, 0.64])
                b1.form_submit_button("Filter", type="primary")
                if b2.form_submit_button("Clear"):
                    filters.clear()

    # update session state with current selected catalog and schema names
    SessionFeatures.set_current_catalog(catalog)
    SessionFeatures.set_current_schema(schema)

    # Generate a list of features for the selected catalog and schema (or all schemas)
    # Save searched features
    all_features = []
    schemas = [schema] if schema else uc_data.get_schemas(catalog)
    for schema in schemas:
        # check if features for this schema are already saved
        features_list_by_table = SessionFeatures.get_saved_features(catalog, schema)
        if features_list_by_table is None:
            # fetch features for this catalog/schema
            tables_data = uc_data.get_tables(catalog, schema)
            feature_data = uc_data.get_features(tables_data)
            features_list_by_table = {
                table_name: [
                    SelectableFeature(feature=feature, selected=False)
                    for feature in features
                ]
                for table_name, features in feature_data.items()
            }
            SessionFeatures.update_saved_features(
                catalog, schema, features_list_by_table
            )
            num_features = sum(
                [len(features) for features in features_list_by_table.values()]
            )
            search_msg.markdown(
                f":hourglass_flowing_sand: Found **{num_features}** features in **`{catalog}.{schema}`**"
            )
        all_features += [
            feature
            for features in features_list_by_table.values()
            for feature in features
        ]
    search_msg.markdown(
        f":white_check_mark: Search complete! Found **{len(all_features)}** features in **`{catalog}`**"
    )

    DATA_EDITOR_UPDATES_KEY = "data_editor_updates"

    def change_state(ordered_feature_list):
        """This callback is called when user selects or unselects a feature."""

        # edits made by the user that triggered the callback
        edited = st.session_state[DATA_EDITOR_UPDATES_KEY]
        # create a change log of all updated feature selected by schema. Record their *new* selected/unselected state
        changes_by_schema: Dict[str, Dict[str, bool]] = {}
        for index, selection in edited.get("edited_rows", {}).items():
            # identify the feature that was changed using index from the ordered feature list
            if selection.get(SELECTED_COLUMN) is not None:
                feature = ordered_feature_list[index]
                schema = feature.feature.table.schema()
                if schema not in changes_by_schema:
                    changes_by_schema[schema] = {}
                changes_by_schema[schema][feature.feature.full_name()] = selection[
                    SELECTED_COLUMN
                ]

        # iterate through the changes and update the selected state
        for schema, changes in changes_by_schema.items():
            # fetch current state for this catalog and schema
            features_in_schema = SessionFeatures.get_saved_features(
                SessionFeatures.current_catalog(), schema
            )

            # create an updated list of features for each table in current schema
            updated_all_features = {
                table_name: [
                    SelectableFeature(
                        feature=f.feature,
                        selected=changes.get(f.feature.full_name(), f.selected),
                    )
                    for f in features
                ]
                for table_name, features in features_in_schema.items()
            }
            # update the session state
            SessionFeatures.update_saved_features(
                SessionFeatures.current_catalog(), schema, updated_all_features
            )

    # Filter the features in this catalog/schema based on selected filters
    if filters.enabled():
        ordered_feature_list = []
        total_features, matching_features = 0, 0
        for feature in all_features:
            total_features += 1
            if filters.include(feature.feature):
                matching_features += 1
                ordered_feature_list.append(feature)
        search_msg.markdown(
            f":white_check_mark: Search complete! "
            f"Found {matching_features} of {total_features} features matching filters."
        )
    else:
        ordered_feature_list = all_features

    # show column for schema name only if no schema was selected from dropdown
    show_schema_column = SessionFeatures.current_schema() is None
    features_df, non_editable_column_names = create_features_dataframe(
        ordered_feature_list, show_schema_column
    )

    # use a data editor to allow user to select features. User can only select not change any other values.
    st.data_editor(
        features_df,
        disabled=non_editable_column_names,
        column_config={
            SELECTED_COLUMN: st.column_config.CheckboxColumn(
                label="Selected Features", width="small"
            )
        },
        use_container_width=True,
        hide_index=True,
        key=DATA_EDITOR_UPDATES_KEY,
        on_change=change_state,
        args=(ordered_feature_list,),
    )

    # show selected features
    if SessionFeatures.total_selected_features():
        (
            create_training_set_tab,
            create_feature_spec_tab,
            selected_features_tab,
        ) = st.tabs(
            [
                "Create Training Set",
                "Create Feature Spec",
                "Selected Features",
            ]
        )

        # Show code gen for create training set
        with create_training_set_tab:
            st.markdown(
                "Copy the code below to your notebook to create a training set with selected features."
            )
            code = generate_create_training_set_code(
                SessionFeatures.get_all_selected_features_by_table()
            )
            st.code(code, language="python")

        # Show code gen for feature spec
        with create_feature_spec_tab:
            st.markdown(
                "Copy the code below to your notebook to create a feature spec with selected features."
            )
            code = generate_create_feature_spec_code(
                SessionFeatures.get_all_selected_features_by_table()
            )
            st.code(code, language="python")

        # Create an expander to show selected features. Automatically expand if there are selected features.
        with selected_features_tab:
            curr_catalog_col, other_catalog_col = st.columns(
                [1, 1], gap="large", vertical_alignment="top"
            )
            selected = SessionFeatures.all_selected_features()
            with curr_catalog_col:
                # Show selected features for the current catalog
                st.markdown(f"Current catalog `{SessionFeatures.current_catalog()}`")
                features_by_table_by_schema = selected.get(
                    SessionFeatures.current_catalog(), {}
                )
                if any(
                    [
                        f
                        for s_data in features_by_table_by_schema.values()
                        for features in s_data.values()
                        for f in features
                    ]
                ):
                    formatted_features = yaml.dump(
                        dict(features_by_table_by_schema), sort_keys=False
                    )
                    st.code(formatted_features, language="yaml")
            with other_catalog_col:
                # Show selected features for other catalogs
                st.markdown(f"Other selected features")
                if SessionFeatures.current_catalog() in selected:
                    # exclude current catalog
                    del selected[SessionFeatures.current_catalog()]
                if any(
                    [
                        f
                        for c_data in selected.values()
                        for s_data in c_data.values()
                        for features in s_data.values()
                        for f in features
                    ]
                ):
                    formatted_features = yaml.dump(selected, sort_keys=False)
                    st.code(formatted_features, language="yaml")

except PermissionDenied as e:
    st.error(f"Permission Denied: The following scopes are required to use this app: {', '.join([f'`{s}`' for s in REQUIRED_SCOPES])}", icon="🚫")
except Exception as e:
    st.error(f"An error occurred: {e}")
    st.exception(e)
