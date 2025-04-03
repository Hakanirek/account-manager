import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime
import os
import psycopg2

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


def fetch_vehicles():
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT DISTINCT arac FROM outcomes')
        vehicles = c.fetchall()
    return ['All Vehicles'] + [vehicle[0] for vehicle in vehicles]


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
        c.execute('SELECT id, date, name, transfer_amount, commission FROM transfers')
        transfers = c.fetchall()
    return transfers


def fetch_outcomes(date, vehicle, all_dates):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()

        sql = '''
            SELECT date, arac, tir_plaka,
                SUM(hamal) as total_hamal,
                SUM(arac_masrafi) as total_arac_masrafi,
                SUM(gumruk) as total_gumruk,
                SUM(komsu) as total_komsu,
                SUM(sofor_ve_eks) as total_sofor_ve_eks,
                SUM(indirme_pln) as total_indirme_pln,
                kap_m,
                SUM(toplam_y) as total_toplam_y
            FROM outcomes
        '''

        if all_dates:
            if vehicle != 'All Vehicles':
                sql += ' WHERE arac = ? GROUP BY date, arac, tir_plaka, kap_m'
                c.execute(sql, (vehicle,))
            else:
                sql += ' GROUP BY date, arac, tir_plaka, kap_m'
                c.execute(sql)
        else:
            if vehicle != 'All Vehicles':
                sql += ' WHERE date = ? AND arac = ? GROUP BY date, arac, tir_plaka, kap_m'
                c.execute(sql, (date, vehicle))
            else:
                sql += ' WHERE date = ? GROUP BY date, arac, tir_plaka, kap_m'
                c.execute(sql, (date,))

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


def update_transaction(transaction_id, date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
        DELETE FROM transactions
        WHERE id = ?
        ''', (transaction_id,))
        c.execute('''
        INSERT INTO transactions (date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl))
        conn.commit()


