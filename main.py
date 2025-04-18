import re
import streamlit as st
import pandas as pd
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
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

##################### LOGIN SISTEMI#############

KULLANICI_LISTESI = {
    "User1": "pass1",
    "User2": "pass2",
    "User3": "pass3"
}
YONETICI_MAIL = "autonicaide@gmail.com"  # Burada bildirilecek mail adresini yaz
MAIL_GONDER = True  # Test için False bırakabilirsiniz


def login_kontrol():
    if "user" not in st.session_state or not st.session_state["user"]:
        st.session_state["user"] = None
    if st.session_state["user"] is None:
        st.title("Giriş Paneli")
        kullanici = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            if kullanici in KULLANICI_LISTESI and KULLANICI_LISTESI[kullanici] == sifre:
                st.session_state["user"] = kullanici
                st.success(f"Hoş geldin, {kullanici}")
                st.rerun()

            else:
                st.error("Hatalı giriş!")
        st.stop()
    else:
        st.sidebar.success(f"Giriş yapan: {st.session_state['user']}  [Çıkış için tıklayın]")
        if st.sidebar.button("Çıkış Yap"):
            st.session_state["user"] = None


##### MAIL ##########

def send_change_mail(kullanici, islemtipi, detay):
    if not MAIL_GONDER:
        return
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "autonicaide@gmail.com"
        app_password = "hzle cpph yexl oglb"

        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        subject = f"Veri Değişikliği Bildirimi - {kullanici}"
        content = f"""Aşağıdaki işlem yapıldı:
        Kullanıcı: {kullanici}
        İşlem türü: {islemtipi}
        Detay: {detay}
        Tarih/Saat: {now}"""

        msg = MIMEText(content)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = YONETICI_MAIL

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, YONETICI_MAIL, msg.as_string())
    except Exception as e:
        st.warning(f"Mail gönderilemedi: {e}")


# Conversion rates placeholders
CONVERSION_RATE_DOLAR = 1.0  # Placeholder conversion rate for dollars
CONVERSION_RATE_EURO = 1.0  # Placeholder conversion rate for euros

# Initialize session state variables
for key in ['filter_option', 'all_dates']:
    if key not in st.session_state:
        st.session_state[key] = None


def process_currency_value(value):
    """Determine numeric values based on currency identifiers."""
    dolar_value = convert_value(value) if 'Y' in str(value) else 0
    euro_value = convert_value(value) if 'M' in str(value) else 0
    return dolar_value, euro_value


def setup_database():
    """Setup the SQLite database and required tables if not already present."""
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
            tl REAL,
            aciklama TEXT
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
                        dolar REAL,
                        euro REAL,
                        commission_dolar REAL,
                        commission_euro REAL
                    )
                ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            arac TEXT,
            tir_plaka TEXT,
            ict REAL,
            mer REAL,
            blg REAL,
            suat REAL,
            komsu REAL,
            islem REAL,
            islem_r REAL,
            kapı_m REAL,
            hamal REAL,
            sofor_ve_ekstr REAL,
            indirme_pln REAL,
            bus REAL,
            mazot REAL,
            sakal_yol REAL,
            ek_masraf REAL,
            aciklama REAL,
            toplam_y REAL,
            toplam_m REAL
        )
        ''')

        c.execute('''
                    CREATE TABLE IF NOT EXISTS customers (
                        m_no INTEGER PRIMARY KEY,
                        isim TEXT,
                        sehir TEXT,
                        cep_tel TEXT,
                        is_tel TEXT,
                        firma TEXT,
                        tel TEXT
                    )
                ''')

        conn.commit()


def convert_value(value_str):
    """Convert a string value to a numerical value."""
    try:
        if pd.isna(value_str):
            return 0.0
        numeric_part = re.findall(r'\d+\.?\d*', str(value_str))
        if numeric_part:
            return float(numeric_part[0])
        else:
            return 0.0
    except ValueError:
        return 0.0


def insert_transaction(date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl, aciklama):
    """Insert transaction data into transactions table with retry logic."""
    retry_count = 5
    while retry_count > 0:
        try:
            with sqlite3.connect('profiles.db', timeout=10) as conn:
                c = conn.cursor()

                # Ensure all values are checked for None and replaced appropriately
                name = name or ''
                vehicle = vehicle or ''
                kap_number = kap_number or ''
                unit_kg = unit_kg or 0.0
                price = price or 0.0
                dolar = dolar or 0.0
                euro = euro or 0.0
                zl = zl or 0.0
                tl = tl or 0.0
                aciklama = aciklama or ''

                c.execute('SELECT COUNT(*) FROM transactions WHERE date = ? AND name = ? AND vehicle = ?',
                          (date, name, vehicle))
                count = c.fetchone()[0]
                if count == 0:
                    c.execute('''
                    INSERT INTO transactions (date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl, aciklama)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl, aciklama))

                # Balance updating
                c.execute('SELECT balance_dolar, balance_euro, balance_zl, balance_tl FROM profiles WHERE name = ?',
                          (name,))
                result = c.fetchone()
                if result:
                    new_balance_dolar = (result[0] or 0.0) + dolar
                    new_balance_euro = (result[1] or 0.0) + euro
                    new_balance_zl = (result[2] or 0.0) + zl
                    new_balance_tl = (result[3] or 0.0) + tl
                    c.execute(
                        'UPDATE profiles SET balance_dolar = ?, balance_euro = ?, balance_zl = ?, balance_tl = ? WHERE name = ?',
                        (new_balance_dolar, new_balance_euro, new_balance_zl, new_balance_tl, name))
                else:
                    c.execute(
                        'INSERT INTO profiles (name, balance_dolar, balance_euro, balance_zl, balance_tl) VALUES (?, ?, ?, ?, ?)',
                        (name, dolar, euro, zl, tl))
                conn.commit()

            kullanici = st.session_state.get("user", "Bilinmiyor")
            detay = f"Transaction Ekleme: {name}"
            send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)

            break
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                retry_count -= 1
                time.sleep(1)
            else:
                st.error(f"An error occurred: {e}")
                break


