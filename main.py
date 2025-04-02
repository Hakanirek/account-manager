import streamlit as st
import pandas as pd
import sqlite3
import time
import os
import psycopg2
from datetime import datetime


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Unable to connect to the database: {e}")
        return None


# Setup the SQLite Database
def setup_database():
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()

        c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            name TEXT,
            vehicle TEXT,
            kap_number TEXT,
            unit_kg REAL,
            price REAL,
            dolar REAL,
            euro REAL,
            zl REAL,
            tl REAL
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            balance_dolar REAL DEFAULT 0,
            balance_euro REAL DEFAULT 0,
            balance_zl REAL DEFAULT 0,
            balance_tl REAL DEFAULT 0
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            name TEXT,
            transfer_amount REAL,
            commission REAL
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            arac TEXT,
            tir_plaka TEXT,
            hamal REAL,
            arac_masrafi REAL,
            gumruk REAL,
            komsu REAL,
            sofor_ve_eks REAL,
            indirme_pln REAL,
            kap_m TEXT,
            toplam_y REAL
        )
        ''')

        conn.commit()


# Functions to interact with the database
def insert_transaction(date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl):
    retry_count = 5
    while retry_count > 0:
        try:
            with sqlite3.connect('profiles.db', timeout=10) as conn:
                c = conn.cursor()

                c.execute('SELECT COUNT(*) FROM transactions WHERE date = ? AND name = ? AND vehicle = ?',
                          (date, name, vehicle))
                count = c.fetchone()[0]
                if count == 0:
                    c.execute('''
                    INSERT INTO transactions (date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl))

                c.execute('SELECT balance_dolar, balance_euro, balance_zl, balance_tl FROM profiles WHERE name = ?',
                          (name,))
                result = c.fetchone()
                if result:
                    new_balance_dolar = (result[0] or 0) + dolar
                    new_balance_euro = (result[1] or 0) + euro
                    new_balance_zl = (result[2] or 0) + zl
                    new_balance_tl = (result[3] or 0) + tl
                    c.execute(
                        'UPDATE profiles SET balance_dolar = ?, balance_euro = ?, balance_zl = ?, balance_tl = ? WHERE name = ?',
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
        c.execute('SELECT COUNT(*) FROM transfers WHERE date = ? AND name = ?', (date, name))
        count = c.fetchone()[0]
        if count == 0:
            c.execute('INSERT INTO transfers (date, name, transfer_amount, commission) VALUES (?, ?, ?, ?)',
                      (date, name, transfer_amount, commission))
        conn.commit()


def insert_outcome(date, arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln, kap_m,
                   toplam_y):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO outcomes (date, arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln, kap_m, toplam_y) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (date, arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln, kap_m, toplam_y))
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
        sql = '''
            SELECT date, name,
                ROUND(SUM(unit_kg), 2) as unit_kg, ROUND(SUM(price), 2) as price,
                ROUND(SUM(dolar), 2) as dolar, ROUND(SUM(euro), 2) as euro, ROUND(SUM(zl), 2) as zl, ROUND(SUM(tl), 2) as tl,
                TRIM(GROUP_CONCAT(DISTINCT vehicle), ', ') as vehicle, TRIM(GROUP_CONCAT(DISTINCT kap_number), ', ') as kap_number
            FROM transactions
        '''

        if all_dates:
            if profile == 'All Profiles':
                sql += ' GROUP BY date, name'
                c.execute(sql)
            else:
                sql += ' WHERE name = ? GROUP BY date, name'
                c.execute(sql, (profile,))
        else:
            if profile == 'All Profiles':
                sql += ' WHERE date = ? GROUP BY date, name'
                c.execute(sql, (date,))
            else:
                sql += ' WHERE date = ? AND name = ? GROUP BY date, name'
                c.execute(sql, (date, profile))

        transactions = c.fetchall()
    return transactions


def fetch_transfers():
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT date, name, transfer_amount, commission FROM transfers')
        transfers = c.fetchall()
    return transfers


def fetch_outcomes(date):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute(
            'SELECT date, arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln, kap_m, toplam_y FROM outcomes WHERE date = ?',
            (date,))
        outcomes = c.fetchall()
    return outcomes


