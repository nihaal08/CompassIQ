# CompassIQ Data Loss Explanation

## Why Tickets/Ratings Disappear

### Root Cause: Database Re-initialization

Data loss typically occurs when the database is re-initialized during development or application startup. This happens when:

1. **Schema.sql with DROP TABLE is executed**
   - The `schema.sql` file contains `DROP TABLE IF EXISTS` statements
   - Running this script wipes all existing data and recreates tables from scratch
   - This is common during development when schema changes are made

2. **Database file is deleted or overwritten**
   - The `compassiq.db` file is manually deleted
   - The database file path is changed
   - A new database is created in a different location

3. **init_db() runs with destructive operations**
   - The `init_db_schema()` function in `db.py` may be called with logic that drops tables
   - If the function detects missing tables or schema changes, it may re-run the entire schema

### How CompassIQ Prevents Data Loss

The current implementation in `db.py` includes safeguards:

```python
def init_db_schema(schema_path: str = None):
    # Checks if database file exists
    db_exists = Path(Config.DATABASE_PATH).exists()
    
    # Only creates new file if missing
    if not db_exists:
        # Create database file
    
    # Checks if users table exists
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM sqlite_master 
        WHERE type='table' AND name='users'
    """)
    table_exists = cursor.fetchone()['count'] > 0
    
    # Only executes schema.sql if tables don't exist
    if table_exists:
        print(f"[CompassIQ DB] Database schema already initialized. Ready.")
        return True  # Does NOT re-run schema.sql
```

### Current Safe Behavior

✅ **The application is configured to NOT overwrite existing data:**
- Database file is only created if missing
- Schema is only executed if tables don't exist
- `init_db_schema()` returns early if tables exist
- No `DROP TABLE` statements run on startup

### When Data Loss Would Occur

❌ **Data loss would occur if:**
- Manually running `schema.sql` directly with `sqlite3`
- Deleting the `compassiq.db` file
- Calling a function that explicitly drops tables
- Modifying `init_db_schema()` to force re-initialization

### Best Practices for Viva Demo

1. **Never manually delete the database file** during demo preparation
2. **Use the `seed_viva_data.py` script** to refresh data without destroying schema
3. **Backup the database** before making changes:
   ```bash
   cp database/storage/compassiq.db database/storage/compassiq.db.backup
   ```
4. **Test schema changes** in a separate development database first

### Seed Script Design

The `seed_viva_data.py` script is designed to:
- ✅ Wipe only ticket-related data (not schema)
- ✅ Preserve table structure
- ✅ Use `DELETE FROM` instead of `DROP TABLE`
- ✅ Re-populate with realistic viva demo data
- ✅ Maintain foreign key relationships

This ensures the database schema remains intact while providing fresh, realistic data for demonstration purposes.
