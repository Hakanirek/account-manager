import subprocess
import sys
import streamlit as st
import pandas as pd
import sqlite3
import time

# Setup the SQLite Database
def setup_database():
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()

        c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            date TEXT,
            name TEXT,
            dolar REAL,
            euro REAL,
            zl REAL,
            tl REAL,
            UNIQUE(date, name, dolar, euro, zl, tl) ON CONFLICT IGNORE
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            balance_dolar REAL,
            balance_euro REAL,
            balance_zl REAL,
            balance_tl REAL
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            date TEXT,
            name TEXT,
            transfer_amount REAL,
            commission REAL
        )
        ''')
        conn.commit()

# Functions to interact with the database
def insert_transaction(date, name, dolar, euro, zl, tl):
    retry_count = 5
    while retry_count > 0:
        try:
            with sqlite3.connect('profiles.db', timeout=10) as conn:
                c = conn.cursor()
                c.execute('INSERT INTO transactions (date, name, dolar, euro, zl, tl) VALUES (?, ?, ?, ?, ?, ?)',
                          (date, name, dolar, euro, zl, tl))
                c.execute('SELECT balance_dolar, balance_euro, balance_zl, balance_tl FROM profiles WHERE name = ?', (name,))
                result = c.fetchone()
                if result:
                    new_balance_dolar = result[0] + dolar
                    new_balance_euro = result[1] + euro
                    new_balance_zl = result[2] + zl
                    new_balance_tl = result[3] + tl
                    c.execute('UPDATE profiles SET balance_dolar = ?, balance_euro = ?, balance_zl = ?, balance_tl = ? WHERE name = ?',
                              (new_balance_dolar, new_balance_euro, new_balance_zl, new_balance_tl, name))
                else:
                    c.execute(
                        'INSERT INTO profiles (name, balance_dolar, balance_euro, balance_zl, balance_tl) VALUES (?, ?, ?, ?, ?)',
                        (name, dolar, euro, zl, tl))
                conn.commit()
            break
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                retry_count -= 1
                time.sleep(1)
            else:
                st.error(f"An error occurred: {e}")
                break

def insert_transfer(date, name, transfer_amount, commission):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO transfers (date, name, transfer_amount, commission) VALUES (?, ?, ?, ?)',
                  (date, name, transfer_amount, commission))
        conn.commit()

def fetch_profiles():
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT name FROM profiles')
        profiles = c.fetchall()
    return ['All Profiles'] + [profile[0] for profile in profiles]

def fetch_transactions(date, profile, all_dates):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        if all_dates:
            if profile == 'All Profiles':
                c.execute('SELECT date, name, dolar, euro, zl, tl FROM transactions')
            else:
                c.execute('SELECT date, name, dolar, euro, zl, tl FROM transactions WHERE name = ?', (profile,))
        else:
            if profile == 'All Profiles':
                c.execute('SELECT date, name, dolar, euro, zl, tl FROM transactions WHERE date = ?', (date,))
            else:
                c.execute('SELECT date, name, dolar, euro, zl, tl FROM transactions WHERE date = ? AND name = ?',
                          (date, profile))
        transactions = c.fetchall()
    return transactions

def fetch_transfers():
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT date, name, transfer_amount, commission FROM transfers')
        transfers = c.fetchall()
    return transfers

def fetch_monthly_summary(month, profile):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        if profile == 'All Profiles':
            c.execute(
                'SELECT name, SUM(dolar) as total_dolar, SUM(euro) as total_euro, SUM(zl) as total_zl, SUM(tl) as total_tl FROM transactions WHERE strftime("%m", date) = ? GROUP BY name',
                (month,))
        else:
            c.execute(
                'SELECT name, SUM(dolar) as total_dolar, SUM(euro) as total_euro, SUM(zl) as total_zl, SUM(tl) as total_tl FROM transactions WHERE strftime("%m", date) = ? AND name = ? GROUP BY name',
                (month, profile))
        monthly_summary = c.fetchall()
    return monthly_summary

def fetch_yearly_summary(year, profile):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        if profile == 'All Profiles':
            c.execute(
                'SELECT name, SUM(dolar) as total_dolar, SUM(euro) as total_euro, SUM(zl) as total_zl, SUM(tl) as total_tl FROM transactions WHERE strftime("%Y", date) = ? GROUP BY name',
                (year,))
        else:
            c.execute(
                'SELECT name, SUM(dolar) as total_dolar, SUM(euro) as total_euro, SUM(zl) as total_zl, SUM(tl) as total_tl FROM transactions WHERE strftime("%Y", date) = ? AND name = ? GROUP BY name',
                (year, profile))
        yearly_summary = c.fetchall()
    return yearly_summary

def run_streamlit():
    if len(sys.argv) == 1:
        subprocess.run([sys.executable, "-m", "streamlit", "run", sys.argv[0], '--server.port=8501'])

# Setup the application pages
def show_accounting_page():
    st.title("Accounting Program")

    uploaded_file = st.file_uploader("Upload Excel file with Date, Name, Dolar, Euro, ZL, T.L", type="xlsx")

    if uploaded_file:
        try:
            daily_data = pd.read_excel(uploaded_file)
            daily_data['Date'] = pd.to_datetime(daily_data['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')

            for index, row in daily_data.iterrows():
                date, name = row['Date'], row['Name']
                dolar, euro, zl, tl = row['Dolar'], row['Euro'], row['ZL'], row['T.L']
                insert_transaction(date, name, dolar, euro, zl, tl)
            st.success('Data uploaded successfully')
        except Exception as e:
            st.error(f"An error occurred: {e}")

    profiles = fetch_profiles()
    selected_profile = st.selectbox("Select Profile", options=profiles)

    st.header("Select Date for Transactions")
    selected_date = st.date_input("Choose a date", pd.to_datetime("today").date())

    all_dates = st.button("Show All Dates")

    if selected_profile:
        try:
            transactions = fetch_transactions(selected_date.strftime('%Y-%m-%d'), selected_profile, all_dates)
            df_transactions = pd.DataFrame(transactions, columns=["Date", "Name", "Dolar", "Euro", "ZL", "T.L"])
            st.subheader(
                f"Transactions for {selected_profile} on {'All Dates' if all_dates else selected_date.strftime('%d.%m.%Y')}")
            st.write(df_transactions)
        except Exception as e:
            st.error(f"An error occurred: {e}")

    st.header("Monthly Summary")
    current_month = selected_date.strftime('%m')
    try:
        monthly_summary = fetch_monthly_summary(current_month, selected_profile)
        df_monthly_summary = pd.DataFrame(monthly_summary, columns=["Name", "Total Dolar", "Total Euro", "Total ZL", "Total T.L"])
        st.write(df_monthly_summary)

        monthly_total_dolar = df_monthly_summary['Total Dolar'].sum()
        monthly_total_euro = df_monthly_summary['Total Euro'].sum()
        monthly_total_zl = df_monthly_summary['Total ZL'].sum()
        monthly_total_tl = df_monthly_summary['Total T.L'].sum()
        st.write(
            f"Monthly Total for {selected_profile}: Dolar: {monthly_total_dolar}, Euro: {monthly_total_euro}, ZL: {monthly_total_zl}, T.L: {monthly_total_tl}")
    except Exception as e:
        st.error(f"An error occurred: {e}")

    st.header("Yearly Summary")
    current_year = selected_date.strftime('%Y')
    try:
        yearly_summary = fetch_yearly_summary(current_year, selected_profile)
        df_yearly_summary = pd.DataFrame(yearly_summary, columns=["Name", "Total Dolar", "Total Euro", "Total ZL", "Total T.L"])
        st.write(df_yearly_summary)

        yearly_total_dolar = df_yearly_summary['Total Dolar'].sum()
        yearly_total_euro = df_yearly_summary['Total Euro'].sum()
        yearly_total_zl = df_yearly_summary['Total ZL'].sum()
        yearly_total_tl = df_yearly_summary['Total T.L'].sum()
        st.write(
            f"Yearly Total for {selected_profile}: Dolar: {yearly_total_dolar}, Euro: {yearly_total_euro}, ZL: {yearly_total_zl}, T.L: {yearly_total_tl}")
    except Exception as e:
        st.error(f"An error occurred: {e}")

def show_transfer_page():
    st.title("Transfer Management")

    transfer_option = st.radio("Select Transfer Method", ("Upload File", "Manual Entry"))

    if transfer_option == "Upload File":
        transfer_file = st.file_uploader("Upload Excel file with Date, Name, Transfer Amount, Commission", type="xlsx")

        if transfer_file:
            try:
                transfer_data = pd.read_excel(transfer_file)
                transfer_data['Date'] = pd.to_datetime(transfer_data['Date']).dt.strftime('%Y-%m-%d')

                for index, row in transfer_data.iterrows():
                    date, name = row['Date'], row['Name']
                    transfer_amount, commission = row['Transfer Amount'], row['Commission']
                    insert_transfer(date, name, transfer_amount, commission)
                st.success('Transfer data uploaded and recorded successfully')
            except Exception as e:
                st.error(f"An error occurred: {e}")

    elif transfer_option == "Manual Entry":
        with st.form("manual_transfer_form"):
            transfer_date = st.date_input("Transaction date", pd.to_datetime("today").date())
            transfer_name = st.text_input("Name")
            transfer_amount = st.number_input("Transfer Amount", min_value=0.0)
            transfer_commission = st.number_input("Commission", min_value=0.0)
            submit_btn = st.form_submit_button("Submit Transfer")

            if submit_btn:
                if not transfer_name.strip():
                    st.error("Name is required.")
                elif transfer_amount <= 0:
                    st.error("Transfer Amount must be greater than 0.")
                elif transfer_commission < 0:
                    st.error("Commission cannot be negative.")
                else:
                    insert_transfer(transfer_date.strftime('%Y-%m-%d'), transfer_name, transfer_amount, transfer_commission)
                    st.success("Transfer recorded successfully")

    st.subheader("All Transfers")
    try:
        transfers = fetch_transfers()
        df_transfers = pd.DataFrame(transfers, columns=["Date", "Name", "Transfer Amount", "Commission"])
        st.write(df_transfers)
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Setup the sidebar navigation
setup_database()
page_selection = st.sidebar.selectbox("Select Page", ["Accounting", "Transfer"])

if page_selection == "Accounting":
    show_accounting_page()
elif page_selection == "Transfer":
    show_transfer_page()