def insert_outcome(date, arac, tir_plaka, ict, mer, blg, suat, komsu, islem, islem_r, kapı_m, hamal,
                   sofor_ve_ekstr, indirme_pln, bus, mazot, sakal_yol, ek_masraf, aciklama):
    """Insert data into outcomes table."""
    try:
        # Convert potential inputs to expected types, with default fallback
        values_y = [ict, mer, blg, suat, komsu, islem, islem_r, hamal, sofor_ve_ekstr, indirme_pln, bus, mazot,
                    sakal_yol, ek_masraf, kapı_m, aciklama]
        values_m = [ict, mer, blg, suat, komsu, islem, islem_r, hamal, sofor_ve_ekstr, indirme_pln, bus, mazot,
                    sakal_yol, ek_masraf, kapı_m, aciklama]

        toplam_y = sum(convert_value(value) for value in values_y if 'Y' in str(value))
        toplam_m = sum(convert_value(value) for value in values_m if 'M' in str(value))

        with sqlite3.connect('profiles.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM outcomes WHERE date = ? AND arac = ? AND tir_plaka = ?',
                      (date, arac, tir_plaka))
            count = c.fetchone()[0]

            if count == 0:
                c.execute(
                    'INSERT INTO outcomes (date, arac, tir_plaka, ict, mer, blg, suat, komsu, islem, islem_r, kapı_m, hamal, sofor_ve_ekstr, indirme_pln, bus, mazot, sakal_yol, ek_masraf, aciklama, toplam_y, toplam_m) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (date, arac, tir_plaka, ict, mer, blg, suat, komsu, islem, islem_r, kapı_m, hamal, sofor_ve_ekstr,
                     indirme_pln,
                     bus, mazot, sakal_yol, ek_masraf, aciklama, toplam_y, toplam_m))
                conn.commit()

        kullanici = st.session_state.get("user", "Bilinmiyor")
        detay = f"Eklenen Gider: {arac}, tir_plaka: {tir_plaka}"
        send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)
    except Exception as e:
        st.error(f"An error occurred while inserting outcomes: {e}")


def insert_transfer(date, name, dolar, euro, commission_dolar, commission_euro):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO transfers (date, name, dolar, euro, commission_dolar, commission_euro)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, name, dolar, euro, commission_dolar, commission_euro))
        conn.commit()


    kullanici = st.session_state.get("user", "Bilinmiyor")
    detay = f"Transfer Eklendi: {name}, transfer_dolar: {dolar},transfer_euro{euro} "
    send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)


def insert_customer(m_no, isim, sehir, cep_tel, is_tel, firma, tel):
    try:
        with sqlite3.connect('profiles.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO customers (m_no, isim, sehir, cep_tel, is_tel, firma, tel) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (int(m_no), isim, sehir, cep_tel, is_tel, firma, tel))
            conn.commit()

        # Bildirim
        kullanici = st.session_state.get("user", "Bilinmiyor")
        detay = f"Eklenen Müşteri: {isim}, M.NO: {m_no}"
        send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)


    except Exception as e:
        st.error(f"Müşteri eklerken hata oluştu: {e}")


def process_outcomes_individually(outcomes_data):
    """Process each outcome by type, aggregating shared date and vehicle entries."""
    outcome_types = ['ICT', 'MER', 'BLG', 'SUAT', 'KOMSU', 'ISLEM', 'ISLEM R', 'KAPI M', 'Hamal',
                     'SOFOR VE EKSTR.', 'INDIRME PLN', 'BUS', 'MAZOT', 'SAKAL YOL', 'EK MASRAF', 'Açıklama']

    outcome_sums = {}

    # Aggregate values by date, vehicle and outcome type
    for _, row in outcomes_data.iterrows():
        date = row['Date']
        vehicle = row['Araç']

        for outcome_type in outcome_types:
            key = (date, vehicle, outcome_type)
            if key not in outcome_sums:
                outcome_sums[key] = {'dolar': 0, 'euro': 0}

            dolar_value, euro_value = process_currency_value(row[outcome_type])
            outcome_sums[key]['dolar'] += dolar_value
            outcome_sums[key]['euro'] += euro_value

    # Insert aggregated results for each type into transactions table
    for (date, vehicle, outcome_type), values in outcome_sums.items():
        insert_transaction(date, outcome_type, vehicle, "", 0, 0, values['dolar'], values['euro'], 0, 0, "")


def fetch_profiles():
    """Fetch profile names from profiles table."""
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT name FROM profiles')
        profiles = c.fetchall()
    return ['All Profiles'] + [profile[0] for profile in profiles]


def fetch_vehicles():
    """Fetch vehicle names from outcomes table."""
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT DISTINCT arac FROM outcomes')
        vehicles = c.fetchall()
    return ['All Vehicles'] + [vehicle[0] for vehicle in vehicles]


def fetch_transactions(date, profile, all_dates):
    """Fetch transaction data based on selected date and profile."""
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        sql = '''
            SELECT id, date, name,
                ROUND(SUM(unit_kg), 2) as unit_kg, ROUND(SUM(price), 2) as price,
                ROUND(SUM(dolar), 2) as dolar, ROUND(SUM(euro), 2) as euro, ROUND(SUM(zl), 2) as zl, ROUND(SUM(tl), 2) as tl,
                TRIM(GROUP_CONCAT(DISTINCT vehicle), ', ') as vehicle, TRIM(GROUP_CONCAT(DISTINCT kap_number), ', ') as kap_number,
                TRIM(GROUP_CONCAT(DISTINCT aciklama), ', ') as aciklama
            FROM transactions
        '''

        where_clause = []
        params = []

        if not all_dates:
            where_clause.append('date = ?')
            params.append(date)

        if profile != 'All Profiles':
            where_clause.append('name = ?')
            params.append(profile)

        if where_clause:
            sql += f" WHERE {' AND '.join(where_clause)}"

        sql += ' GROUP BY date, name'

        c.execute(sql, params)
        transactions = c.fetchall()
    return transactions