def fetch_monthly_summary(month, profile):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        sql = '''
            SELECT name,
                ROUND(SUM(dolar), 2) as total_dolar, ROUND(SUM(euro), 2) as total_euro, ROUND(SUM(zl), 2) as total_zl, ROUND(SUM(tl), 2) as total_tl,
                ROUND(SUM(unit_kg), 2) as total_unit_kg, ROUND(SUM(price), 2) as total_price
            FROM transactions
            WHERE strftime("%m", date) = ?
        '''
        if profile == 'All Profiles':
            sql += ' GROUP BY name'
            c.execute(sql, (month,))
        else:
            sql += ' AND name = ? GROUP BY name'
            c.execute(sql, (month, profile))

        monthly_summary = c.fetchall()
    return monthly_summary


def fetch_yearly_summary(year, profile):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        sql = '''
            SELECT name,
                ROUND(SUM(dolar), 2) as total_dolar, ROUND(SUM(euro), 2) as total_euro, ROUND(SUM(zl), 2) as total_zl, ROUND(SUM(tl), 2) as total_tl,
                ROUND(SUM(unit_kg), 2) as total_unit_kg, ROUND(SUM(price), 2) as total_price
            FROM transactions
            WHERE strftime("%Y", date) = ?
        '''
        if profile == 'All Profiles':
            sql += ' GROUP BY name'
            c.execute(sql, (year,))
        else:
            sql += ' AND name = ? GROUP BY name'
            c.execute(sql, (year, profile))

        yearly_summary = c.fetchall()
    return yearly_summary


