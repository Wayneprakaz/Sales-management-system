import streamlit as st
import pyodbc
import pandas as pd
import datetime

# --- Database Connection ---
def get_connection():
    return pyodbc.connect(
        'DRIVER={SQL Server};SERVER=PRAKASH\\SQLEXPRESS;DATABASE=Sales_Management_System;Trusted_Connection=yes;'
    )

def get_data(query, params=None):
    conn = get_connection()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# --- Streamlit Setup ---
st.set_page_config(page_title="Sales Dashboard", layout="wide")
st.title("Sales Intelligence Hub")

# --- Session State ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'branch_id' not in st.session_state:
    st.session_state['branch_id'] = None

def logout():
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.session_state['branch_id'] = None
    st.rerun()

# --- Login ---
if not st.session_state['logged_in']:
    st.subheader("Secure System Authentication")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    def validate_login(user, pwd):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, branch_id FROM users WHERE username=? AND password=?", (user, pwd))
        result = cursor.fetchone()
        conn.close()
        return result

    if st.button("Login", type="primary"):
        login_info = validate_login(username, password)
        if login_info:
            role, branch_id = login_info
            st.session_state['role'] = role
            st.session_state['branch_id'] = branch_id
            st.session_state['logged_in'] = True
            st.success(f"Welcome back, {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password.")
