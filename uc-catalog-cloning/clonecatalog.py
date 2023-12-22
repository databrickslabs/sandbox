from py4j.protocol import Py4JError
from typing import Dict, Optional, List
import re
import logging

# Set up logger to capture logs and store them in a file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler = logging.FileHandler(filename="logs.log", mode="w")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Attempt to retrieve the Databricks environment's API URL
# This block checks whether the code is running inside a Databricks notebook.
try:
    dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiUrl().get()
except Exception as e:
    logger.info(e)
    try:
        from databricks.connect import DatabricksSession

        spark = DatabricksSession.builder.getOrCreate()
    except ImportError as ie:
        logger.info(ie)
        raise ImportError(
            "Could not import databricks-connect, please install with `pip install databricks-connect==13.3.3`."
        ) from ie
    except ValueError as ve:
        logger.info(ve)
        raise ImportError(
            "Please re-install databricks-connect with `pip install databricks-connect==13.3.3`.\n"
            "and databricks-sdk with `pip install databricks-sdk==0.14.0`.\n"
            "If you are running from Databricks you also need to restart Python by running `dbutils.library.restartPython()`."
        ) from ve

# Import necessary Databricks SDK modules
# If unavailable, prompt the user to install or upgrade them
try:
    from databricks.sdk.core import DatabricksError
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service import catalog
except ImportError as e:
    logger.info(e)
    raise ImportError(
        "Could not import databricks-sdk, please install with `pip install databricks-sdk==0.14.0`.\n"
        "If you are running from Databricks you also need to restart Python by running `dbutils.library.restartPython()`."
    ) from e

# Import other necessary modules and handle potential import errors
try:
    from pyspark.sql.utils import AnalysisException
    from pyspark.errors.exceptions.connect import SparkConnectGrpcException
except ImportError as e:
    logger.info(e)
    raise ImportError(
        "Could not import pyspark, please install with `pip install pyspark`."
    ) from e
try:
    from termcolor import cprint
except ImportError as e:
    logger.info(e)
    raise ImportError(
        "Could not import termcolor, please install with `pip install termcolor`."
    ) from e