# Setup the application pages
def show_accounting_page():
    st.title("Accounting Program")

    # This remains the same
    uploaded_file = st.file_uploader("Upload Process Excel file with Date, Name, Dolar, Euro, ZL, T.L", type="xlsx",
                                     key="transactions")

    if uploaded_file:
        try:
            daily_data = pd.read_excel(uploaded_file)
            daily_data['Date'] = pd.to_datetime(daily_data['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')

            for _, row in daily_data.iterrows():
                date, name = row['Date'], row['Name']
                dolar = row['Dolar'] if not pd.isna(row['Dolar']) else 0
                euro = row['Euro'] if not pd.isna(row['Euro']) else 0
                zl = row['ZL'] if not pd.isna(row['ZL']) else 0
                tl = row['T.L'] if not pd.isna(row['T.L']) else 0
                insert_transaction(date, name, '', '', 0, 0, dolar, euro, zl, tl)
            st.success('Transaction data uploaded successfully')
        except Exception as e:
            st.error(f"An error occurred: {e}")

    # This section is updated to handle two sheets
    income_file = st.file_uploader(
        "Upload Income-Outcome Excel file with Income and Outcome sheets", type="xlsx", key="income")

    if income_file:
        try:
            xls = pd.ExcelFile(income_file)

            if 'Income' in xls.sheet_names:
                income_data = pd.read_excel(xls, sheet_name='Income')
                income_data['Date'] = pd.to_datetime(income_data['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')

                for _, row in income_data.iterrows():
                    date = row['Date']
                    name = row['Name']
                    vehicle = str(row.get('Vehicle', ''))
                    kap_number = str(row.get('Kap-Number', ''))
                    unit_kg = row.get('Unit-Kg', 0) if not pd.isna(row.get('Unit-Kg', 0)) else 0
                    price = row.get('Price', 0) if not pd.isna(row.get('Price', 0)) else 0
                    dolar = row.get('Dolar', 0) if not pd.isna(row.get('Dolar', 0)) else 0
                    euro = row.get('Euro', 0) if not pd.isna(row.get('Euro', 0)) else 0
                    zl = row.get('ZL', 0) if 'ZL' in row and not pd.isna(row['ZL']) else 0
                    tl = row.get('T.L', 0) if 'T.L' in row and not pd.isna(row['T.L']) else 0
                    insert_transaction(date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl)
                st.success('Income data uploaded successfully')

            if 'Outcome' in xls.sheet_names:
                outcome_data = pd.read_excel(xls, sheet_name='Outcome')
                outcome_data['Date'] = pd.to_datetime(outcome_data['Date']).dt.strftime('%Y-%m-%d')

                for _, row in outcome_data.iterrows():
                    date = row['Date']
                    arac = row['Araç']
                    tir_plaka = row['Tır Plaka']
                    hamal = row.get('Hamal', 0) if not pd.isna(row.get('Hamal', 0)) else 0
                    arac_masrafi = row.get('Araç Masrafı', 0) if not pd.isna(row.get('Araç Masrafı', 0)) else 0
                    gumruk = row.get('Gümrük', 0) if not pd.isna(row.get('Gümrük', 0)) else 0
                    komsu = row.get('KOMŞU', 0) if not pd.isna(row.get('KOMŞU', 0)) else 0
                    sofor_ve_eks = row.get('ŞOFÖR VE EKS.', 0) if not pd.isna(row.get('ŞOFÖR VE EKS.', 0)) else 0
                    indirme_pln = row.get('İNDİRME PLN.', 0) if not pd.isna(row.get('İNDİRME PLN.', 0)) else 0
                    kap_m = row.get('KAP M.', '')
                    toplam_y = row.get('Toplam Y', 0) if not pd.isna(row.get('Toplam Y', 0)) else 0
                    insert_outcome(date, arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln,
                                   kap_m, toplam_y)
                st.success('Outcome data uploaded successfully')

        except Exception as e:
            st.error(f"An error occurred: {e}")

    profiles = fetch_profiles()
    selected_profile = st.selectbox("Select Profile", options=profiles)

    st.header("Select Date for Transactions")
    selected_date = st.date_input("Choose a date", pd.to_datetime("today").date())

    all_dates = st.checkbox("Show All Dates")

    if selected_profile:
        try:
            transactions = fetch_transactions(selected_date.strftime('%Y-%m-%d'), selected_profile, all_dates)
            df_transactions = pd.DataFrame(transactions,
                                           columns=["Date", "Name", "Unit-Kg", "Price", "Dolar", "Euro", "ZL", "T.L",
                                                    "Vehicle", "Kap-Number"])
            st.subheader(
                f"Transactions for {selected_profile} on {'All Dates' if all_dates else selected_date.strftime('%d.%m.%Y')}")
            st.write(df_transactions)
        except Exception as e:
            st.error(f"An error occurred: {e}")

    st.header("Outcome Data for Selected Date")
    try:
        selected_date_str = selected_date.strftime('%Y-%m-%d')
        outcomes = fetch_outcomes(selected_date_str)
        df_outcomes = pd.DataFrame(outcomes,
                                   columns=["Date", "Araç", "Tır Plaka", "Hamal", "Araç Masrafı", "Gümrük", "KOMŞU",
                                            "ŞOFÖR VE EKS.", "İNDİRME PLN.", "KAP M.", "Toplam Y"])
        st.write(df_outcomes)
    except Exception as e:
        st.error(f"An error occurred: {e}")

    st.header("Monthly Summary")
    current_month = selected_date.strftime('%m')
    try:
        monthly_summary = fetch_monthly_summary(current_month, selected_profile)
        df_monthly_summary = pd.DataFrame(monthly_summary,
                                          columns=["Name", "Total Dolar", "Total Euro", "Total ZL", "Total T.L",
                                                   "Total Unit-Kg", "Total Price"])
        st.write(df_monthly_summary)

        monthly_total_dolar = df_monthly_summary['Total Dolar'].sum()
        monthly_total_euro = df_monthly_summary['Total Euro'].sum()
        monthly_total_zl = df_monthly_summary['Total ZL'].sum()
        monthly_total_tl = df_monthly_summary['Total T.L'].sum()
        monthly_total_unit_kg = df_monthly_summary['Total Unit-Kg'].sum()

        st.markdown(
            f"**Monthly Total for {selected_profile}:** Dolar: {monthly_total_dolar}, Euro: {monthly_total_euro}, ZL: {monthly_total_zl}, T.L: {monthly_total_tl}, Unit-Kg: {monthly_total_unit_kg}"
        )
    except Exception as e:
        st.error(f"An error occurred: {e}")

    st.header("Yearly Summary")
    current_year = selected_date.strftime('%Y')
    try:
        yearly_summary = fetch_yearly_summary(current_year, selected_profile)
        df_yearly_summary = pd.DataFrame(yearly_summary,
                                         columns=["Name", "Total Dolar", "Total Euro", "Total ZL", "Total T.L",
                                                  "Total Unit-Kg", "Total Price"])
        st.write(df_yearly_summary)

        yearly_total_dolar = df_yearly_summary['Total Dolar'].sum()
        yearly_total_euro = df_yearly_summary['Total Euro'].sum()
        yearly_total_zl = df_yearly_summary['Total ZL'].sum()
        yearly_total_tl = df_yearly_summary['Total T.L'].sum()
        yearly_total_unit_kg = df_yearly_summary['Total Unit-Kg'].sum()

        st.markdown(
            f"**Yearly Total for {selected_profile}:** Dolar: {yearly_total_dolar}, Euro: {yearly_total_euro}, ZL: {yearly_total_zl}, T.L: {yearly_total_tl}, Unit-Kg: {yearly_total_unit_kg}"
        )
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
                    insert_transfer(transfer_date.strftime('%Y-%m-%d'), transfer_name, transfer_amount,
                                    transfer_commission)
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
