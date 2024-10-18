# Module for T-SQL Conversion Prompt
from typing import List, TypedDict


class FewShot(TypedDict):
    role: str
    content: str


class TsqlConversionPromptManager:
    def __init__(self, comment_lang: str):
        self.comment_lang = comment_lang

    def get_system_message(self) -> str:
        return _system_message.format(comment_lang=self.comment_lang)

    def get_few_shots(self) -> List[FewShot]:
        return [
            {"role": "user", "content": _example_1_user},
            {"role": "assistant", "content": _example_1_assistant},
        ]

# System message
_system_message = """
Convert T-SQL code to Python code that runs on Databricks according to the following instructions and guidelines:

# Input and Output
- Input: CREATE OR ALTER PROCEDURE statements (SQL Server syntax).
- Output: Python functions for Databricks notebooks with Python comments (in {comment_lang}) explaining the code and any necessary context.

# Instructions:
1. Convert the input T-SQL stored procedure into a Python function suitable for execution in a Databricks notebook.
2. Strictly adhere to the guidelines provided below.
3. The output should be Python code and Python comments only, and no other strings are allowed.
4. If you receive a message like "Please continue," simply continue the conversion from where you left off without adding any extra phrases.
5. DO NOT omit any part of the conversion. Instead, include any non-convertible parts as Python comments in the output code, along with explanations in {comment_lang} of the necessary changes or alternatives.
6. DO NOT need to output explanation string. Just output Python code and Python comments.

# Guidelines
1. Python-based:
    - Use Python as the primary programming language.
2. Databricks Environment:
    - DO NOT include the creation of Spark Sessions or imports of libraries like `from delta.tables import DeltaTable` as these are assumed to be available in the Databricks environment.
3. Spark SQL Execution:
    - Use `spark.sql()` to execute SQL statements.
    - Write SQL statements directly within `spark.sql()`.
    - DO NOT store SQL statements in variables unless absolutely necessary. If you must store SQL statements in variables, prefix the variable names with `qs_` for identification.
4. Delta Tables:
    - Assume all tables appearing in the T-SQL script without a CREATE statement are already defined as delta tables.
5. Comments:
    - Add Python comments in {comment_lang} as needed to explain the code's logic.
6. Transaction and Rollback Handling:
    - For T-SQL syntax related to transaction control (e.g., BEGIN TRANSACTION, COMMIT, ROLLBACK), implement equivalent logic in Python using try-except-finally blocks for error handling.
    - DO NOT use `BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK` in `spark.sql()`. They are not supported and will cause errors.
    - If table rollback is needed:
        - Fetch the latest update timestamp of the delta table from the first row of its HISTORY table.
        - Use `RESTORE TABLE TIMESTAMP AS OF` to revert the delta table to that specific timestamp.
7. Looping Constructs:
    - DO NOT use `collect()`, for/while loops, or `iterrows()` as they are inefficient for large datasets.
    - Use DataFrame operations instead of cursors.
    - Leverage Spark's built-in transformations and actions (e.g., `map`, `filter`, `reduce`, `groupBy`, `merge`) for distributed data processing.
    - Use JOINs for bulk updates instead of loops.
8. Handling Non-Compatible Syntax:
    - For T-SQL syntax that cannot be directly converted (e.g., CREATE NONCLUSTERED INDEX, EXEC, etc.), exclude it from the conversion and add a Python comment explaining why it was excluded and suggesting potential alternatives in Databricks, if available.
9. SQL Function Handling:
    - Convert queries to get the same result as T-SQL, considering SQL functions that perform differently (e.g., `concat` function handling NULL values and zero byte strings).
    - Example: In Databricks, `concat` does not ignore null values, so handle cases where null values are included.
10. Table and View Names:
    - Respect the original view names as much as possible, but remove `@`, `#`, and `$` as they are not supported by Spark SQL.
11. Converting T-SQL CREATE TEMP TABLE:
    - Use a Delta table instead of a T-SQL TEMP TABLE and delete it in the finally clause.
    - DO NOT convert T-SQL TEMP TABLE to Spark TEMP VIEW, as they are not equivalent.
12. Converting T-SQL DELETE with Alias:
    - Delta Lake does not support using table aliases in DELETE statements. Ensure that the full table name is used instead of an alias in DELETE statements.
13. Converting T-SQL DELETE with JOIN:
    - Delta Lake does not support JOINs directly in DELETE statements.
    - Use a temporary view or subquery to perform the JOIN, then reference the results in the DELETE statement.
14. Converting T-SQL UPDATE Statements:
    - DO NOT use `FROM` clauses in Spark SQL `UPDATE` statements as they are not supported.
    - Use `MERGE INTO` for `UPDATE` statements with `JOIN`. Use `UPDATE` for statements without `JOIN`.
    - If `MERGE INTO` is not suitable, use a temporary view or subquery for the `JOIN`, then perform the `UPDATE`.
15. Special Character Handling:
    - Use backticks `` to enclose table and column names that contain special characters or spaces.
    - Avoid using square brackets [] as they are not supported.
16. Data Type Conversion: Use the following mappings to convert data types when creating the CREATE TABLE statement:
    - `VARCHAR` -> `STRING`
    - `NVARCHAR` -> `STRING`
    - `TEXT` -> `STRING`
    - `NTEXT` -> `STRING`
    - `IMAGE` -> `BINARY`
    - `MONEY` -> `DECIMAL` or `DOUBLE`
    - `SMALLMONEY` -> `DECIMAL` or `DOUBLE`
    - `UNIQUEIDENTIFIER` -> `STRING`
    - `SQL_VARIANT` -> `STRING`
    - `GEOGRAPHY` -> `STRING`
    - `GEOMETRY` -> `STRING`
17. Converting OBJECT_NAME(@@PROCID):
    - Use the function name dynamically retrieved with `__name__`.
"""

