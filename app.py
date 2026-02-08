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

# ---------------- HELPERS ----------------
def now_str():
    return datetime.now().strftime("%d-%m-%Y %I:%M %p")

def next_system_no():
    c.execute("SELECT MAX(system_no) FROM systems")
    m = c.fetchone()[0]
    return 2000 if m is None else m + 1

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
        col4.metric(
            "Last Update",
            log.iloc[-1]["date_time"] if not log.empty else "-"
        )

        def style_row(row):
            if row["quantity"] <= 2:
                return ["background-color:#ff4d4d;color:white;font-weight:bold"] * len(row)
            if row["status"] == "Not Working":
                return ["background-color:#ffcccc"] * len(row)
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

    # ---------- UPDATE ----------
    elif choice == "Update Item":
        st.subheader("🛠️ Update Item")

        sys_no = st.number_input("System No", min_value=2000, step=1)
        c.execute("SELECT * FROM systems WHERE system_no=?", (sys_no,))
        r = c.fetchone()

        if r:
            name = st.text_input("Item Name", r[1])
            qty = st.number_input("Quantity", min_value=0, value=r[2])
            quality = st.selectbox("Quality", ["Good","Average","Poor"], index=["Good","Average","Poor"].index(r[3]))
            status = st.selectbox("Status", ["Working","Not Working"], index=0 if r[4]=="Working" else 1)

            if st.button("Update"):
                c.execute(
                    "UPDATE systems SET name=?, quantity=?, quality=?, status=? WHERE system_no=?",
                    (name, qty, quality, status, sys_no)
                )
                conn.commit()
                st.success("Updated")
                st.rerun()
        else:
            st.info("Item not found")

    # ---------- DELETE ----------
    elif choice == "Delete Item":
        st.subheader("🗑️ Delete Item")

        sys_no = st.number_input("System No", min_value=2000, step=1)
        if st.button("Delete"):
            c.execute("DELETE FROM systems WHERE system_no=?", (sys_no,))
            c.execute(
                "INSERT INTO activity_log(action, system_no, quantity, date_time) VALUES (?,?,?,?)",
                ("DELETE", sys_no, 0, now_str())
            )
            conn.commit()
            st.success("Deleted")
            st.rerun()

    # ---------- COMPLAINT ----------
    elif choice == "Raise Complaint":
        st.subheader("📩 Raise Complaint")

        title = st.text_input("Title")
        desc = st.text_area("Description")

        if st.button("Submit"):
            c.execute("""
                INSERT INTO complaints
                (raised_by, role, title, description, status, date_time)
                VALUES (?,?,?,?,?,?)
            """, (st.session_state.username, role, title, desc, "Open", now_str()))
            conn.commit()
            st.success("Complaint submitted")
            st.rerun()

    elif choice == "Complaints":
        df = pd.read_sql("SELECT * FROM complaints ORDER BY id DESC", conn)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ---------- DEAD STOCK ----------
    elif choice == "Dead Stock":
        st.subheader("📦 Dead Stock")

        df = pd.read_sql("SELECT * FROM systems", conn)
        if not df.empty:
            sys_no = st.selectbox("System No", df["system_no"])
            reason = st.text_input("Reason")

            if st.button("Move to Dead Stock"):
                if role != "HOD":
                    st.error("Only HOD allowed")
                else:
                    name = df[df.system_no==sys_no].iloc[0]["name"]
                    c.execute("""
                        INSERT INTO dead_stock
                        (system_no, name, reason, accepted_by, date_time)
                        VALUES (?,?,?,?,?)
                    """, (sys_no, name, reason, st.session_state.username, now_str()))
                    c.execute("DELETE FROM systems WHERE system_no=?", (sys_no,))
                    conn.commit()
                    st.success("Moved to Dead Stock")
                    st.rerun()

        ds = pd.read_sql("SELECT * FROM dead_stock", conn)
        st.dataframe(ds, use_container_width=True, hide_index=True)

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

    # ---------- EXCEL ----------
    elif choice == "Excel Upload / Download":
        if role != "Admin":
            st.error("Admin only")
            return

        file = st.file_uploader("Upload Excel", type=["xlsx"])
        if file:
            df = pd.read_excel(file)
            df.to_sql("systems", conn, if_exists="replace", index=False)
            st.success("Uploaded")
            st.rerun()

        df = pd.read_sql("SELECT * FROM systems", conn)
        df.to_excel("inventory.xlsx", index=False)
        with open("inventory.xlsx","rb") as f:
            st.download_button("Download Excel", f, "inventory.xlsx")

# ---------------- RUN ----------------
if not st.session_state.logged_in:
    login()
else:
    main_app()
