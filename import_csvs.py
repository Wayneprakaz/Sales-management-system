import pyodbc
import pandas as pd

# --- Database Connection ---
conn = pyodbc.connect(
    'DRIVER={SQL Server};SERVER=PRAKASH\\SQLEXPRESS;DATABASE=Sales_Management_System;Trusted_Connection=yes;'
)
cursor = conn.cursor()

def clean_value(val):
    if pd.isna(val) or str(val).strip() == "":
        return None
    return val

def import_csv_to_sql(table_name, csv_file, columns, key_column):
    df = pd.read_csv(csv_file)
    for _, row in df.iterrows():
        values = [clean_value(row[col]) for col in columns]

        # Check if record already exists
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {key_column} = ?", values[columns.index(key_column)])
        exists = cursor.fetchone()[0]

        if exists == 0:
            placeholders = ",".join("?" for _ in columns)
            sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
            cursor.execute(sql, values)

    conn.commit()
    print(f"Imported {len(df)} rows into {table_name} (duplicates skipped)")

# Import Branches
import_csv_to_sql("branches", "branches.csv", ["branch_id","branch_name","branch_admin_name"], "branch_id")

# Import Users
import_csv_to_sql("users", "users.csv", ["user_id","username","password","branch_id","role","email"], "user_id")

# Import Customer Sales
import_csv_to_sql("customer_sales", "customer_sales.csv",
    ["sale_id","branch_id","date","name","mobile_number","product_name","gross_sales","received_amount","status"], "sale_id")

# Import Payment Splits
import_csv_to_sql("payment_splits", "payment_splits.csv",
    ["payment_id","sale_id","payment_date","amount_paid","payment_method"], "payment_id")

conn.close()
print("All CSVs imported successfully!")
