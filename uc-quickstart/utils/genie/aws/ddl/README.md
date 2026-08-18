# DDL Input Folder

Place your `CREATE TABLE` DDL files here (`.sql`). The `generate_abac.py` script reads all `.sql` files from this folder.

**Supports:**
- A single file with multiple `CREATE TABLE` statements
- One file per table (recommended for clarity)

**Example — using the healthcare sample DDLs:**

```bash
cp examples/healthcare/ddl/*.sql ddl/
python generate_abac.py --catalog my_catalog --schema my_schema
```
