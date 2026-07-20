import sqlite3
import random
from datetime import date, timedelta
import requests
import json


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
    



#connection with the database and definition of a cursor to manipulate it
connection = sqlite3.connect("fx_dashboard.db")
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
connection.commit()

descriptionAvailable = ["fattura fornitore", "Pagamento cliente", "Rimborso spese", 
                        "Accorto contratto", "Ammortamento immobilizzazioni", "Saldo ordine"]
currencyAvailable = ["USD", "GBP"]
positionsInsert()

#cursor.execute("SELECT * FROM positions")
#rows = cursor.fetchall()
#for row in rows:
#   print(row)
cursor.execute("SELECT MAX(data) FROM rates")
lastDateChange = cursor.fetchone()[0]
if (date.today().isoformat() != lastDateChange):
    response = requests.get("https://api.frankfurter.dev/v2/rates", 
                        params = {"base": "EUR", "quotes": "USD,GBP"})
    dataAPI = response.json()
    ratesInsert()
else: print("Exchange rate has not changed from [" + lastDateChange + "]")

cursor.execute("SELECT * FROM rates")
rows = cursor.fetchall()
for row in rows:
   print(row)