# Define the CloneCatalog class
class CloneCatalog:
    """
    This class facilitates the cloning of external storages and catalogs and the data assets between catalogs, including the associated permissions, comments, and tags.
    It creates new data assets if they do not already exist in the target catalog, and if they exist it only transfers the associated permissions, comments, and tags.
    """

    def __init__(
        self,
        source_catalog_external_location_name: str,
        source_catalog_name: str,
        target_catalog_external_location_pre_req: List,
        target_catalog_name: str,
        schemas_locations_dict: Optional[Dict[str, List]],
    ) -> None:
        """
        Initializes the CloneCatalog class.

        Parameters:
        source_catalog_external_location_name (str): Name of the source external location.
        source_catalog_name (str): Name of the source catalog.
        target_catalog_external_location_pre_req (List): Pre-requisites for the new external location in the form of `[target_catalog_ext_loc_name, 'storage_credential_name', 'storage_location_url(ADLS, S3, GS)']`
        target_catalog_name (str): Name of the new target catalog.
        schemas_locations_dict (Dict[str, List]): Dictionary mapping schemas to locations in the form of a schema_name as a key and a list as the associated value in the form
        `[ext_loc_name, 'storage_credential_name', 'storage_location_url(ADLS, S3, GS)']`
        """
        try:
            self.w = WorkspaceClient()
        except ValueError as e:
            logger.info(e)
            raise ValueError(
                "Please reinstall databricks-sdk with `pip install databricks-sdk --upgrade`.\n"
                "If you are running from Databricks you also need to restart Python by running `dbutils.library.restartPython()`"
            ) from e

        self.source_ext_loc_name = source_catalog_external_location_name
        self.source_ctlg_name = source_catalog_name
        self.target_external_location_pre_req = target_catalog_external_location_pre_req
        (
            self.target_ext_loc_name,
            self.target_strg_cred_name,
            self.target_ext_loc_url,
        ) = self.target_external_location_pre_req
        self.target_ctlg_name = target_catalog_name
        self.db_dict = self._build_location_for_schemas(
            schemas_locations_dict or dict()
        )
        self.securable_dict = {
            catalog.SecurableType.EXTERNAL_LOCATION: [
                self.w.external_locations,
                "External location",
            ],
            catalog.SecurableType.CATALOG: [self.w.catalogs, "Catalog"],
            catalog.SecurableType.SCHEMA: [self.w.schemas, "Schema"],
            catalog.SecurableType.TABLE: [self.w.tables, "Table"],
        }

    def _print_to_console(
        self,
        message: str,
        end: str = "\n",
        indent_size: int = 1,
        indent_level: int = 0,
        color: str = None,
        on_color: str = None,
    ) -> None:
        """
        Prints a message to the console.

        Parameters:
            message (str): Message to be printed.
            color (Optional[str]): Color of the printed message.
        """
        indent = " " * indent_size * indent_level
        cprint(indent + message.strip(), color=color, on_color=on_color, end=end)

    def _build_location_for_schemas(self, db_dict: Dict[str, List]) -> Dict[str, List]:
        """
        Creates or retrieves external locations for schemas.

        Parameters:
            db_dict (Dict[str, List])): dictionary of schema location requirements.

        Returns:
            Dict[str, List]: Dictionary mapping schemas to their external locations.
        """
        databricks_exception_hit = 0
        db_dict_out = {}
        if db_dict:
            self._print_to_console(
                "Creating external locations if they do not exist for the schemas based on the input dictionary.",
                color="cyan",
            )
        for db_name, (ext_loc_name, cred_name, url) in db_dict.items():
            try:
                db_external_location = self.w.external_locations.get(ext_loc_name)
                self._print_to_console(
                    f"External location {ext_loc_name} already exists and will be used for {db_name}.",
                    indent_level=3,
                )
            except DatabricksError as e:
                logger.info(e)
                self._print_to_console(
                    f"Creating External location {ext_loc_name} ...",
                    indent_level=3,
                    end=" ",
                )
                try:
                    db_external_location = self.w.external_locations.create(
                        name=ext_loc_name, credential_name=cred_name, url=url
                    )
                    self._print_to_console("DONE!", color="green")

                except AnalysisException as e:
                    logger.info(e)
                    self._print_to_console(str(e), color="red", on_color="on_yellow")
                except DatabricksError as de:
                    databricks_exception_hit = 1
                    logger.exception(de)
                    raise de
            finally:
                if not databricks_exception_hit:
                    db_dict_out[db_name] = db_external_location.url

        return db_dict_out

    def _clone_tags(
        self,
        securable_type_str: str,
        source_catalog_name: str,
        target_securable_full_name: str,
    ) -> bool:
        """
        Clones tags for a securable type.

        Parameters:
            securable_type_str (str): The type of the securable to clone tags for.

        Returns:
            bool: True if cloning was successful, False otherwise.
        """
        _, schema, table = (*target_securable_full_name.split("."), None, None)[:3]
        schema_clause = f"\tAND schema_name = '{schema}'" if schema else ""
        table_clause = f"\tAND table_name = '{table}'" if table else ""
        query = (
            f"""
            SELECT * FROM 
            system.information_schema.{securable_type_str.lower()}_tags 
            WHERE catalog_name = '{source_catalog_name}'
            """
            + schema_clause
            + table_clause
        )
        try:
            securable_tag_list = spark.sql(query).collect()

            for row in securable_tag_list:
                if securable_type_str.lower() == "column":
                    spark.sql(
                        f"""
                  ALTER TABLE {target_securable_full_name}
                  ALTER COLUMN {row.column_name}
                  SET TAGS ('{row.tag_name}' = '{row.tag_value}')
                  """
                    )
                else:
                    spark.sql(
                        f"""
                  ALTER {securable_type_str} {target_securable_full_name}
                  SET TAGS ('{row.tag_name}' = '{row.tag_value}')
                  """
                    )

        except DatabricksError as e:
            logger.info(e)
            self._print_to_console(str(e), color="red", on_color="on_yellow")

    def _parse_transfer_permissions(
        self,
        securable_type: catalog.SecurableType,
        source_securable_full_name: str,
        target_securable_full_name: str,
    ) -> bool:
        """
        Transfers permissions between securable objects.

        Parameters:
            source_securable_full_name (str): The source securable object full name.
            target_securable_full_name (str): The new target securable object full name.

        Returns:
            bool: True if transfer was successful, False otherwise.
        """
        try:
            grants = self.w.grants.get(
                securable_type=securable_type, full_name=f"{source_securable_full_name}"
            )
            if grants.privilege_assignments == None:
                return True
            changes = [
                catalog.PermissionsChange(add=pair.privileges, principal=pair.principal)
                for pair in grants.privilege_assignments
            ]
            self.w.grants.update(
                full_name=target_securable_full_name,
                securable_type=securable_type,
                changes=changes,
            )
            return True
        except DatabricksError as e:
            logger.info(e)
            self._print_to_console(str(e), color="red", on_color="on_yellow")
            return False

    def _get_or_create_transfer(
        self,
        securable_type: catalog.SecurableType,
        source_securable_full_name: Optional[str],
        target_securable_full_name: str,
        print_indent_level: str = 0,
        **kwarg,
    ) -> None:
        """
        Retrieves or creates a securable object and transfers data, permissions, comments and tags.

        Parameters:
            securable_type (str): The type of securable object.
            source_securable_full_name (str): full name of the source securable object.
            target_securable_full_name (str): full name of the new target securable object.
        """
        target_securable = None
        analysis_exception_hit = 0
        databricks_exception_hit = 0
        source_securable = (
            self.securable_dict[securable_type][0].get(source_securable_full_name)
            if source_securable_full_name
            else None
        )
        target_securable_name = re.findall("[^.]+$", target_securable_full_name)[0]
        try:
            target_securable = self.securable_dict[securable_type][0].get(
                target_securable_full_name
            )
            self._print_to_console(
                f"{self.securable_dict[securable_type][1]} {target_securable_name} already exists. Only transferring permissions, comments and tags ...",
                indent_level=print_indent_level,
                end=" ",
            )
        except DatabricksError as e:
            logger.info(e)
            self._print_to_console(
                f"Creating {self.securable_dict[securable_type][1]} {target_securable_name} and transferring permissions, comments and tags ...",
                indent_level=print_indent_level,
                end=" ",
            )
            try:
                if securable_type == catalog.SecurableType.TABLE:
                    spark.sql(
                        f"CREATE TABLE {target_securable_full_name} DEEP CLONE {source_securable_full_name}"
                    )
                    target_securable = self.securable_dict[securable_type][0].get(
                        full_name=target_securable_full_name
                    )

                else:
                    target_securable = self.securable_dict[securable_type][0].create(
                        name=target_securable_name, **kwarg
                    )
            except AnalysisException as ae:
                logger.exception(ae)
                analysis_exception_hit = 1
                self._print_to_console(str(ae), color="red", on_color="on_yellow")
            except DatabricksError as de:
                logger.exception(de)
                databricks_exception_hit = 1
                raise de
            except (Py4JError, SparkConnectGrpcException, Exception) as e:
                logger.exception(e)
                databricks_exception_hit = 1
                self._print_to_console(
                    "Tables with row level security or column level masking are not supported!",
                    color="red",
                    on_color="on_yellow",
                )
        finally:
            if not (analysis_exception_hit or databricks_exception_hit):
                # clone the securable's granted permissions
                if source_securable_full_name:
                    _ = self._parse_transfer_permissions(
                        securable_type=securable_type,
                        source_securable_full_name=source_securable_full_name,
                        target_securable_full_name=target_securable_full_name,
                    )
                # clone the securable's tags
                if securable_type != catalog.SecurableType.EXTERNAL_LOCATION:
                    _ = self._clone_tags(
                        self.securable_dict[securable_type][1],
                        self.source_ctlg_name,
                        target_securable_full_name,
                    )
                if securable_type == catalog.SecurableType.TABLE:
                    # clone the table columns' tags
                    _ = self._clone_tags(
                        "column", self.source_ctlg_name, target_securable_full_name
                    )

                    # clone the table's comment
                    spark.sql(
                        f'COMMENT ON TABLE {target_securable_full_name} IS "{source_securable.comment or ""}"'
                    )

                    # clone the table columns' comments
                    for col in source_securable.columns:
                        spark.sql(
                            f"""
                      ALTER TABLE {target_securable_full_name}
                      ALTER COLUMN {col.name}
                      COMMENT "{col.comment or ""}"
                      """
                        )

                else:
                    # clone the securable's comment
                    if target_securable_name.lower() != "information_schema":
                        comment = source_securable.comment if source_securable else None
                        self.securable_dict[securable_type][0].update(
                            target_securable_full_name,
                            comment=comment or "",
                        )

                self._print_to_console("DONE!", color="green")

        return target_securable

    def __call__(self):
        """
        Executes the cloning process.
        """
        self._print_to_console(
            "Creating data assets if they do not exist and clone permissions, comments and tags.",
            color="cyan",
        )
        self.target_external_location = self._get_or_create_transfer(
            catalog.SecurableType.EXTERNAL_LOCATION,
            self.source_ext_loc_name,
            self.target_ext_loc_name,
            print_indent_level=3,
            credential_name=self.target_strg_cred_name,
            url=self.target_ext_loc_url,
        )

        self.target_catalog = self._get_or_create_transfer(
            catalog.SecurableType.CATALOG,
            self.source_ctlg_name,
            self.target_ctlg_name,
            print_indent_level=6,
            storage_root=self.target_external_location.url,
        )

        db_list = self.w.schemas.list(self.source_ctlg_name)
        for db in db_list:
            self.target_db = self._get_or_create_transfer(
                catalog.SecurableType.SCHEMA,
                f"{self.source_ctlg_name}.{db.name}",
                f"{self.target_ctlg_name}.{db.name}",
                print_indent_level=9,
                catalog_name=self.target_catalog.name,
                storage_root=self.db_dict.get(db.name, None) or db.storage_root,
            )

            tbl_list = self.w.tables.list(
                catalog_name=self.source_ctlg_name, schema_name=db.name
            )
            for tbl in tbl_list:
                if tbl.table_type == catalog.TableType.MANAGED:
                    self.target_table = self._get_or_create_transfer(
                        catalog.SecurableType.TABLE,
                        f"{self.source_ctlg_name}.{db.name}.{tbl.name}",
                        f"{self.target_ctlg_name}.{db.name}.{tbl.name}",
                        print_indent_level=12,
                    )