else:
    role = st.session_state['role']
    branch_id = st.session_state['branch_id']

    # Sidebar
    st.sidebar.markdown("### Active Profile")
    st.sidebar.info(f"**Role:** {role}")
    if st.sidebar.button("Log Out"):
        logout()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filters")

    default_start = datetime.date(2024, 1, 1)
    today = datetime.date.today()
    start_date = st.sidebar.date_input("Start Date", value=default_start)
    end_date = st.sidebar.date_input("End Date", value=today, max_value=today)

    if role == "Super Admin":
        branches_df = get_data("SELECT branch_id, branch_name FROM branches")
        branch_options = ["All"] + branches_df['branch_name'].tolist()
        selected_branch_name = st.sidebar.selectbox("Branch", branch_options)
        active_branch_id = None if selected_branch_name == "All" else int(branches_df.loc[branches_df['branch_name']==selected_branch_name,'branch_id'].values[0])
    else:
        branch_info = get_data("SELECT branch_name FROM branches WHERE branch_id = ?", [branch_id])
        assigned_branch_name = branch_info['branch_name'].iloc[0] if not branch_info.empty else "My Branch"
        st.sidebar.text_input("Branch", value=assigned_branch_name, disabled=True)
        active_branch_id = int(branch_id)

    product_options = ["All","DS","DA","BA","FSD","ML","AI","BI","SQL"]
    product_choice = st.sidebar.selectbox("Product", product_options)

    # --- Filters ---
    conditions = ["cs.date BETWEEN ? AND ?"]
    params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]
    if active_branch_id is not None:
        conditions.append("cs.branch_id = ?")
        params.append(active_branch_id)
    if product_choice != "All":
        conditions.append("cs.product_name = ?")
        params.append(product_choice)
    where_clause = " WHERE " + " AND ".join(conditions)

    # --- Main Query ---
    query = f"""
    SELECT cs.sale_id, b.branch_name, cs.date, cs.name, cs.mobile_number,
           cs.product_name, cs.gross_sales, cs.received_amount, cs.pending_amount, cs.status
    FROM customer_sales cs
    JOIN branches b ON cs.branch_id = b.branch_id
    {where_clause}
    ORDER BY cs.sale_id DESC
    """
    records_df = get_data(query, params)

    # KPIs
    st.subheader("KPIs")
    if not records_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Gross Sales", f"₹{records_df['gross_sales'].sum():,.2f}")
        col2.metric("Total Received", f"₹{records_df['received_amount'].sum():,.2f}")
        col3.metric("Total Pending", f"₹{records_df['pending_amount'].sum():,.2f}")
    else:
        st.warning("No records found for selected filters.")

    # Data Table
    st.markdown("---")
    st.write("### Transactions")
    if not records_df.empty:
        st.dataframe(records_df, use_container_width=True)

    # Add New Sale
    st.markdown("---")
    st.write("### Add New Customer Sale")
    with st.form("new_sale_form", clear_on_submit=True):
        if role == "Super Admin":
            branches_df = get_data("SELECT branch_id, branch_name FROM branches")
            form_branch_name = st.selectbox("Branch", branches_df['branch_name'].tolist())
            target_branch_id = int(branches_df.loc[branches_df['branch_name']==form_branch_name,'branch_id'].values[0])
        else:
            st.text_input("Branch", value=assigned_branch_name, disabled=True)
            target_branch_id = int(branch_id)

        customer_name = st.text_input("Customer Name *")
        phone_number = st.text_input("Mobile Number *")
        course_product = st.selectbox("Product *", product_options[1:])
        gross_amount = st.number_input("Gross Sales (₹)", min_value=0.0, step=500.0)
        sale_date_input = st.date_input("Sale Date", value=today)
        submit_sale = st.form_submit_button("Submit")

        if submit_sale:
            if not customer_name or not phone_number:
                st.error("Name and Mobile Number are required.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM customer_sales WHERE mobile_number=?", (phone_number,))
                exists = cursor.fetchone()[0]
                if exists > 0:
                    st.error("Customer with this mobile number already exists.")
                else:
                    cursor.execute("""
                        INSERT INTO customer_sales (sale_id, branch_id, date, name, mobile_number, product_name, gross_sales, status)
                        VALUES ((SELECT ISNULL(MAX(sale_id),0)+1 FROM customer_sales), ?, ?, ?, ?, ?, ?, 'Open')
                    """, (target_branch_id, sale_date_input.strftime("%Y-%m-%d"), customer_name, phone_number, course_product, gross_amount))
                    conn.commit()
                    conn.close()
                    st.success("Sale added successfully!")
                    st.rerun()

    # Add Payment Split
    st.markdown("---")
    st.write("### Add Payment Split")
    with st.form("payment_form", clear_on_submit=True):
        valid_sales = get_data("SELECT sale_id, name FROM customer_sales WHERE status='Open'")
        if not valid_sales.empty:
            sales_options = [f"{row['sale_id']} - {row['name']}" for _, row in valid_sales.iterrows()]
            selected_sale_string = st.selectbox("Sale", sales_options)
            target_sale_id = int(selected_sale_string.split(" - ")[0])
        else:
            target_sale_id = st.number_input("Sale ID", min_value=1, step=1)

        pay_method = st.selectbox("Payment Method", ["Cash","UPI","Card"])
        pay_date = st.date_input("Payment Date", value=today)
        pay_amount = st.number_input("Amount (₹)", min_value=1.0, step=500.0)
        submit_payment = st.form_submit_button("Submit")

        if submit_payment:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM customer_sales WHERE sale_id=?", (target_sale_id,))
            exists = cursor.fetchone()[0]
            if exists == 0:
                st.error("Sale ID not found.")
            else:
                cursor.execute("""
                    INSERT INTO payment_splits (payment_id, sale_id, payment_date, amount_paid, payment_method)
                    VALUES ((SELECT ISNULL(MAX(payment_id),0)+1 FROM payment_splits), ?, ?, ?, ?)
                """, (target_sale_id, pay_date.strftime("%Y-%m-%d"), pay_amount, pay_method))
                conn.commit()
                conn.close()
                st.success("Payment split added successfully!")
                st.rerun()

# Query Explorer Section (Visible only after login)