# Example 1: Comprehensive Procedure with Error Handling, Rollback, Temporary Table, Object Name Handling, and Conditional SQL Statements
## Input
_example_1_user = """
CREATE OR ALTER PROCEDURE usp_ProcessOrdersWithTempTable
    @OrderID INT,
    @NewStatus NVARCHAR(50),
    @CustomerID INT = NULL,  -- Optional parameter
    @IsPriority BIT
AS
BEGIN
    BEGIN TRANSACTION VALIDATION;
    BEGIN TRY
        -- Create a temporary table
        CREATE TABLE #TempOrderDetails (
            OrderID INT,
            ProductID INT,
            Quantity INT
        );

        -- Insert data into the temporary table
        INSERT INTO #TempOrderDetails (OrderID, ProductID, Quantity)
        SELECT OrderID, ProductID, Quantity
        FROM OrderDetails
        WHERE OrderID = @OrderID;

        -- Conditional SQL statements based on priority
        DECLARE @SqlStatement NVARCHAR(MAX);
        IF @IsPriority = 1
        BEGIN
            SET @SqlStatement = N'
                UPDATE Orders
                SET OrderStatus = ''' + @NewStatus + '''
                WHERE OrderID = ' + CAST(@OrderID AS NVARCHAR) + ' AND IsPriority = 1';
        END
        ELSE
        BEGIN
            SET @SqlStatement = N'
                UPDATE Orders
                SET OrderStatus = ''' + @NewStatus + '''
                WHERE OrderID = ' + CAST(@OrderID AS NVARCHAR);
        END
        EXEC sp_executesql @SqlStatement;

        -- Optionally update customer's last order date
        IF @CustomerID IS NOT NULL
        BEGIN
            UPDATE Customers
            SET LastOrderDate = GETDATE()
            WHERE CustomerID = @CustomerID;
        END

        -- Join with the original table and perform calculations
        SELECT p.ProductName, SUM(t.Quantity * p.UnitPrice) AS TotalPrice
        FROM #TempOrderDetails t
        JOIN Products p ON t.ProductID = p.ProductID
        GROUP BY p.ProductName;

        -- Log the successful operation
        INSERT INTO AuditLogs (Event, OrderID) VALUES ('Order processed', @OrderID);

        -- Create an index on the temporary table
        CREATE NONCLUSTERED INDEX IX_TempOrderDetails_OrderID ON #TempOrderDetails (OrderID); 

        -- Loop through the temporary table and perform updates
        DECLARE @ProductID INT, @Quantity INT;
        DECLARE product_cursor CURSOR FOR
        SELECT ProductID, Quantity FROM #TempOrderDetails;
        OPEN product_cursor;
        FETCH NEXT FROM product_cursor INTO @ProductID, @Quantity;
        WHILE @@FETCH_STATUS = 0
        BEGIN
            UPDATE Products
            SET StockLevel = StockLevel - @Quantity
            WHERE ProductID = @ProductID;
            FETCH NEXT FROM product_cursor INTO @ProductID, @Quantity;
        END;
        CLOSE product_cursor;
        DEALLOCATE product_cursor;

        -- Function handling example
        SELECT CONCAT(column1, column2) FROM my_table;

        -- Special character handling example
        SELECT o.OrderID, o.OrderDate, c.CustomerName
        FROM [dbo].[Orders] AS o
        JOIN [dbo].[Customers] AS c ON o.CustomerID = c.CustomerID;

        -- Object name example
        SELECT env.KEY1
        FROM env
        WHERE env.KEY1 = OBJECT_NAME(@@PROCID);

        -- Delete example with alias
        DELETE tmp
        FROM #TempOrderDetails tmp
        LEFT JOIN OrderDetails od ON tmp.OrderID = od.OrderID
        WHERE od.OrderID IS NULL;

        -- Update using JOIN (converted to MERGE INTO)
        UPDATE Products p
        SET p.StockLevel = p.StockLevel - t.Quantity
        FROM Products p
        INNER JOIN #TempOrderDetails t ON p.ProductID = t.ProductID;

        COMMIT TRANSACTION VALIDATION;

        -- Drop the temporary table
        DROP TABLE #TempOrderDetails;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION VALIDATION;

        -- Drop the temporary table (if it exists)
        IF OBJECT_ID('tempdb..#TempOrderDetails') IS NOT NULL
            DROP TABLE #TempOrderDetails;

        -- Log the error
        INSERT INTO ErrorLogs (ErrorMessage) VALUES (ERROR_MESSAGE());

        -- Call a stored procedure to log the error (ignored)
        EXEC dbo.LOGGER_INS 'usp_ProcessOrdersWithTempTable', ERROR_MESSAGE();

        THROW; -- Re-throw the error
    END CATCH
END;
"""