def fetch_transfers(name_filter=None):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        sql = 'SELECT id, date, name, dolar, euro, commission_dolar, commission_euro FROM transfers'
        params = []
        if name_filter:
            sql += ' WHERE LOWER(name) LIKE ?'
            params.append(f'%{name_filter.lower()}%')
        c.execute(sql, params)
        transfers = c.fetchall()
    return transfers


def fetch_outcomes(date, vehicle, all_dates):
    """Fetch outcomes data based on selected date and vehicle."""
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()

        sql = '''
            SELECT DISTINCT id, date, arac, tir_plaka, ict, mer, blg, suat, komsu, islem, islem_r, kapı_m, hamal, sofor_ve_ekstr, indirme_pln, bus, mazot, sakal_yol, ek_masraf, aciklama, toplam_y, toplam_m
            FROM outcomes
        '''

        if all_dates:
            if vehicle != 'All Vehicles':
                sql += ' WHERE arac = ?'
                c.execute(sql, (vehicle,))
            else:
                c.execute(sql)
        else:
            if vehicle != 'All Vehicles':
                sql += ' WHERE date = ? AND arac = ?'
                c.execute(sql, (date, vehicle))
            else:
                sql += ' WHERE date = ?'
                c.execute(sql, (date,))

        outcomes = c.fetchall()
    return outcomes


def fetch_monthly_summary(month, profile):
    """Fetch monthly summary from transactions table."""
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
    """Fetch yearly summary from transactions table."""
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


def fetch_customers(search_name=None, search_mno=None):
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        sql = 'SELECT m_no, isim, sehir, cep_tel, is_tel, firma, tel FROM customers WHERE 1=1'
        params = []
        if search_name:
            sql += ' AND lower(isim) LIKE ?'
            params.append(f'%{search_name.lower()}%')
        if search_mno:
            sql += ' AND m_no = ?'
            params.append(int(search_mno))
        sql += ' ORDER BY m_no ASC'
        c.execute(sql, params)
        customers = c.fetchall()
    return customers


def upload_transfers_from_excel(file):
    try:
        df = pd.read_excel(file)
        colmap = {
            "DATE": "date",
            "NAME": "name",
            "DOLAR": "dolar",
            "EURO": "euro",
            "COMMISSION_DOLAR": "commission_dolar",
            "COMMISSION_EURO": "commission_euro"
        }
        df.columns = [col.strip().upper() for col in df.columns]
        # Eksik sütun kontrolü
        for required in colmap.keys():
            if required not in df.columns:
                raise Exception(f"Beklenen sütun eksik: {required}")
        for _, row in df.iterrows():
            insert_transfer(
                str(row["DATE"]),
                str(row["NAME"]),
                float(row["DOLAR"]) if pd.notna(row["DOLAR"]) else 0,
                float(row["EURO"]) if pd.notna(row["EURO"]) else 0,
                float(row["COMMISSION_DOLAR"]) if pd.notna(row["COMMISSION_DOLAR"]) else 0,
                float(row["COMMISSION_EURO"]) if pd.notna(row["COMMISSION_EURO"]) else 0,
            )
        st.success("Transferler başarıyla yüklendi!")

        kullanici = st.session_state.get("user", "Bilinmiyor")
        detay = f"Excel'den Eklenen Transfer"
        send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)

    except Exception as e:
        st.error(f"Transfer excel yüklemesi hatası: {e}")


def upload_customers_from_excel(file):
    try:
        df = pd.read_excel(file, dtype=str)
        # Beklenen kolon adları: M.NO, İSİM, ŞEHİR, CEP TEL, İŞ TEL, FIRMA, TEL
        df.columns = [col.strip().upper() for col in df.columns]
        required_columns = ['M.NO', 'İSİM', 'ŞEHİR', 'CEP TEL', 'İŞ TEL', 'FIRMA', 'TEL']
        if not all(col in df.columns for col in required_columns):
            raise Exception("Eksik ya da yanlış sütun adı! Beklenen: " + ", ".join(required_columns))
        for _, row in df.iterrows():
            insert_customer(
                row['M.NO'], row['İSİM'], row['ŞEHİR'],
                row['CEP TEL'], row['İŞ TEL'],
                row['FIRMA'], row['TEL']
            )
        st.success("Excel'den müşteriler başarıyla yüklendi.")

        kullanici = st.session_state.get("user", "Bilinmiyor")
        detay = f"Excel'den Eklenen Müşteri"
        send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)

    except Exception as e:
        st.error(f"Excel yüklenirken hata oluştu: {e}")


def update_transaction(transaction_id, date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl, aciklama):
    """Update transaction data in transactions table."""
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT balance_dolar, balance_euro, balance_zl, balance_tl FROM profiles WHERE name = ?', (name,))
        result = c.fetchone()
        if result:
            c.execute('SELECT dolar, euro, zl, tl FROM transactions WHERE id = ?', (transaction_id,))
            old_values = c.fetchone()
            if old_values:
                old_dolar, old_euro, old_zl, old_tl = old_values
                new_balance_dolar = (result[0] or 0) - old_dolar + dolar
                new_balance_euro = (result[1] or 0) - old_euro + euro
                new_balance_zl = (result[2] or 0) - old_zl + zl
                new_balance_tl = (result[3] or 0) - old_tl + tl
                c.execute(
                    'UPDATE profiles SET balance_dolar = ?, balance_euro = ?, balance_zl = ?, balance_tl = ? WHERE name = ?',
                    (new_balance_dolar, new_balance_euro, new_balance_zl, new_balance_tl, name))

        c.execute('''
        UPDATE transactions
        SET date = ?, name = ?, vehicle = ?, kap_number = ?, unit_kg = ?, price = ?, dolar = ?, euro = ?, zl = ?, tl = ?, aciklama = ?
        WHERE id = ?
        ''', (date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl, aciklama, transaction_id))
        conn.commit()

    kullanici = st.session_state.get("user", "Bilinmiyor")
    detay = f"Transaction Güncelleme : {name}"
    send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)


