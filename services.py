import hashlib

def authenticate(database, username, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    sql = "SELECT user_id, role FROM Users WHERE username = %s AND password = %s"
    rows = database.query(sql, (username, password_hash))
    return rows[0] if rows else None

def get_all(database, table, order_by="1"):
    return database.query(f"SELECT * FROM {table} ORDER BY {order_by}")

def get_by_id(database, table, id_column, id_value):
    sql = f"SELECT * FROM {table} WHERE {id_column} = %s"
    rows = database.query(sql, (id_value,))
    return rows[0] if rows else None

def insert(database, table, **fields):
    columns = ", ".join(fields.keys())
    placeholders = ", ".join(["%s"] * len(fields))
    values = tuple(fields.values())
    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *"
    return database.insert(sql, values)

def update(database, table, id_column, id_value, **fields):
    set_clause = ", ".join([f"{key} = %s" for key in fields.keys()])
    values = tuple(fields.values()) + (id_value,)
    sql = f"UPDATE {table} SET {set_clause} WHERE {id_column} = %s"
    database.execute(sql, values)

def delete(database, table, id_column, id_value):
    sql = f"DELETE FROM {table} WHERE {id_column} = %s"
    database.execute(sql, (id_value,))

def get_clients(database):
    return database.query("SELECT * FROM Clients ORDER BY surname")

def get_employees(database):
    sql = """
        SELECT Employees.*, Positions.name AS position
        FROM Employees
        JOIN Positions USING(position_id)
        ORDER BY Employees.surname
    """
    return database.query(sql)

def get_pets(database, type_id=None):
    sql = """
        SELECT Pets.*, Breeds.name AS breed, Pet_types.name AS type
        FROM Pets
        JOIN Breeds USING(breed_id)
        JOIN Pet_types ON Breeds.pet_type_id = Pet_types.type_id
    """
    if type_id:
        return database.query(sql + " WHERE Pet_types.type_id = %s ORDER BY Pets.name", (type_id,))
    return database.query(sql + " ORDER BY Pet_types.name, Pets.name")

def get_pets_by_client(database, client_id):
    sql = """
        SELECT Pets.*, Breeds.name AS breed, Client_pets.client_pet_id, Client_pets.is_owner
        FROM Client_pets
        JOIN Pets USING(pet_id)
        JOIN Breeds USING(breed_id)
        WHERE Clients_pets.client_id = %s
    """
    return database.query(sql, (client_id,))

def link_pet_to_client(database, client_id, pet_id):
    sql = "INSERT INTO Client_pets (client_id, pet_id) VALUES (%s, %s) RETURNING client_pet_id"
    return database.insert(sql, (client_id, pet_id))

def unlink_pet_from_client(database, client_pet_id):
    database.execute("DELETE FROM Client_pets WHERE client_pet_id = %s", (client_pet_id,))

def get_users(database):
    sql = """
        SELECT Users.*,
               COALESCE(Employees.surname || ' ' || Employees.name, '') AS employee_name,
               COALESCE(Clients.surname || ' ' || Clients.name, '') AS client_name
        FROM Users
        LEFT JOIN Employees USING(employee_id)
        LEFT JOIN Clients USING(client_id)
        ORDER BY Users.username
    """
    return database.query(sql)

def create_user(database, employee_id, client_id, username, password, role):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    sql = """
        INSERT INTO Users (employee_id, client_id, username, password, role)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING user_id
    """
    return database.insert(sql, (employee_id, client_id, username, password_hash, role))

def get_appointments(database, filter_date=None, filter_status=None):
    sql = """
        SELECT Appointments.*,
               Pets.name AS pet,
               Employees.surname || ' ' || Employees.name AS doctor,
               Clients.surname || ' ' || Clients.name AS client
        FROM Appointments
        JOIN Pets USING(pet_id)
        LEFT JOIN Employees USING(employee_id)
        LEFT JOIN Client_pets USING(pet_id)
        LEFT JOIN Clients USING(client_id)
    """
    conditions = []
    params = []

    if filter_date:
        conditions.append("DATE(Appointments.appointment_date) = %s")
        params.append(filter_date)
    if filter_status:
        conditions.append("Appointments.status = %s")
        params.append(filter_status)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY Appointments.appointment_date DESC"
    return database.query(sql, params if params else None)

def create_appointment(database, pet_id, doctor_id, appointment_date):
    sql = """
        INSERT INTO Appointments (pet_id, employee_id, appointment_date, status)
        VALUES (%s, %s, %s, 'запланирован')
        RETURNING appointment_id
    """
    return database.insert(sql, (pet_id, doctor_id, appointment_date))

def update_appointment_status(database, appointment_id, status):
    database.execute(
        "UPDATE Appointments SET status = %s WHERE appointment_id = %s",
        (status, appointment_id)
    )

def get_appointment_services(database, appointment_id):
    sql = """
        SELECT Appointment_services.*, Services.name AS service_name
        FROM Appointment_services
        JOIN Services USING(service_id)
        WHERE Appointment_services.appointment_id = %s
    """
    return database.query(sql, (appointment_id,))

def add_service_to_appointment(database, appointment_id, service_id, quantity, price):
    sql = """
        INSERT INTO Appointment_services (appointment_id, service_id, quantity, price)
        VALUES (%s, %s, %s, %s)
        RETURNING appointment_service_id
    """
    return database.insert(sql, (appointment_id, service_id, quantity, price))

def get_appointment_items(database, appointment_id):
    sql = """
        SELECT Appointment_items.*, Items.name AS item_name
        FROM Appointment_items
        JOIN Items USING(item_id)
        WHERE Appointment_items.appointment_id = %s
    """
    return database.query(sql, (appointment_id,))

def add_item_to_appointment(database, appointment_id, item_id, quantity, dosage, price):
    sql = """
        INSERT INTO Appointment_items (appointment_id, item_id, quantity, dosage, price)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING appointment_item_id
    """
    return database.insert(sql, (appointment_id, item_id, quantity, dosage, price))

def update_stock(database, item_id, delta):
    database.execute(
        "UPDATE Items SET stock = stock + %s WHERE item_id = %s",
        (delta, item_id)
    )

def get_item_id_by_name(database, name):
    rows = database.query("SELECT item_id FROM Items WHERE name = %s", (name,))
    return rows[0]['item_id'] if rows else None

def get_medical_record(database, appointment_id=None, hospitalization_id=None):
    if appointment_id:
        rows = database.query("SELECT * FROM Medical_records WHERE appointment_id = %s", (appointment_id,))
    elif hospitalization_id:
        rows = database.query("SELECT * FROM Medical_records WHERE hospitalization_id = %s", (hospitalization_id,))
    else:
        return None
    return rows[0] if rows else None

def save_medical_record(database, record_id, appointment_id, hospitalization_id,
                        reason, diagnosis, temperature, weight, recommendations):
    if record_id:
        sql = """
            UPDATE Medical_records
            SET reason = %s, diagnosis = %s, temperature = %s, weight = %s, recommendations = %s
            WHERE record_id = %s
        """
        database.execute(sql, (reason, diagnosis, temperature, weight, recommendations, record_id))
    else:
        sql = """
            INSERT INTO Medical_records (appointment_id, hospitalization_id, reason, diagnosis, temperature, weight, recommendations)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING record_id
        """
        database.insert(sql, (appointment_id, hospitalization_id, reason, diagnosis, temperature, weight, recommendations))

def get_hospitalizations(database):
    sql = """
        SELECT Hospitalizations.*, Pets.name AS pet, Employees.surname || ' ' || Employees.name AS doctor, Ward_rooms.room_number
        FROM Hospitalizations
        JOIN Pets USING(pet_id)
        LEFT JOIN Employees USING(employee_id)
        LEFT JOIN Ward_rooms ON Hospitalizations.ward_room_id = Ward_rooms.room_id
        ORDER BY Hospitalizations.admission_date DESC
    """
    return database.query(sql)


def create_hospitalization(database, pet_id, doctor_id, ward_id, admission_date):
    sql = """
        INSERT INTO Hospitalizations (pet_id, employee_id, ward_room_id, admission_date, status)
        VALUES (%s, %s, %s, %s, 'активна')
        RETURNING hospitalization_id
    """
    hospitalization_id = database.insert(sql, (pet_id, doctor_id, ward_id, admission_date))
    database.execute("UPDATE Ward_rooms SET is_available = FALSE WHERE room_id = %s", (ward_id,))
    return hospitalization_id


def discharge_hospitalization(database, hospitalization_id, discharge_date):
    database.execute(
        "UPDATE Hospitalizations SET discharge_date = %s, status = 'завершена' WHERE hospitalization_id = %s",
        (discharge_date, hospitalization_id)
    )
    database.execute(
        "UPDATE Ward_rooms SET is_available = TRUE WHERE room_id = (SELECT ward_room_id FROM Hospitalizations WHERE hospitalization_id = %s)",
        (hospitalization_id,)
    )


def cancel_hospitalization(database, hospitalization_id):
    database.execute(
        "UPDATE Hospitalizations SET status = 'отменена' WHERE hospitalization_id = %s",
        (hospitalization_id,)
    )
    database.execute(
        "UPDATE Ward_rooms SET is_available = TRUE WHERE room_id = (SELECT ward_room_id FROM Hospitalizations WHERE hospitalization_id = %s)",
        (hospitalization_id,)
    )