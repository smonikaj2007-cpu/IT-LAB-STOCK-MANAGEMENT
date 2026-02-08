import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="IT Lab Stock Management", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("inventory.db", check_same_thread=False)
c = conn.cursor()

# ---------------- TABLES ----------------
c.execute("""
CREATE TABLE IF NOT EXISTS systems (
    system_no INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    quantity INTEGER,
    quality TEXT,
    status TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS dead_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system_no INTEGER,
    name TEXT,
    reason TEXT,
    accepted_by TEXT,
    date_time TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raised_by TEXT,
    role TEXT,
    title TEXT,
    description TEXT,
    status TEXT,
    date_time TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT,
    system_no INTEGER,
    quantity INTEGER,
    date_time TEXT
)
""")

conn.commit()

# ---------------- HELPERS ----------------
def now_str():
    return datetime.now().strftime("%d-%m-%Y %I:%M %p")

def next_system_no():
    c.execute("SELECT MAX(system_no) FROM systems")
    m = c.fetchone()[0]
    return 2000 if m is None else m + 1

# ---------------- DEFAULT USERS ----------------
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    users = [
        ("admin", "admin123", "Admin"),
        ("hod", "hod123", "HOD"),
        ("principal", "principal123", "Principal")
    ]
    c.executemany("INSERT INTO users VALUES (?,?,?)", users)
    conn.commit()

# ---------------- DEFAULT ITEMS ----------------
c.execute("SELECT COUNT(*) FROM systems")
if c.fetchone()[0] == 0:
    default_items = [
        (2000, "Monitor", 10, "Good", "Working"),
        (2001, "Mouse", 5, "Average", "Working"),
        (2002, "Keyboard", 1, "Poor", "Not Working"),
        (2003, "CPU", 3, "Good", "Working"),
        (2004, "UPS", 2, "Average", "Working")
    ]

    c.executemany("INSERT INTO systems VALUES (?,?,?,?,?)", default_items)

    for item in default_items:
        c.execute(
            "INSERT INTO activity_log(action, system_no, quantity, date_time) VALUES (?,?,?,?)",
            ("ADD", item[0], item[2], now_str())
        )

    conn.commit()

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 Login")
    st.caption(now_str())

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, p))
        r = c.fetchone()
        if r:
            st.session_state.logged_in = True
            st.session_state.role = r[0]
            st.session_state.username = u
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------------- MAIN APP ----------------
def main_app():
    st.title("🧾 IT Lab Stock Management System")
    st.caption(f"{now_str()} | {st.session_state.username} ({st.session_state.role})")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

    role = st.session_state.role

    if role == "Admin":
        menu = [
            "Register of Items",
            "Add Item",
            "Update Item",
            "Delete Item",
            "Complaints",
            "Dead Stock",
            "Reports",
            "Excel Upload / Download"
        ]
    else:
        menu = [
            "Register of Items",
            "Raise Complaint",
            "Dead Stock",
            "Reports"
        ]

    choice = st.sidebar.selectbox("Menu", menu)

    # ---------- REGISTER ----------
    if choice == "Register of Items":
        st.subheader("📒 Register of Items")

        df = pd.read_sql(
            "SELECT * FROM systems WHERE quantity > 0 ORDER BY system_no",
            conn
        )

        log = pd.read_sql("SELECT * FROM activity_log", conn)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Items", len(df))
        col2.metric("Total Quantity", int(df["quantity"].sum()) if not df.empty else 0)
        col3.metric("Total Added", log[log.action=="ADD"]["quantity"].sum())
        col4.metric("Last Update", log.iloc[-1]["date_time"] if not log.empty else "-")

        def style_row(row):
            if row["quantity"] <= 2:
                return ["background-color:#ff4d4d;color:white;font-weight:bold"] * len(row)
            if row["status"] == "Not Working":
                return ["background-color:#ffd6d6"] * len(row)
            if row["quality"] == "Poor":
                return ["background-color:#fff2cc"] * len(row)
            return [""] * len(row)

        st.dataframe(
            df.style.apply(style_row, axis=1),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("🕒 Activity History")
        hist = pd.read_sql("SELECT * FROM activity_log ORDER BY id DESC", conn)
        st.dataframe(hist, use_container_width=True, hide_index=True)

    # ---------- ADD ----------
    elif choice == "Add Item":
        st.subheader("➕ Add Item")

        sys_no = next_system_no()
        st.info(f"System No: {sys_no}")

        name = st.text_input("Item Name")
        qty = st.number_input("Quantity", min_value=0, step=1)
        quality = st.selectbox("Quality", ["Good", "Average", "Poor"])
        status = st.selectbox("Status", ["Working", "Not Working"])

        if st.button("Add"):
            c.execute(
                "INSERT INTO systems VALUES (?,?,?,?,?)",
                (sys_no, name, qty, quality, status)
            )
            c.execute(
                "INSERT INTO activity_log(action, system_no, quantity, date_time) VALUES (?,?,?,?)",
                ("ADD", sys_no, qty, now_str())
            )
            conn.commit()
            st.success("Item added")
            st.rerun()

    # ---------- REPORTS ----------
    elif choice == "Reports":
        st.subheader("📊 Reports")

        df = pd.read_sql("SELECT * FROM systems WHERE quantity > 0", conn)
        if not df.empty:
            st.bar_chart(df.set_index("name")["quantity"])

            fig, ax = plt.subplots()
            ax.pie(
                df["status"].value_counts(),
                labels=df["status"].value_counts().index,
                autopct="%1.1f%%"
            )
            st.pyplot(fig)

# ---------------- RUN ----------------
if not st.session_state.logged_in:
    login()
else:
    main_app()