def update_transfer(transfer_id, date, name, dolar,euro, commission_dolar,commission_euro):
    """Update transfer data in transfers table."""
    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
        UPDATE transfers
        SET date = ?, name = ?, dolar = ?, euro = ?, commission_dolar = ?,commission_euro = ?
        WHERE id = ?
        ''', (date, name, dolar, euro, commission_dolar,commission_euro, transfer_id))
        conn.commit()




    kullanici = st.session_state.get("user", "Bilinmiyor")
    detay = f"Transfer Güncelleme : {name}"
    send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)


def update_outcome(outcome_id, date, arac, tir_plaka, ict, mer, blg, suat, komsu, islem, islem_r, kapı_m, hamal,
                   sofor_ve_ekstr, indirme_pln, bus, mazot, sakal_yol, ek_masraf, aciklama):
    """Update outcome data in outcomes table."""
    values_y = [ict, mer, blg, suat, komsu, islem, islem_r,
                hamal, sofor_ve_ekstr, indirme_pln, bus, mazot, sakal_yol,
                ek_masraf, kapı_m, aciklama]
    values_m = [ict, mer, blg, suat, komsu, islem, islem_r,
                hamal, sofor_ve_ekstr, indirme_pln, bus, mazot, sakal_yol,
                ek_masraf, kapı_m, aciklama]

    toplam_y = sum(convert_value(value) for value in values_y if 'Y' in str(value))
    toplam_m = sum(convert_value(value) for value in values_m if 'M' in str(value))

    with sqlite3.connect('profiles.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
        UPDATE outcomes
        SET date = ?, arac = ?, tir_plaka = ?, ict = ?, mer = ?, blg = ?, suat = ?, komsu = ?, islem = ?, islem_r = ?, kapı_m = ?, hamal = ?, sofor_ve_ekstr = ?, indirme_pln = ?, bus = ?, mazot = ?, sakal_yol = ?, ek_masraf = ?, aciklama = ?, toplam_y = ?, toplam_m = ?
        WHERE id = ?
        ''', (
            date, arac, tir_plaka, ict, mer, blg, suat, komsu, islem, islem_r, kapı_m, hamal, sofor_ve_ekstr,
            indirme_pln, bus, mazot, sakal_yol, ek_masraf, aciklama, toplam_y, toplam_m, outcome_id))
        conn.commit()

    kullanici = st.session_state.get("user", "Bilinmiyor")
    detay = f"Gider Güncelleme : {arac}, tir_plaka: {tir_plaka} "
    send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)


