import sqlite3
import random
from datetime import date, timedelta
import requests
import streamlit as st
import pandas as pd
import plotly.express as px


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

def ratesInsert():
    for row in dataAPI:
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
#ID, valuta, importo, data, descrizione
cursor.execute("""
    CREATE TABLE IF NOT EXISTS rates (
        currency TEXT, 
        data TEXT, 
        exchange REAL,
        PRIMARY KEY (currency, data)
    )""")
#valuta, data, tasso

#saving all the DB updates
connection.commit()

descriptionAvailable = ["Supplier invoice", "Client payment", "expense account", 
                        "Deposit agreement", "Assets amortization", "Sale order"]
currencyAvailable = ["USD", "GBP"]
#Adding data to the empty DB
cursor.execute("SELECT COUNT(*) FROM positions")
if (cursor.fetchone()[0] == 0): positionsInsert()

cursor.execute("SELECT MAX(data) FROM rates")
lastDateChange = cursor.fetchone()[0]
if (date.today().isoformat() != lastDateChange):
    response = requests.get("https://api.frankfurter.dev/v2/rates", 
                        params = {"base": "EUR", "quotes": "USD,GBP"})
    dataAPI = response.json()
    ratesInsert()

#streamlit for graphic dashboard representation
st.set_page_config(page_title="FX Exposure Dashboard", page_icon="💱", layout="wide")
st.title("FX Exposure Dashboard")
st.space("xsmall")
ce = currencyExposure()
de = descriptionExposure()
eqv = equivalentValue()

graph = px.bar(eqv, x="currency", y="EUR_value", title="Exposure in EUR for currency")
graph.update_traces(width = 0.3)
graph.update_layout(bargap = 0.7)
col1, col2 = st.columns(2)
col1.plotly_chart(graph)
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