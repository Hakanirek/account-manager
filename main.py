import os
import streamlit as st
import pandas as pd
import psycopg2
import time
import subprocess
import sys


# Function to get database connection using credentials from environment variables
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


# Function to set up the database
def setup_database():
    conn = get_db_connection()
    if conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            date TEXT,
            name TEXT,
            dolar REAL,
            euro REAL,
            zl REAL,
            UNIQUE (date, name, dolar, euro, zl) ON CONFLICT DO NOTHING
        )
        ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            balance_dolar REAL,
            balance_euro REAL,
            balance_zl REAL
        )
        ''')
        conn.commit()
        c.close()
        conn.close()


def insert_transaction(date, name, dolar, euro, zl):
    retry_count = 5
    while retry_count > 0:
        conn = get_db_connection()
        if conn:
            try:
                c = conn.cursor()
                c.execute('INSERT INTO transactions (date, name, dolar, euro, zl) VALUES (%s, %s, %s, %s, %s)',
                          (date, name, dolar, euro, zl))
                c.execute('SELECT balance_dolar, balance_euro, balance_zl FROM profiles WHERE name = %s', (name,))
                result = c.fetchone()
                if result:
                    new_balance_dolar = result[0] + dolar
                    new_balance_euro = result[1] + euro
                    new_balance_zl = result[2] + zl
                    c.execute('UPDATE profiles SET balance_dolar = %s, balance_euro = %s, balance_zl = %s WHERE name = %s',
                              (new_balance_dolar, new_balance_euro, new_balance_zl, name))
                else:
                    c.execute(
                        'INSERT INTO profiles (name, balance_dolar, balance_euro, balance_zl) VALUES (%s, %s, %s, %s)',
                        (name, dolar, euro, zl))
                conn.commit()
                c.close()
                conn.close()
                break
            except psycopg2.OperationalError as e:
                st.error(f"An error occurred: {e}")
                retry_count -= 1
                time.sleep(1)
            finally:
                if conn:
                    conn.close()


def fetch_profiles():
    conn = get_db_connection()
    profiles = []
    if conn:
        try:
            c = conn.cursor()
            c.execute('SELECT name FROM profiles')
            profiles = c.fetchall()
            c.close()
        except psycopg2.Error as e:
            st.error(f"An error occurred while fetching profiles: {e}")
        finally:
            conn.close()
    return ['All Profiles'] + [profile[0] for profile in profiles]


def fetch_transactions(date, profile, all_dates):
    conn = get_db_connection()
    transactions = []
    if conn:
        try:
            c = conn.cursor()
            if all_dates:
                if profile == 'All Profiles':
                    c.execute('SELECT date, name, dolar, euro, zl FROM transactions')
                else:
                    c.execute('SELECT date, name, dolar, euro, zl FROM transactions WHERE name = %s', (profile,))
            else:
                if profile == 'All Profiles':
                    c.execute('SELECT date, name, dolar, euro, zl FROM transactions WHERE date = %s', (date,))
                else:
                    c.execute('SELECT date, name, dolar, euro, zl FROM transactions WHERE date = %s AND name = %s',
                              (date, profile))
            transactions = c.fetchall()
            c.close()
        except psycopg2.Error as e:
            st.error(f"An error occurred while fetching transactions: {e}")
        finally:
            conn.close()
    return transactions


def fetch_monthly_summary(month, profile):
    conn = get_db_connection()
    monthly_summary = []
    if conn:
        try:
            c = conn.cursor()
            if profile == 'All Profiles':
                c.execute(
                    'SELECT name, SUM(dolar) as total_dolar, SUM(euro) as total_euro, SUM(zl) as total_zl FROM transactions WHERE EXTRACT(MONTH FROM date::DATE) = %s GROUP BY name',
                    (month,))
            else:
                c.execute(
                    'SELECT name, SUM(dolar) as total_dolar, SUM(euro) as total_euro, SUM(zl) as total_zl FROM transactions WHERE EXTRACT(MONTH FROM date::DATE) = %s AND name = %s GROUP BY name',
                    (month, profile))
            monthly_summary = c.fetchall()
            c.close()
        except psycopg2.Error as e:
            st.error(f"An error occurred while fetching monthly summary: {e}")
        finally:
            conn.close()
    return monthly_summary


def fetch_yearly_summary(year, profile):
    conn = get_db_connection()
    yearly_summary = []
    if conn:
        try:
            c = conn.cursor()
            if profile == 'All Profiles':
                c.execute(
                    'SELECT name, SUM(dolar) as total_dolar, SUM(euro) as total_euro, SUM(zl) as total_zl FROM transactions WHERE EXTRACT(YEAR FROM date::DATE) = %s GROUP BY name',
                    (year,))
            else:
                c.execute(
                    'SELECT name, SUM(dolar) as total_dolar, SUM(euro) as total_euro, SUM(zl) as total_zl FROM transactions WHERE EXTRACT(YEAR FROM date::DATE) = %s AND name = %s GROUP BY name',
                    (year, profile))
            yearly_summary = c.fetchall()
            c.close()
        except psycopg2.Error as e:
            st.error(f"An error occurred while fetching yearly summary: {e}")
        finally:
            conn.close()
    return yearly_summary


def run_streamlit():
    if len(sys.argv) == 1:
        subprocess.run([sys.executable, "-m", "streamlit", "run", sys.argv[0], '--server.port=8501'])


if __name__ == '__main__':
    setup_database()
    # run_streamlit()

st.title("Accounting Program")

uploaded_file = st.file_uploader("Upload Excel file with Date, Name, Dolar, Euro, ZL", type="xlsx")

if uploaded_file:
    try:
        daily_data = pd.read_excel(uploaded_file)
        daily_data['Date'] = pd.to_datetime(daily_data['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')

        for index, row in daily_data.iterrows():
            date, name = row['Date'], row['Name']
            dolar, euro, zl = row['Dolar'], row['Euro'], row['ZL']
            insert_transaction(date, name, dolar, euro, zl)
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
        df_transactions = pd.DataFrame(transactions, columns=["Date", "Name", "Dolar", "Euro", "ZL"])
        st.subheader(
            f"Transactions for {selected_profile} on {'All Dates' if all_dates else selected_date.strftime('%d.%m.%Y')}")
        st.write(df_transactions)
    except Exception as e:
        st.error(f"An error occurred: {e}")

st.header("Monthly Summary")
current_month = selected_date.strftime('%m')
try:
    monthly_summary = fetch_monthly_summary(current_month, selected_profile)
    df_monthly_summary = pd.DataFrame(monthly_summary, columns=["Name", "Total Dolar", "Total Euro", "Total ZL"])
    st.write(df_monthly_summary)

    monthly_total_dolar = df_monthly_summary['Total Dolar'].sum()
    monthly_total_euro = df_monthly_summary['Total Euro'].sum()
    monthly_total_zl = df_monthly_summary['Total ZL'].sum()
    st.write(
        f"Monthly Total for {selected_profile}: Dolar: {monthly_total_dolar}, Euro: {monthly_total_euro}, ZL: {monthly_total_zl}")
except Exception as e:
    st.error(f"An error occurred: {e}")

st.header("Yearly Summary")
current_year = selected_date.strftime('%Y')
try:
    yearly_summary = fetch_yearly_summary(current_year, selected_profile)
    df_yearly_summary = pd.DataFrame(yearly_summary, columns=["Name", "Total Dolar", "Total Euro", "Total ZL"])
    st.write(df_yearly_summary)

    yearly_total_dolar = df_yearly_summary['Total Dolar'].sum()
    yearly_total_euro = df_yearly_summary['Total Euro'].sum()
    yearly_total_zl = df_yearly_summary['Total ZL'].sum()
    st.write(
        f"Yearly Total for {selected_profile}--> Dolar: {yearly_total_dolar}, Euro: {yearly_total_euro}, ZL: {yearly_total_zl}")
except Exception as e:
    st.error(f"An error occurred: {e}")