def update_customer(m_no, isim, sehir, cep_tel, is_tel, firma, tel):
    try:
        with sqlite3.connect('profiles.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE customers SET
                  isim = ?,
                  sehir = ?,
                  cep_tel = ?,
                  is_tel = ?,
                  firma = ?,
                  tel = ?
                WHERE m_no = ?
            ''', (isim, sehir, cep_tel, is_tel, firma, tel, int(m_no)))
            conn.commit()

        kullanici = st.session_state.get("user", "Bilinmiyor")
        detay = f"Müşteri Güncellemesi : {isim}, M.NO: {m_no}"
        send_change_mail(kullanici, "Müşteri Kaydı/Güncelleme", detay)

    except Exception as e:
        st.error(f"Müşteri güncellenirken hata oluştu: {e}")


def show_accounting_page():
    login_kontrol()
    """Show the accounting page logic."""
    st.title("Accounting Program")
    st.info("İşlemlerinizi toplu Excel yüklemesi veya manuel olarak ekleyebilirsiniz.\n"
            "Ayrıca ad, tarih ve araca göre arama ve filtreleme yapabilirsiniz.\n"
            "**Beklenen sütunlar:** Date, Name, Dolar, Euro, ZL, T.L, Açıklama "
            "(Başlıklar büyük harf olmalı, tarih GÜN.AY.YIL formatında olmalı)")

    uploaded_file = st.file_uploader("Muhasebe Excel Dosyası (Date, Name, Dolar, Euro, ZL, T.L, Açıklama",
                                     type="xlsx",
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
                aciklama = row.get('Açıklama', '')
                insert_transaction(date, name, '', '', 0, 0, dolar, euro, zl, tl, aciklama)
            st.success('Transaction data uploaded successfully')
        except Exception as e:
            st.error(f"An error occurred: {e}")

    st.info("Gelir ve giderler için Excel yükleyebilirsiniz. \n\n"
            "Gelir sayfası için: **Date, Name, Vehicle, Kap-Number, Unit-Kg, Price, Dolar, Euro, ZL, T.L, Açıklama**\n\n"
            "Gider sayfası için: **Date, Araç, Tır Plaka, ICT, MER, BLG, SUAT, KOMSU, ISLEM, ISLEM R, ...**")

    income_file = st.file_uploader("Upload Income-Outcome Excel file with Income and Outcome sheets", type="xlsx",
                                   key="income")

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
                    aciklama = row.get('Açıklama', '')

                    insert_transaction(date, name, vehicle, kap_number, unit_kg, price, dolar, euro, zl, tl, aciklama)
                st.success('Income data uploaded successfully')

            if 'Outcome' in xls.sheet_names:
                outcome_data = pd.read_excel(xls, sheet_name='Outcome')
                outcome_data['Date'] = pd.to_datetime(outcome_data['Date']).dt.strftime('%Y-%m-%d')

                for _, row in outcome_data.iterrows():
                    date = row['Date']
                    arac = row['Araç']
                    tir_plaka = row['Tır Plaka']
                    ict = row.get('ICT', '0')
                    mer = row.get('MER', '0')
                    blg = row.get('BLG', '0')
                    suat = row.get('SUAT', '0')
                    komsu = row.get('KOMSU', '0')
                    islem = row.get('ISLEM', '0')
                    islem_r = row.get('ISLEM R', '0')
                    kapı_m = row.get('KAPI M', '0')
                    hamal = row.get('Hamal', '0')
                    sofor_ve_ekstr = row.get('SOFOR VE EKSTR.', '0')
                    indirme_pln = row.get('INDIRME PLN', '0')
                    bus = row.get('BUS', '0')
                    mazot = row.get('MAZOT', '0')
                    sakal_yol = row.get('SAKAL YOL', '0')
                    ek_masraf = row.get('EK MASRAF', '0')
                    aciklama = row.get('Açıklama', '0')

                    insert_outcome(date, arac, tir_plaka, ict, mer, blg, suat, komsu, islem, islem_r, kapı_m, hamal,
                                   sofor_ve_ekstr, indirme_pln, bus, mazot, sakal_yol, ek_masraf, aciklama)

                # Process outcomes individually and insert transactions per type
                process_outcomes_individually(outcome_data)

                st.success('Outcome data processed and uploaded successfully')

        except Exception as e:
            st.error(f"An error occurred: {e}")

    profiles = fetch_profiles()
    selected_profile = st.selectbox("Select Profile", options=profiles)

    st.header("Select Date for Transactions")
    selected_date = st.date_input("Choose a date", pd.to_datetime("today").date())

    st.session_state.all_dates = st.checkbox("Show All Dates", value=st.session_state.all_dates)

    if selected_profile:
        try:
            transactions = fetch_transactions(selected_date.strftime('%Y-%m-%d'), selected_profile,
                                              st.session_state.all_dates)
            df_transactions = pd.DataFrame(transactions,
                                           columns=["ID", "Date", "Name", "Unit-Kg", "Price", "Dolar", "Euro", "ZL",
                                                    "T.L", "Vehicle", "Kap-Number", "Açıklama"])
            df_transactions.fillna('', inplace=True)  # Ensure no None values
            st.subheader(
                f"Transactions for {selected_profile} on {'All Dates' if st.session_state.all_dates else selected_date.strftime('%d.%m.%Y')}")
            st.write(df_transactions)

            transaction_total_dolar = round(df_transactions['Dolar'].sum(), 2)
            transaction_total_euro = round(df_transactions['Euro'].sum(), 2)
            transaction_total_zl = round(df_transactions['ZL'].sum(), 2)
            transaction_total_tl = round(df_transactions['T.L'].sum(), 2)
            transaction_total_kg = round(df_transactions['Unit-Kg'].sum(), 2)

            st.write(
                f"Total Transactions: Dolar: {transaction_total_dolar}, Euro: {transaction_total_euro}, ZL: {transaction_total_zl}, T.L: {transaction_total_tl}, KG: {transaction_total_kg}")
        except Exception as e:
            st.error(f"An error occurred: {e}")

    vehicles = fetch_vehicles()
    selected_vehicle = st.selectbox("Select Vehicle", options=vehicles)

    st.header(f"Outcome Data for Selected Date and Vehicle: {selected_vehicle}")
    try:
        selected_date_str = selected_date.strftime('%Y-%m-%d')
        outcomes = fetch_outcomes(selected_date_str, selected_vehicle, st.session_state.all_dates)
        df_outcomes = pd.DataFrame(outcomes,
                                   columns=["ID", "Date", "Araç", "Tır Plaka", "ICT", "MER", "BLG", "SUAT", "KOMSU",
                                            "ISLEM", "ISLEM R", "KAPI M", "Hamal", "SOFOR VE EKSTR.", "INDIRME PLN",
                                            "BUS",
                                            "MAZOT", "SAKAL YOL", "EK MASRAF", "Açıklama", "Total Toplam Y",
                                            "Total Toplam M"])

        filter_columns = ["Show All", "ICT", "MER", "BLG", "SUAT", "KOMSU", "ISLEM", "ISLEM R", "KAPI M", "Hamal",
                          "SOFOR VE EKSTR.", "INDIRME PLN", "BUS", "MAZOT", "SAKAL YOL", "EK MASRAF", "Açıklama",
                          "Total Toplam Y", "Total Toplam M"]
        st.session_state['filter_option'] = st.selectbox("Select a column to filter", options=filter_columns,
                                                         index=filter_columns.index(
                                                             st.session_state['filter_option']) if st.session_state[
                                                             'filter_option'] else 0)

        filter_option = st.session_state['filter_option']

        if filter_option == "Show All":
            st.write(df_outcomes)

            converted_values_y = df_outcomes["Total Toplam Y"].apply(convert_value)
            total_value_y = converted_values_y.sum()
            converted_values_m = df_outcomes["Total Toplam M"].apply(convert_value)
            total_value_m = converted_values_m.sum()

            st.write(f"Total Y: {total_value_y:.2f}")
            st.write(f"Total M: {total_value_m:.2f}")

        elif filter_option in df_outcomes.columns:
            df_filtered = df_outcomes[["Date", "Araç", filter_option]]
            st.write(f"Filtered view: showing only Date, Araç, and {filter_option}")
            st.write(df_filtered)

            occurrences = df_outcomes[filter_option].count()
            # Convert and separate values with "Y" and "M"
            converted_values_y = df_outcomes[filter_option].apply(lambda x: convert_value(x) if 'Y' in str(x) else 0)
            converted_values_m = df_outcomes[filter_option].apply(lambda x: convert_value(x) if 'M' in str(x) else 0)
            total_value_y = converted_values_y.sum()
            total_value_m = converted_values_m.sum()

            st.write(f"Occurrences of {filter_option}: {occurrences}")
            st.write(f"Total {filter_option}: {total_value_y:.2f} Y")
            st.write(f"Total {filter_option}: {total_value_m:.2f} M")

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

        monthly_total_dolar = round(df_monthly_summary['Total Dolar'].sum(), 2)
        monthly_total_euro = round(df_monthly_summary['Total Euro'].sum(), 2)
        monthly_total_zl = round(df_monthly_summary['Total ZL'].sum(), 2)
        monthly_total_tl = round(df_monthly_summary['Total T.L'].sum(), 2)
        monthly_total_kg = round(df_monthly_summary['Total Unit-Kg'].sum(), 2)

        st.write(
            f"Monthly Total for {selected_profile}: Dolar: {monthly_total_dolar}, Euro: {monthly_total_euro}, ZL: {monthly_total_zl}, T.L: {monthly_total_tl}, KG: {monthly_total_kg}")
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

        yearly_total_dolar = round(df_yearly_summary['Total Dolar'].sum(), 2)
        yearly_total_euro = round(df_yearly_summary['Total Euro'].sum(), 2)
        yearly_total_zl = round(df_yearly_summary['Total ZL'].sum(), 2)
        yearly_total_tl = round(df_yearly_summary['Total T.L'].sum(), 2)
        yearly_total_kg = round(df_yearly_summary['Total Unit-Kg'].sum(), 2)

        st.write(
            f"Yearly Total for {selected_profile}: Dolar: {yearly_total_dolar}, Euro: {yearly_total_euro}, ZL: {yearly_total_zl}, T.L: {yearly_total_tl}, KG: {yearly_total_kg}")
    except Exception as e:
        st.error(f"An error occurred: {e}")


def show_transfer_page():
    login_kontrol()

    st.title("Transfer Yönetimi")
    st.info("Transferleri toplu Excel yüklemesiyle veya tek tek manuel olarak ekleyebilirsiniz.\n\n"
            "Beklenen sütunlar: DATE, NAME, DOLAR, EURO, COMMISSION_DOLAR, COMMISSION_EURO (Başlıklar büyük harf olmalı)"
            )

    transfer_option = st.radio("Transfer ekleme yöntemi:", ("Excel ile Ekle", "Manuel Ekle"))
    if transfer_option == "Excel ile Ekle":
        st.subheader("Excel ile Toplu Transfer Ekle")
        st.markdown(":blue[**Beklenen Sütunlar:** DATE, NAME, DOLAR, EURO, COMMISSION_DOLAR, COMMISSION_EURO]")
        transfer_file = st.file_uploader("Excel Yükle", type="xlsx")
        if transfer_file:
            upload_transfers_from_excel(transfer_file)

    elif transfer_option == "Manuel Ekle":
        st.subheader("Manuel Transfer Ekle")
        with st.form("manual_transfer_form"):
            transfer_date = st.date_input("Date", pd.to_datetime("today").date())
            transfer_name = st.text_input("Name")
            transfer_dolar = st.number_input("Dolar", value=0.0, step=0.01)
            transfer_euro = st.number_input("Euro", value=0.0, step=0.01)
            commission_dolar = st.number_input("Komisyon DOLAR", value=0.0, step=0.01)
            commission_euro = st.number_input("Komisyon EURO", value=0.0, step=0.01)
            submit_btn = st.form_submit_button("Transferi Kaydet")
            if submit_btn and transfer_name:
                insert_transfer(
                    transfer_date.strftime('%Y-%m-%d'),
                    transfer_name,
                    transfer_dolar,
                    transfer_euro,
                    commission_dolar,
                    commission_euro
                )
                st.success("Transfer kaydedildi!")

    st.markdown("---")
    st.subheader("Transferler Listesi")

    # Arama Kutusu
    search_name = st.text_input("İsme göre arama (içeren):", key="transfer_name_search")
    transfers = fetch_transfers(name_filter=search_name)

    df_transfers = pd.DataFrame(
        transfers,
        columns=["ID", "Date", "Name", "Dolar", "Euro", "Komisyon Dolar", "Komisyon Euro"]
    )
    st.dataframe(df_transfers)

    # Yearly Summary tarzında aşağıda otomatik toplam: (sadece görüntüde)
    if not df_transfers.empty:
        totals = {
            "Toplam Dolar": df_transfers["Dolar"].sum(),
            "Toplam Euro": df_transfers["Euro"].sum(),
            "Toplam Komisyon Dolar": df_transfers["Komisyon Dolar"].sum(),
            "Toplam Komisyon Euro": df_transfers["Komisyon Euro"].sum(),
        }
        st.markdown("#### Toplamlar (Listedeki kayıtlar için):")
        for k, v in totals.items():
            st.write(f"{k}: {v:.2f}")


def show_edit_page():
    login_kontrol()

    """Show the edit data records page logic."""
    st.title("Edit Data Records")

    edit_option = st.radio("Select Data Type to Edit", ("Transactions", "Transfers", "Outcomes"))

    if edit_option == "Transactions":
        transactions = fetch_transactions(datetime.now().strftime('%Y-%m-%d'), 'All Profiles', True)
        df_transactions = pd.DataFrame(transactions,
                                       columns=["ID", "Date", "Name", "Unit-Kg", "Price", "Dolar", "Euro", "ZL", "T.L",
                                                "Vehicle", "Kap-Number", "Açıklama"])
        st.dataframe(df_transactions)

        if not df_transactions.empty:
            transaction_id = st.selectbox("Select Transaction ID to Edit", df_transactions['ID'].tolist())
            transaction_row = df_transactions[df_transactions['ID'] == transaction_id].iloc[0]

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
                aciklama = st.text_input("Açıklama", value=transaction_row['Açıklama'])
                submit_btn = st.form_submit_button("Update Transaction")

                if submit_btn:
                    update_transaction(transaction_id, date.strftime("%Y-%m-%d"), name, vehicle, kap_number, unit_kg,
                                       price, dolar, euro, zl, tl, aciklama)
                    st.success("Transaction updated successfully")

    elif edit_option == "Transfers":
        transfers = fetch_transfers()
        df_transfers = pd.DataFrame(transfers, columns=["ID", "Date", "Name","Dolar", "Euro","Komisyon Dolar", "Komisyon Euro"])
        st.dataframe(df_transfers)

        if not df_transfers.empty:
            transfer_id = st.selectbox("Düzenlenecek Transfer ID", df_transfers['ID'].tolist())
            transfer_row = df_transfers[df_transfers['ID'] == transfer_id].iloc[0]
            with st.form("edit_transfer_form"):
                date = st.date_input("Tarih", value=pd.to_datetime(transfer_row['Date']))
                name = st.text_input("İsim", value=transfer_row['Name'])
                dolar = st.number_input("Dolar", value=float(transfer_row['Dolar']))
                euro = st.number_input("Euro", value=float(transfer_row['Euro']))
                commission_dolar = st.number_input("Komisyon Dolar", value=float(transfer_row['Komisyon Dolar']))
                commission_euro = st.number_input("Komisyon Euro", value=float(transfer_row['Komisyon Euro']))
                submit_btn = st.form_submit_button("Güncelle")
                if submit_btn:
                    update_transfer(
                        transfer_id,
                        date.strftime("%Y-%m-%d"), name,
                        dolar, euro,
                        commission_dolar, commission_euro
                    )
                    st.success("Transfer güncellendi.")

                    # Listeyi güncelle
                    transfers = fetch_transfers()
                    df_transfers = pd.DataFrame(
                        transfers,
                        columns=[
                            "ID", "Date", "Name",
                            "Dolar", "Euro",
                            "Komisyon Dolar", "Komisyon Euro"
                        ]
                    )
                    st.dataframe(df_transfers)

    elif edit_option == "Outcomes":
        selected_date = st.date_input("Choose a date for Outcomes", pd.to_datetime("today").date())
        st.session_state.all_dates = st.checkbox("Show All Dates", value=st.session_state.all_dates)

        outcomes = fetch_outcomes(selected_date.strftime('%Y-%m-%d'), 'All Vehicles', st.session_state.all_dates)
        df_outcomes = pd.DataFrame(outcomes,
                                   columns=["ID", "Date", "Araç", "Tır Plaka", "ICT", "MER", "BLG", "SUAT", "KOMSU",
                                            "ISLEM", "ISLEM R", "KAPI M", "Hamal", "SOFOR VE EKSTR.", "INDIRME PLN",
                                            "BUS",
                                            "MAZOT", "SAKAL YOL", "EK MASRAF", "Açıklama", "Total Toplam Y",
                                            "Total Toplam M"])
        st.dataframe(df_outcomes)

        if not df_outcomes.empty:
            outcome_id = st.selectbox("Select Outcome ID to Edit", df_outcomes['ID'].tolist())
            outcome_row = df_outcomes[df_outcomes['ID'] == outcome_id].iloc[0]

            form_key = f"edit_outcome_form_{outcome_id}"

            with st.form(form_key):
                date = st.date_input("Date", value=pd.to_datetime(outcome_row['Date']))
                arac = st.text_input("Araç", value=outcome_row['Araç'])
                tir_plaka = st.text_input("Tır Plaka", value=outcome_row['Tır Plaka'])
                ict = st.text_input("ICT", value=str(outcome_row['ICT']))
                mer = st.text_input("MER", value=str(outcome_row['MER']))
                blg = st.text_input("BLG", value=str(outcome_row['BLG']))
                suat = st.text_input("SUAT", value=str(outcome_row['SUAT']))
                komsu = st.text_input("KOMSU", value=str(outcome_row['KOMSU']))
                islem = st.text_input("ISLEM", value=str(outcome_row['ISLEM']))
                islem_r = st.text_input("ISLEM R", value=str(outcome_row['ISLEM R']))
                kapı_m = st.text_input("KAPI M", value=str(outcome_row['KAPI M']))
                hamal = st.text_input("Hamal", value=str(outcome_row['Hamal']))
                sofor_ve_ekstr = st.text_input("SOFOR VE EKSTR.", value=str(outcome_row['SOFOR VE EKSTR.']))
                indirme_pln = st.text_input("INDIRME PLN", value=str(outcome_row['INDIRME PLN']))
                bus = st.text_input("BUS", value=str(outcome_row['BUS']))
                mazot = st.text_input("MAZOT", value=str(outcome_row['MAZOT']))
                sakal_yol = st.text_input("SAKAL YOL", value=str(outcome_row['SAKAL YOL']))
                ek_masraf = st.text_input("EK MASRAF", value=str(outcome_row['EK MASRAF']))
                aciklama = st.text_input("Açıklama", value=str(outcome_row['Açıklama']))
                submit_btn = st.form_submit_button("Update Outcome")

                if submit_btn:
                    update_outcome(outcome_id, date.strftime("%Y-%m-%d"), arac, tir_plaka, ict, mer, blg, suat,
                                   komsu, islem, islem_r, kapı_m, hamal, sofor_ve_ekstr, indirme_pln, bus, mazot,
                                   sakal_yol, ek_masraf, aciklama)
                    st.success("Outcome updated successfully")
                    outcomes = fetch_outcomes(selected_date.strftime('%Y-%m-%d'), 'All Vehicles',
                                              st.session_state.all_dates)
                    df_outcomes = pd.DataFrame(outcomes,
                                               columns=["ID", "Date", "Araç", "Tır Plaka", "ICT", "MER", "BLG", "SUAT",
                                                        "KOMSU", "ISLEM", "ISLEM R", "KAPI M", "Hamal",
                                                        "SOFOR VE EKSTR.",
                                                        "INDIRME PLN", "BUS", "MAZOT", "SAKAL YOL", "EK MASRAF",
                                                        "Açıklama", "Total Toplam Y", "Total Toplam M"])
                    st.dataframe(df_outcomes)
        else:
            st.warning("No outcomes available for selection.")


def show_customers_page():
    login_kontrol()
    st.title("Müşteri Bilgileri Yönetimi")
    st.info(
        "Müşterilerinizi toplu Excel yüklemesiyle veya tek tek manuel olarak ekleyebilirsiniz. "
        "Ek olarak ada ya da M.NO'ya göre arama ve düzenleme yapabilirsiniz.\n\n"
        "Beklenen sütunlar: M.NO, İSİM, ŞEHİR, CEP TEL, İŞ TEL, FIRMA, TEL "
        "(Başlıklar büyük harf ve Türkçe karakterli olmalı)"
    )

    add_mode = st.radio("Müşteri ekleme yöntemi seçin:", ("Excel ile Ekle", "Manuel Ekle"))

    if add_mode == "Excel ile Ekle":
        st.subheader("Excel ile Toplu Müşteri Ekle")
        st.markdown(
            "**Beklenen sütunlar:** `M.NO, İSİM, ŞEHİR, CEP TEL, İŞ TEL, FIRMA, TEL`  (Başlıklar büyük harf ve Türkçe karakterli olmalı)")
        cust_file = st.file_uploader("Müşteri Bilgileri Excel Dosyası (.xlsx)", type='xlsx', key="customer_upload")
        if cust_file:
            upload_customers_from_excel(cust_file)

    elif add_mode == "Manuel Ekle":
        st.subheader("Manuel Müşteri Ekle (veya Güncelle)")
        st.markdown(
            "**Açıklama:** Form ile tek tek müşteri ekleyebilir veya aynı M.NO'yu girerek mevcut müşteriyi güncelleyebilirsiniz.")
        with st.form("manual_customer_form"):
            m_no = st.number_input("Müşteri Numarası (M.NO)", min_value=0, step=1, format="%d")
            isim = st.text_input("İsim")
            sehir = st.text_input("Şehir")
            cep_tel = st.text_input("Cep Tel")
            is_tel = st.text_input("İş Tel")
            firma = st.text_input("Firma")
            tel = st.text_input("Tel")
            submit_btn = st.form_submit_button("Müşteri Ekle veya Güncelle")
            if submit_btn and isim:
                insert_customer(m_no, isim, sehir, cep_tel, is_tel, firma, tel)
                st.success(f"Müşteri kaydı başarıyla eklendi/güncellendi: {isim}")

    st.markdown("---")

    st.subheader("Müşteri Ara")
    st.markdown(
        "İsim veya M.NO ile arama yapabilirsiniz. Sonuç tablosundan müşteriyi seçip düzenlemek için 'Düzenle' butonuna tıklayın.")
    col1, col2 = st.columns(2)
    with col1:
        search_name = st.text_input("İsimde ara", key="cust_name_search")
    with col2:
        search_mno = st.text_input("M.NO ile ara", key="cust_mno_search")
    customers = fetch_customers(search_name=search_name, search_mno=search_mno)
    df_customers = pd.DataFrame(customers, columns=['M.NO', 'İSİM', 'ŞEHİR', 'CEP TEL', 'İŞ TEL', 'FIRMA', 'TEL'])
    st.dataframe(df_customers)

    # DÜZENLEME MODU (tıklandığında göster)
    if not df_customers.empty:
        st.subheader("Müşteri Bilgisi Düzenleme")

        # Formu açmak için state kullanalım:
        if "edit_open" not in st.session_state:
            st.session_state["edit_open"] = False
        if "edit_mno_value" not in st.session_state:
            st.session_state["edit_mno_value"] = None

        edit_mno = st.selectbox("Düzenlenecek M.NO seçin", df_customers['M.NO'].astype(int).tolist(),
                                key="edit_mno_select")
        edit_btn = st.button("Düzenle")

        if edit_btn:
            st.session_state["edit_open"] = True
            st.session_state["edit_mno_value"] = edit_mno

        # Formu sadece buton basıldığında göster
        if st.session_state["edit_open"] and st.session_state["edit_mno_value"] == edit_mno:
            current = df_customers[df_customers['M.NO'] == edit_mno].iloc[0]
            with st.form("edit_customer_form"):
                isim_e = st.text_input("İsim", value=current['İSİM'])
                sehir_e = st.text_input("Şehir", value=current['ŞEHİR'])
                cep_tel_e = st.text_input("Cep Tel", value=current['CEP TEL'])
                is_tel_e = st.text_input("İş Tel", value=current['İŞ TEL'])
                firma_e = st.text_input("Firma", value=current['FIRMA'])
                tel_e = st.text_input("Tel", value=current['TEL'])
                submit_edit = st.form_submit_button("Güncelle")
                if submit_edit:
                    update_customer(edit_mno, isim_e, sehir_e, cep_tel_e, is_tel_e, firma_e, tel_e)
                    st.success(f"Müşteri (M.NO: {edit_mno}) başarıyla güncellendi.")
                    # Güncellemeden sonra formu kapatmak için:
                    st.session_state["edit_open"] = False


setup_database()
page_selection = st.sidebar.selectbox("Select Page", ["Accounting", "Transfer", "Customer", "Edit Data"])

if page_selection == "Accounting":
    show_accounting_page()
elif page_selection == "Transfer":
    show_transfer_page()
elif page_selection == "Customer":
    show_customers_page()
elif page_selection == "Edit Data":
    show_edit_page()
