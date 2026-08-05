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

#computing of the exposure: for all the currency, sum of all the value
def currencyExposure():
    cursor.execute("""SELECT SUM(amount), currency 
                   FROM positions 
                   GROUP BY currency""")
    espTotValue = cursor.fetchall()
    cursor.execute("""SELECT currency, SUM(amount), description 
                   FROM positions 
                   GROUP BY currency, description""")
    espDescValue = cursor.fetchall()
    print("\nTotal esposition for all currency: ")
    for row in espTotValue:
        print(row)
    print("")
    print("Total esposition for all currency and description: ")
    for row in espDescValue:
        print(row)

#computing of the equivalent value from USD, GBP in EUR
def equivalentValue():
    print("")
    cursor.execute("""SELECT p.currency, 
                   SUM(p.amount) AS expVal, 
                   ROUND(SUM(p.amount / r.exchange)) AS eqvVal 
                   FROM positions AS p 
                   JOIN rates AS r 
                   ON r.currency = p.currency AND r.data = (SELECT MAX(data) FROM rates) 
                   GROUP BY p.currency""")
    eqvValue = cursor.fetchall()
    print("Equivalent value for currency in EUR: ")
    for row in eqvValue:
        print(row)

def what_if(currency, percentuale_change):
    print("")
    cursor.execute("""SELECT exchange FROM rates
                   WHERE currency = ?
                   AND data = (SELECT MAX(data) FROM rates)""", (currency,))
    cacheRate = cursor.fetchone()[0]
    cursor.execute("""SELECT SUM(amount) FROM positions
                   WHERE currency = ?""", (currency,))
    amount = cursor.fetchone()[0]
    ifRate = cacheRate * (1 + int(percentuale_change)/100)
    actualValue = amount / cacheRate
    ifEqvVal = amount / ifRate
    deltaVar = ifEqvVal - actualValue
    
    print(f"{currency}: if the rate value changes by {percentuale_change}%,"
          f" the equivalent value goes from {actualValue: .2f} to {ifEqvVal: .2f}."
          f"\nThe variation is: {deltaVar:+.2f}")
    return deltaVar

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

#saving all the DB updates
connection.commit()

descriptionAvailable = ["Supplier invoice", "Client payment", "expense account", 
                        "Deposit agreement", "Assets amortization", "Sale order"]
currencyAvailable = ["USD", "GBP"]
#Adding data to the empty DB
cursor.execute("SELECT COUNT(*) FROM positions")
if (cursor.fetchone()[0] == 0): positionsInsert()
cursor.execute("SELECT * FROM positions")
rows = cursor.fetchall()
for row in rows:
   print(row)

cursor.execute("SELECT MAX(data) FROM rates")
lastDateChange = cursor.fetchone()[0]
if (date.today().isoformat() != lastDateChange):
    response = requests.get("https://api.frankfurter.dev/v2/rates", 
                        params = {"base": "EUR", "quotes": "USD,GBP"})
    dataAPI = response.json()
    ratesInsert()
    print("\nExchange rates has changed:")
else: print("\nExchange rate has not changed from [" + lastDateChange + "]:")

#Showing the most recent date
cursor.execute("""SELECT currency, MAX(data), exchange FROM rates 
                GROUP BY currency""")
rows = cursor.fetchall()
for row in rows:
   print(row)

currencyExposure()
equivalentValue()
ifCurrency = 'USD'
what_if(ifCurrency, 3)