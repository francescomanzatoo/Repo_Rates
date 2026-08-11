import sqlite3
import random
from datetime import date, timedelta
import requests
import streamlit as st
import pandas as pd
import plotly.express as px

#insertion of random amount per currency just for the simulation
def positionsInsert():
    for i in range(15):
        amount = random.randint(5, 250) * 1000
        currency = random.choice(currencyAvailable)
        data = date.today() - timedelta(days = random.randint(5, 120))
        description = random.choice(descriptionAvailable)

        cursor.execute("""INSERT INTO positions 
                    (currency, amount, data, description) 
                    VALUES (?, ?, ?, ?)""", 
                    (currency, amount, data.isoformat(), description))
    connection.commit()

#Saving all the historical rates for the occurrences in positions
def save_hist_rates():
    cursor.execute("SELECT DISTINCT data FROM positions")
    download_date = cursor.fetchall()
    for row in download_date:
        hist_date = row["data"]
        hist_response = requests.get("https://api.frankfurter.dev/v2/rates",
                                    params = {"base": "EUR", 
                                            "quotes": "USD,GBP", 
                                            "date": hist_date})
        hist_dataAPI = hist_response.json()
        ratesInsert(hist_dataAPI)

#insertion of the rates taken from the Frankfurter API
def ratesInsert(rates_dataAPI):
    for row in rates_dataAPI:
        cursor.execute("""INSERT INTO rates 
                       (currency, data, exchange) 
                       VALUES (?, ?, ?)""", 
                       (row["quote"], row["date"], row["rate"]))
    connection.commit()

#computing of the exposure: for all the currency, sum of all the value
def currencyExposure():
    return pd.read_sql_query("""
        SELECT currency, SUM(amount) AS amount 
        FROM positions 
        GROUP BY currency
        """, connection)
def descriptionExposure():
    return pd.read_sql_query("""
        SELECT currency, SUM(amount) AS amount, description 
        FROM positions 
        GROUP BY currency, description
        """, connection)

#computing of the equivalent value from USD, GBP in EUR
def equivalentValue():
    return pd.read_sql_query("""
        SELECT p.currency, 
        SUM(p.amount) AS currency_amount, 
        ROUND(SUM(p.amount / r.exchange)) AS EUR_value 
        FROM positions AS p 
        JOIN rates AS r 
        ON r.currency = p.currency AND r.data = (SELECT MAX(data) FROM rates) 
        GROUP BY p.currency
        """, connection)

#Comparision between historical and actual exchange rates
def valueComparision():
    return pd.read_sql_query("""
        SELECT p.currency, p.data, p.amount, 
        ROUND(p.amount / r_ins.exchange, 2) AS initial_value, 
        ROUND(p.amount / r_now.exchange, 2) AS actual_value, 
        ROUND(p.amount / r_now.exchange - p.amount / r_ins.exchange, 2) AS pnl
        FROM positions p
        JOIN rates AS r_ins ON r_ins.currency = p.currency
                    AND r_ins.data = p.data
        JOIN rates AS r_now ON r_now.currency = p.currency
                    AND r_now.data = (SELECT MAX(data) FROM rates)
        """, connection)

#definition of the what-if scenario
def what_if(currency, percentage_change):
    cursor.execute("""SELECT exchange FROM rates
                   WHERE currency = ?
                   AND data = (SELECT MAX(data) FROM rates)""", (currency,))
    cacheRate = cursor.fetchone()[0]
    cursor.execute("""SELECT SUM(amount) FROM positions
                   WHERE currency = ?""", (currency,))
    amount = cursor.fetchone()[0]
    ifRate = cacheRate * (1 + percentage_change/100)
    actualValue = amount / cacheRate
    ifEUR_value = amount / ifRate
    deltaVar = ifEUR_value - actualValue
    return amount, actualValue, ifEUR_value, deltaVar

#connection with the database and definition of a cursor to manipulate it
connection = sqlite3.connect("fx_dashboard.db")
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

#creation of the database's tables
cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        ID INTEGER PRIMARY KEY, 
        currency TEXT, 
        amount REAL, 
        data TEXT, 
        description TEXT
    )""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS rates (
        currency TEXT, 
        data TEXT, 
        exchange REAL,
        PRIMARY KEY (currency, data)
    )""")

#saving all the DB updates
connection.commit()
descriptionAvailable = ["Supplier invoice", "Client payment", "expense account", 
                        "Deposit agreement", "Assets amortization", "Sale order"]
currencyAvailable = ["USD", "GBP"]

#Adding data to the empty DB
cursor.execute("SELECT COUNT(*) FROM positions")
if (cursor.fetchone()[0] == 0): 
    positionsInsert()
    save_hist_rates()

#checking if the actual rate in DB is the most updated one
cursor.execute("SELECT MAX(data) FROM rates")
lastDateChange = cursor.fetchone()[0]
if (date.today().isoformat() != lastDateChange):
    response = requests.get("https://api.frankfurter.dev/v2/rates", 
                        params = {"base": "EUR", "quotes": "USD,GBP"})
    dataAPI = response.json()
    ratesInsert(dataAPI)

#streamlit for graphic dashboard representation
st.set_page_config(page_title="FX Exposure Dashboard", page_icon="💱", layout="wide")
st.title("FX Exposure Dashboard")
st.space("xsmall")
ce = currencyExposure()
de = descriptionExposure()
eqv = equivalentValue()
cmp = valueComparision()

graph_eqv = px.bar(eqv, x="currency", y="EUR_value", title="Exposure in EUR for currency")
graph_eqv.update_layout(bargap = 0.7)
pnl_val = cmp.groupby("currency")["pnl"].sum().reset_index()
pnl_val["esito"] = pnl_val["pnl"].apply(lambda x: "Guadagno" if x >= 0 else "Perdita")
graph_cmp = px.bar(pnl_val, x="currency", y="pnl",
                   title="Profit/Loss per currency (EUR)",
                   color="esito",
                   color_discrete_map={"Guadagno": "green", "Perdita": "red"})
graph_cmp.update_layout(bargap = 0.6)
col1, col2 = st.columns(2)
col1.plotly_chart(graph_eqv)
col2.plotly_chart(graph_cmp)

tab1, tab2, tab3 = st.tabs(["Exposure", "Equivalent Value", "What-if"])
with tab1:
    st.subheader("Exposure for currency ")
    st.dataframe(ce)
    st.subheader("Exposure for descriptions ")
    st.dataframe(de)
    st.space("xsmall")
with tab2:
    st.subheader("Equivalent value from EUR to currency ")
    st.dataframe(eqv)
    n = pd.read_sql_query("SELECT COUNT(*) AS n FROM positions", connection)["n"][0]
    col1, col2 = st.columns(2)
    col1.metric("Total EUR value", f"{eqv['EUR_value'].sum():,.2f} EUR")
    col2.metric("Number of positions", n)
    st.space("xsmall")
with tab3:
    st.subheader("What-if scenario")
    sel = st.selectbox("Currency", currencyAvailable)
    pct = st.slider("Rate change in %:", -20.0, 20.0, 0.0)
    amount, actual, simulted, delta = what_if(sel, pct)
    st.metric(f"{amount:,.0f} {sel} correspond to ", f"{simulted:,.2f} EUR", f"{delta:+.2f}")
st.caption(f"Tax rates by BCE taken from Frankfurter API, updated since {lastDateChange}")