def update_transfer(transfer_id, date, name, transfer_amount, commission):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
        DELETE FROM transfers
        WHERE id = ?
        ''', (transfer_id,))
        c.execute('''
        INSERT INTO transfers (date, name, transfer_amount, commission)
        VALUES (?, ?, ?, ?)
        ''', (date, name, transfer_amount, commission))
        conn.commit()


def update_outcome(outcome_id, date, arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln,
                   kap_m, toplam_y):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
        DELETE FROM outcomes
        WHERE id = ?
        ''', (outcome_id,))
        c.execute('''
        INSERT INTO outcomes (date, arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln, kap_m, toplam_y)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln, kap_m, toplam_y))
        conn.commit()

# Setup the application pages
def show_accounting_page():
    st.title("Accounting Program")

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

    all_dates = st.button("Show All Dates")

    if selected_profile:
        try:
            transactions = fetch_transactions(selected_date.strftime('%Y-%m-%d'), selected_profile, all_dates)
            df_transactions = pd.DataFrame(transactions,
                                           columns=["Date", "Name", "Unit-Kg", "Price", "Dolar", "Euro", "ZL", "T.L",
                                                    "Vehicle", "Kap-Number"])
            st.subheader(
                f"Transactions for {selected_profile} on {'All Dates' if all_dates else selected_date.strftime('%d.%m.%Y')}")
            st.write(df_transactions)

            # Calculate transaction total for all dates or specific date
            transaction_total_dolar = round(df_transactions['Dolar'].sum(), 2)
            transaction_total_euro = round(df_transactions['Euro'].sum(), 2)
            transaction_total_zl = round(df_transactions['ZL'].sum(), 2)
            transaction_total_tl = round(df_transactions['T.L'].sum(), 2)
            transaction_total_kg = round(df_transactions['Unit-Kg'].sum(), 2)

            # Show transaction total for all profiles under the transactions table
            st.write(
                f"Transaction Total for {'All Profiles' if selected_profile == 'All Profiles' else selected_profile}: Dolar: {transaction_total_dolar}, Euro: {transaction_total_euro}, ZL: {transaction_total_zl}, T.L: {transaction_total_tl}, KG: {transaction_total_kg}")

        except Exception as e:
            st.error(f"An error occurred: {e}")

    vehicles = fetch_vehicles()
    selected_vehicle = st.selectbox("Select Vehicle", options=vehicles)

    st.header(f"Outcome Data for Selected Date and Vehicle: {selected_vehicle}")
    try:
        selected_date_str = selected_date.strftime('%Y-%m-%d')
        outcomes = fetch_outcomes(selected_date_str, selected_vehicle, all_dates)
        df_outcomes = pd.DataFrame(outcomes,
                                   columns=["Date", "Araç", "Tır Plaka",
                                            "Total Hamal", "Total Araç Masrafı", "Total Gümrük",
                                            "Total KOMŞU", "Total ŞOFÖR VE EKS.", "Total İNDİRME PLN.",
                                            "KAP M.", "Total Toplam Y"])
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

        monthly_total_dolar = round(df_monthly_summary['Total Dolar'].sum(),2)
        monthly_total_euro = round(df_monthly_summary['Total Euro'].sum(),2)
        monthly_total_zl = round(df_monthly_summary['Total ZL'].sum(),2)
        monthly_total_tl = round(df_monthly_summary['Total T.L'].sum(),2)
        monthly_total_kg = round(df_monthly_summary['Total Unit-Kg'].sum(),2)


        st.write(
            f"Monthly Total for {selected_profile}: Dolar: {monthly_total_dolar}, Euro: {monthly_total_euro}, ZL: {monthly_total_zl}, T.L: {monthly_total_tl}, KG: {monthly_total_kg}", )
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

        yearly_total_dolar = round(df_yearly_summary['Total Dolar'].sum(),2)
        yearly_total_euro = round(df_yearly_summary['Total Euro'].sum(),2)
        yearly_total_zl = round(df_yearly_summary['Total ZL'].sum(),2)
        yearly_total_tl = round(df_yearly_summary['Total T.L'].sum(),2)
        yearly_total_kg = round(df_yearly_summary['Total Unit-Kg'].sum(),2)
        st.write(
            f"Yearly Total for {selected_profile}: Dolar: {yearly_total_dolar}, Euro: {yearly_total_euro}, ZL: {yearly_total_zl}, T.L: {yearly_total_tl}, KG: {yearly_total_kg}")
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
        df_transfers = pd.DataFrame(transfers, columns=["ID", "Date", "Name", "Transfer Amount", "Commission"])
        st.write(df_transfers)
    except Exception as e:
        st.error(f"An error occurred: {e}")


def show_edit_page():
    st.title("Edit Data Records")

    edit_option = st.radio("Select Data Type to Edit", ("Transactions", "Transfers", "Outcomes"))

    if edit_option == "Transactions":
        transactions = fetch_transactions(datetime.now().strftime('%Y-%m-%d'), 'All Profiles', True)
        df_transactions = pd.DataFrame(transactions,
                                       columns=["Date", "Name", "Unit-Kg", "Price", "Dolar", "Euro", "ZL", "T.L", "Vehicle", "Kap-Number"])
        st.dataframe(df_transactions)

        if not df_transactions.empty:
            row_index = st.selectbox("Select Row ID to Edit", df_transactions.index.tolist())
            transaction_row = df_transactions.loc[row_index]

            with st.form("edit_transaction_form"):
                date = st.date_input("Date", value=pd.to_datetime(transaction_row['Date']))
                name = st.text_input("Name", value=transaction_row['Name'])
                vehicle = st.text_input("Vehicle", value=transaction_row['Vehicle'])
                kap_number = st.text_input("Kap Number", value=transaction_row['Kap-Number'])
                unit_kg = st.number_input("Unit Kg", value=transaction_row['Unit-Kg'])
                price = st.number_input("Price", value=transaction_row['Price'])
                dolar = st.number_input("Dolar", value=transaction_row['Dolar'])
                euro = st.number_input("Euro", value=transaction_row['Euro'])
                zl = st.number_input("ZL", value=transaction_row['ZL'])
                tl = st.number_input("TL", value=transaction_row['T.L'])
                submit_btn = st.form_submit_button("Update Transaction")

                if submit_btn:
                    # Call the update function with row_index and new values to update the database
                    update_transaction(row_index, date.strftime("%Y-%m-%d"), name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl)
                    st.success("Transaction updated successfully")

                    # Re-fetch updated transactions to reflect changes
                    transactions = fetch_transactions(datetime.now().strftime('%Y-%m-%d'), 'All Profiles', True)
                    df_transactions = pd.DataFrame(transactions, columns=["Date", "Name", "Unit-Kg", "Price", "Dolar", "Euro", "ZL", "T.L", "Vehicle", "Kap-Number"])
                    st.dataframe(df_transactions)

    elif edit_option == "Transfers":
        transfers = fetch_transfers()
        df_transfers = pd.DataFrame(transfers, columns=["ID", "Date", "Name", "Transfer Amount", "Commission"])
        st.dataframe(df_transfers)

        if not df_transfers.empty:
            transfer_id = st.selectbox("Select Transfer ID to Edit", df_transfers['ID'].tolist())
            transfer_row = df_transfers[df_transfers['ID'] == transfer_id]

            if not transfer_row.empty:
                transfer_row = transfer_row.iloc[0]
                with st.form("edit_transfer_form"):
                    date = st.date_input("Date", value=pd.to_datetime(transfer_row['Date']))
                    name = st.text_input("Name", value=transfer_row['Name'])
                    transfer_amount = st.number_input("Transfer Amount", value=float(transfer_row['Transfer Amount']))
                    commission = st.number_input("Commission", value=float(transfer_row['Commission']))
                    submit_btn = st.form_submit_button("Update Transfer")

                    if submit_btn:
                        update_transfer(transfer_id, date.strftime("%Y-%m-%d"), name, transfer_amount, commission)
                        st.success("Transfer updated successfully")

                        transfers = fetch_transfers()
                        df_transfers = pd.DataFrame(transfers, columns=["ID", "Date", "Name", "Transfer Amount", "Commission"])
                        st.dataframe(df_transfers)

    elif edit_option == "Outcomes":
        selected_date = st.date_input("Choose a date for Outcomes", pd.to_datetime("today").date())
        all_dates = st.checkbox("Show All Dates")
        outcomes = fetch_outcomes(selected_date.strftime('%Y-%m-%d'), 'All Vehicles', all_dates)

        df_outcomes = pd.DataFrame(outcomes,
                                   columns=["Date", "Araç", "Tır Plaka", "Total Hamal", "Total Araç Masrafı", "Total Gümrük", "Total KOMŞU", "Total ŞOFÖR VE EKS.", "Total İNDİRME PLN.", "KAP M.", "Total Toplam Y"])
        st.dataframe(df_outcomes)

        if not df_outcomes.empty:
            row_index = st.selectbox("Select Row ID to Edit", df_outcomes.index.tolist())
            outcome_row = df_outcomes.loc[row_index]

            with st.form("edit_outcome_form"):
                date = st.date_input("Date", value=pd.to_datetime(outcome_row['Date']))
                arac = st.text_input("Araç", value=outcome_row['Araç'])
                tir_plaka = st.text_input("Tır Plaka", value=outcome_row['Tır Plaka'])
                hamal = st.number_input("Total Hamal", value=float(outcome_row['Total Hamal']))
                arac_masrafi = st.number_input("Total Araç Masrafı", value=float(outcome_row['Total Araç Masrafı']))
                gumruk = st.number_input("Total Gümrük", value=float(outcome_row['Total Gümrük']))
                komsu = st.number_input("Total KOMŞU", value=float(outcome_row['Total KOMŞU']))
                sofor_ve_eks = st.number_input("Total ŞOFÖR VE EKS.", value=float(outcome_row['Total ŞOFÖR VE EKS.']))
                indirme_pln = st.number_input("Total İNDİRME PLN.", value=float(outcome_row['Total İNDİRME PLN.']))
                kap_m = st.text_input("KAP M.", value=outcome_row['KAP M.'])
                toplam_y = st.number_input("Total Toplam Y", value=float(outcome_row['Total Toplam Y']))
                submit_btn = st.form_submit_button("Update Outcome")

                if submit_btn:
                    update_outcome(row_index, date.strftime("%Y-%m-%d"), arac, tir_plaka, hamal, arac_masrafi, gumruk, komsu, sofor_ve_eks, indirme_pln, kap_m, toplam_y)
                    st.success("Outcome updated successfully")

                    outcomes = fetch_outcomes(selected_date.strftime('%Y-%m-%d'), 'All Vehicles', all_dates)
                    df_outcomes = pd.DataFrame(outcomes,
                                               columns=["Date", "Araç", "Tır Plaka", "Total Hamal", "Total Araç Masrafı", "Total Gümrük", "Total KOMŞU", "Total ŞOFÖR VE EKS.", "Total İNDİRME PLN.", "KAP M.", "Total Toplam Y"])
                    st.dataframe(df_outcomes)

        if not df_outcomes.empty:
            row_index = st.selectbox("Select Row ID to Edit", df_outcomes.index.tolist())
            outcome_row = df_outcomes.loc[row_index]

            with st.form("edit_outcome_form"):
                date = st.date_input("Date", value=pd.to_datetime(outcome_row['Date']))
                arac = st.text_input("Araç", value=outcome_row['Araç'])
                tir_plaka = st.text_input("Tır Plaka", value=outcome_row['Tır Plaka'])

                hamal = st.number_input("Total Hamal", value=float(outcome_row['Total Hamal']))
                arac_masrafi = st.number_input("Total Araç Masrafı", value=float(outcome_row['Total Araç Masrafı']))
                gumruk = st.number_input("Total Gümrük", value=float(outcome_row['Total Gümrük']))
                komsu = st.number_input("Total KOMŞU", value=float(outcome_row['Total KOMŞU']))
                sofor_ve_eks = st.number_input("Total ŞOFÖR VE EKS.", value=float(outcome_row['Total ŞOFÖR VE EKS.']))
                indirme_pln = st.number_input("Total İNDİRME PLN.", value=float(outcome_row['Total İNDİRME PLN.']))
                kap_m = st.text_input("KAP M.", value=outcome_row['KAP M.'])
                toplam_y = st.number_input("Total Toplam Y", value=float(outcome_row['Total Toplam Y']))
                submit_btn = st.form_submit_button("Update Outcome")

                if submit_btn:
                    update_outcome(row_index, date.strftime("%Y-%m-%d"), arac, tir_plaka, hamal, arac_masrafi, gumruk,
                                   komsu, sofor_ve_eks, indirme_pln, kap_m, toplam_y)
                    st.success("Outcome updated successfully")
        else:
            st.warning("No outcomes available for selection.")


# Setup the sidebar navigation
setup_database()
page_selection = st.sidebar.selectbox("Select Page", ["Accounting", "Transfer", "Edit Data"])

if page_selection == "Accounting":
    show_accounting_page()
elif page_selection == "Transfer":
    show_transfer_page()
elif page_selection == "Edit Data":
    show_edit_page()