## Output
_example_1_assistant = '''
def usp_process_orders_with_temp_table(order_id, new_status, customer_id, is_priority):
    # Since BEGIN TRANSACTION, COMMIT TRANSACTION, and ROLLBACK TRANSACTION are not supported in Databricks,
    # we will handle error processing using try-except blocks.
    latest_version_timestamp_orders = spark.sql("DESCRIBE HISTORY Orders LIMIT 1").collect()[0]['timestamp']
    latest_version_timestamp_customers = spark.sql("DESCRIBE HISTORY Customers LIMIT 1").collect()[0]['timestamp']
    latest_version_timestamp_products = spark.sql("DESCRIBE HISTORY Products LIMIT 1").collect()[0]['timestamp']
    try:
        spark.sql("""
            CREATE TABLE TempOrderDetails (
                OrderID INT,
                ProductID INT,
                Quantity INT
            )
        """)

        spark.sql(f"""
            INSERT INTO TempOrderDetails
            SELECT OrderID, ProductID, Quantity
            FROM OrderDetails
            WHERE OrderID = {order_id}
        """)

        # Conditional SQL statements based on priority
        # The string variable name of SQL statement starts from `qs_` for easy identification
        if is_priority:
            qs_sql_statement = f"""
                UPDATE Orders
                SET OrderStatus = '{new_status}'
                WHERE OrderID = {order_id} AND IsPriority = 1
            """
        else:
            qs_sql_statement = f"""
                UPDATE Orders
                SET OrderStatus = '{new_status}'
                WHERE OrderID = {order_id}
            """
        spark.sql(qs_sql_statement)

        if customer_id is not None:
            spark.sql(f"""
                UPDATE Customers
                SET LastOrderDate = CURRENT_TIMESTAMP()
                WHERE CustomerID = {customer_id}
            """)

        result = spark.sql("""
            SELECT p.ProductName, SUM(t.Quantity * p.UnitPrice) AS TotalPrice
            FROM TempOrderDetails t
            JOIN Products p ON t.ProductID = p.ProductID
            GROUP BY p.ProductName
        """)
        display(result)

        spark.sql(f"""
            INSERT INTO AuditLogs (Event, OrderID) VALUES ('Order processed', {order_id})
        """)

        # Convert the T-SQL DELETE with alias to Delta Lake DELETE
        spark.sql("""
            DELETE FROM TempOrderDetails
            WHERE OrderID IN (
                SELECT t.OrderID
                FROM TempOrderDetails t
                LEFT JOIN OrderDetails od ON t.OrderID = od.OrderID
                WHERE od.OrderID IS NULL
            )
        """)

        # CREATE NONCLUSTERED INDEX IX_TempOrderDetails_OrderID ON TempOrderDetails (OrderID); -- Not supported in Databricks

        # Looping through the temporary table and perform updates using DataFrame transformations
        temp_df = spark.sql("SELECT ProductID, Quantity FROM TempOrderDetails")
        temp_df.createOrReplaceTempView("temp_view")
        spark.sql("""
            MERGE INTO Products p
            USING temp_view t ON p.ProductID = t.ProductID
            WHEN MATCHED THEN
                UPDATE SET p.StockLevel = p.StockLevel - t.Quantity
        """)

        # Function handling example
        spark.sql("""
            SELECT CONCAT_WS('', COALESCE(column1, ''), COALESCE(column2, ''))
            FROM my_table
        """)

        # Special character handling example
        spark.sql("""
            SELECT o.OrderID, o.OrderDate, c.CustomerName
            FROM `dbo`.`Orders` AS o
            JOIN `dbo`.`Customers` AS c ON o.CustomerID = c.CustomerID
        """)

        # Object name example
        spark.sql(f"""
            SELECT env.KEY1
            FROM env
            WHERE env.KEY1 = '{usp_process_orders_with_temp_table.__name__}'
        """)

        # Convert T-SQL UPDATE with JOIN to Delta Lake MERGE INTO
        spark.sql("""
            MERGE INTO Products p
            USING TempOrderDetails t ON p.ProductID = t.ProductID
            WHEN MATCHED THEN
                UPDATE SET p.StockLevel = p.StockLevel - t.Quantity
        """)

    except Exception as e:
        spark.sql(f"RESTORE TABLE Orders TO TIMESTAMP AS OF '{latest_version_timestamp_orders}'")
        spark.sql(f"RESTORE TABLE Customers TO TIMESTAMP AS OF '{latest_version_timestamp_customers}'")
        spark.sql(f"RESTORE TABLE Products TO TIMESTAMP AS OF '{latest_version_timestamp_products}'")
        spark.sql(f"INSERT INTO ErrorLogs (ErrorMessage) VALUES ('{str(e)}')")
        # EXEC dbo.LOGGER_INS 'usp_ProcessOrdersWithTempTable', ERROR_MESSAGE(); -- Not supported in Databricks
        raise e
    finally:
        spark.sql("DROP TABLE IF EXISTS TempOrderDetails")
'''