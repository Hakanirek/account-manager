import subprocess
import sys
import streamlit as st
import pandas as pd
import sqlite3
import time


# Function to set up the database
def setup_database():
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            date TEXT,
            name TEXT,
            value REAL,
            UNIQUE(date, name, value) ON CONFLICT IGNORE
        )
        ''')
        c.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            balance REAL
        )
        ''')
        conn.commit()


def insert_transaction(date, name, value):
    retry_count = 5
    while retry_count > 0:
        try:
            with sqlite3.connect('profiles.db', timeout=10) as conn:
                c = conn.cursor()
                c.execute('INSERT INTO transactions (date, name, value) VALUES (?, ?, ?)', (date, name, value))
                c.execute('SELECT balance FROM profiles WHERE name = ?', (name,))
                result = c.fetchone()
                if result:
                    new_balance = result[0] + value
                    c.execute('UPDATE profiles SET balance = ? WHERE name = ?', (new_balance, name))
                else:
                    c.execute('INSERT INTO profiles (name, balance) VALUES (?, ?)', (name, value))
                conn.commit()
            break
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                retry_count -= 1
                time.sleep(1)
            else:
                st.error(f"An error occurred: {e}")
                break


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
                c.execute('SELECT date, name, value FROM transactions')
            else:
                c.execute('SELECT date, name, value FROM transactions WHERE name = ?', (profile,))
        else:
            if profile == 'All Profiles':
                c.execute('SELECT date, name, value FROM transactions WHERE date = ?', (date,))
            else:
                c.execute('SELECT date, name, value FROM transactions WHERE date = ? AND name = ?', (date, profile))
        transactions = c.fetchall()
    return transactions


def fetch_monthly_summary(month, profile):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        if profile == 'All Profiles':
            c.execute('SELECT name, SUM(value) FROM transactions WHERE strftime("%m", date) = ? GROUP BY name',
                      (month,))
        else:
            c.execute(
                'SELECT name, SUM(value) FROM transactions WHERE strftime("%m", date) = ? AND name = ? GROUP BY name',
                (month, profile))
        monthly_summary = c.fetchall()
    return monthly_summary


def fetch_yearly_summary(year, profile):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        if profile == 'All Profiles':
            c.execute('SELECT name, SUM(value) FROM transactions WHERE strftime("%Y", date) = ? GROUP BY name', (year,))
        else:
            c.execute(
                'SELECT name, SUM(value) FROM transactions WHERE strftime("%Y", date) = ? AND name = ? GROUP BY name',
                (year, profile))
        yearly_summary = c.fetchall()
    return yearly_summary


def run_streamlit():
    # Open Streamlit app only once
    if len(sys.argv) == 1:  # Check if script is called without additional arguments
        subprocess.run([sys.executable, "-m", "streamlit", "run", sys.argv[0], '--server.port=8501'])


# Main logic to run Streamlit server only once
if __name__ == '__main__':
    setup_database()  # Set up database if necessary
    run_streamlit()  # Start Streamlit in subprocess

# Streamlit app title
st.title("Accounting Program")

# File uploader for Excel
uploaded_file = st.file_uploader("Upload Excel file with Date, Name, Value", type="xlsx")

if uploaded_file:
    try:
        # Read the uploaded Excel file
        daily_data = pd.read_excel(uploaded_file)
        daily_data['Date'] = pd.to_datetime(daily_data['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')

        # Insert data without checking for duplicates
        for index, row in daily_data.iterrows():
            date, name, value = row['Date'], row['Name'], row['Value']
            insert_transaction(date, name, value)
        st.success('Data uploaded successfully')
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Dropdown for profile selection
profiles = fetch_profiles()
selected_profile = st.selectbox("Select Profile", options=profiles)

# Calendar date input for specific date selection
st.header("Select Date for Transactions")
selected_date = st.date_input("Choose a date", pd.to_datetime("today").date())

# Button for "All Dates" selection
all_dates = st.button("Show All Dates")

if selected_profile:
    try:
        # Fetch transactions based on whether "All Dates" is selected
        transactions = fetch_transactions(selected_date.strftime('%Y-%m-%d'), selected_profile, all_dates)
        df_transactions = pd.DataFrame(transactions, columns=["Date", "Name", "Value"])
        st.subheader(
            f"Transactions for {selected_profile} on {'All Dates' if all_dates else selected_date.strftime('%d.%m.%Y')}")
        st.write(df_transactions)
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Monthly Summary
st.header("Monthly Summary")
current_month = selected_date.strftime('%m')
try:
    monthly_summary = fetch_monthly_summary(current_month, selected_profile)
    df_monthly_summary = pd.DataFrame(monthly_summary, columns=["Name", "Total Value"])
    st.write(df_monthly_summary)

    # Calculate monthly total
    monthly_total = df_monthly_summary['Total Value'].sum()
    st.write(f"Monthly Total for {selected_profile}: {monthly_total}")
except Exception as e:
    st.error(f"An error occurred: {e}")

# Yearly Summary
st.header("Yearly Summary")
current_year = selected_date.strftime('%Y')
try:
    yearly_summary = fetch_yearly_summary(current_year, selected_profile)
    df_yearly_summary = pd.DataFrame(yearly_summary, columns=["Name", "Total Value"])
    st.write(df_yearly_summary)

    # Calculate yearly total
    yearly_total = df_yearly_summary['Total Value'].sum()
    st.write(f"Yearly Total for {selected_profile}: {yearly_total}")
except Exception as e:
    st.error(f"An error occurred: {e}")