if st.session_state.get('logged_in'):
    st.markdown("---")
    st.write("### Explore Predefined Queries")

    queries = {
        "1. Retrieve all records from customer_sales":
            "SELECT sale_id, branch_id, date, name, mobile_number, product_name, gross_sales, received_amount, pending_amount, status FROM customer_sales",

        "2. Retrieve all records from branches":
            "SELECT branch_id, branch_name, branch_admin_name FROM branches",

        "3. Retrieve all records from payment_splits":
            "SELECT payment_id, sale_id, payment_date, amount_paid, payment_method FROM payment_splits",

        "4. Display all sales with status = 'Open'":
            "SELECT sale_id, branch_id, date, name, mobile_number, product_name, gross_sales, received_amount, pending_amount, status FROM customer_sales WHERE status='Open'",

        "5. Retrieve all sales belonging to the Chennai branch":
            """SELECT 
                cs.sale_id, cs.date, cs.name, cs.mobile_number, cs.product_name,
                cs.gross_sales, cs.received_amount, cs.pending_amount, cs.status,
                b.branch_name
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id = b.branch_id
            WHERE b.branch_name = 'Chennai'""",

        "6. Total gross sales across all branches":
            "SELECT SUM(gross_sales) AS total_gross_sales FROM customer_sales",

        "7. Total received amount across all sales":
            "SELECT SUM(received_amount) AS total_received FROM customer_sales",

        "8. Total pending amount across all sales":
            "SELECT SUM(pending_amount) AS total_pending FROM customer_sales",

        "9. Count total number of sales per branch":
            """SELECT b.branch_name, COUNT(cs.sale_id) AS total_sales
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id = b.branch_id
            GROUP BY b.branch_name""",

        "10. Average gross sales amount":
            "SELECT AVG(gross_sales) AS avg_gross_sales FROM customer_sales",

        "11. Sales details with branch name":
            """SELECT cs.sale_id, cs.date, cs.name, cs.mobile_number, cs.product_name,
                      cs.gross_sales, cs.received_amount, cs.pending_amount, cs.status,
                      b.branch_name
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id = b.branch_id""",

        "12. Sales details with total payment received":
            """SELECT cs.sale_id, cs.name, SUM(ps.amount_paid) AS total_payment
            FROM customer_sales cs
            LEFT JOIN payment_splits ps ON cs.sale_id = ps.sale_id
            GROUP BY cs.sale_id, cs.name""",

        "13. Branch-wise total gross sales":
            """SELECT b.branch_name, SUM(cs.gross_sales) AS total_gross_sales
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id = b.branch_id
            GROUP BY b.branch_name""",

        "14. Sales with payment method used":
            """SELECT cs.sale_id, cs.name, ps.payment_method, ps.amount_paid
            FROM customer_sales cs
            JOIN payment_splits ps ON cs.sale_id = ps.sale_id""",

        "15. Sales with branch admin name":
            """SELECT cs.sale_id, cs.name, cs.product_name, cs.gross_sales,
                      b.branch_admin_name
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id = b.branch_id""",

        "16. Sales where pending amount > 5000":
            "SELECT sale_id, name, product_name, gross_sales, received_amount, pending_amount FROM customer_sales WHERE pending_amount > 5000",

        "17. Top 3 highest gross sales":
            "SELECT TOP 3 sale_id, name, product_name, gross_sales FROM customer_sales ORDER BY gross_sales DESC",

        "18. Branch with highest total gross sales":
            """SELECT TOP 1 b.branch_name, SUM(cs.gross_sales) AS total_gross_sales
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id = b.branch_id
            GROUP BY b.branch_name
            ORDER BY total_gross_sales DESC""",

        "19. Monthly sales summary":
            """SELECT YEAR(date) AS year, MONTH(date) AS month, SUM(gross_sales) AS total_sales
            FROM customer_sales
            GROUP BY YEAR(date), MONTH(date)
            ORDER BY year, month""",

        "20. Payment method-wise total collection":
            """SELECT payment_method, SUM(amount_paid) AS total_collection
            FROM payment_splits
            GROUP BY payment_method"""
    }

    selected_query = st.selectbox("Choose a query to run:", list(queries.keys()))

    if st.button("Run Query"):
        sql = queries[selected_query]
        result_df = get_data(sql)
        if not result_df.empty:
            st.dataframe(result_df, use_container_width=True)
        else:
            st.warning("No data found for this query.")