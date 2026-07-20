import sqlite3

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