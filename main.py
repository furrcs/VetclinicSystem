from database import Database
from gui import App

def main():
    database = Database(host="localhost", port=5432, dbname="vetclinic", user="postgres", password="1234567890")
    app = App(database)
    app.mainloop()
    database.close()

if __name__ == "__main__": main()