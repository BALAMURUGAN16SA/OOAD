import random
import datetime
import mysql.connector

# Connect to MySQL database
conn = mysql.connector.connect(
    host="localhost",           # Replace with your host
    user="root",       # Replace with your MySQL username
    password="",   # Replace with your MySQL password
    database="OOADP"    # Replace with your database name
)

cursor = conn.cursor()

# Define locations and distances (real distances in km)
location_distances = {
    ("CHENNAI", "USA"): 14400,
    ("CHENNAI", "UK"): 8000,
    ("CHENNAI", "FRANCE"): 8200,
    ("CHENNAI", "GERMANY"): 9500,
    ("CHENNAI", "RUSSIA"): 9900,
    ("MUMBAI", "USA"): 14100,
    ("MUMBAI", "UK"): 7200,
    ("MUMBAI", "FRANCE"): 7500,
    ("MUMBAI", "GERMANY"): 8500,
    ("MUMBAI", "RUSSIA"): 9300,
    ("DELHI", "USA"): 12900,
    ("DELHI", "UK"): 6700,
    ("DELHI", "FRANCE"): 7000,
    ("DELHI", "GERMANY"): 8000,
    ("DELHI", "RUSSIA"): 7300,
    ("KOLKATA", "USA"): 12900,
    ("KOLKATA", "UK"): 7000,
    ("KOLKATA", "FRANCE"): 7200,
    ("KOLKATA", "GERMANY"): 8000,
    ("KOLKATA", "RUSSIA"): 7600,
    ("BANGALORE", "USA"): 13900,
    ("BANGALORE", "UK"): 7500,
    ("BANGALORE", "FRANCE"): 7800,
    ("BANGALORE", "GERMANY"): 8600,
    ("BANGALORE", "RUSSIA"): 8900
}

vehicle_types = ["CARGO", "SHIP"]

# Generate random date in a range (for 2024)
def random_date():
    start_date = datetime.date(2024, 11, 16)
    end_date = datetime.date(2024, 11, 20)
    return start_date + datetime.timedelta(days=random.randint(0, (end_date - start_date).days))

# Calculate end date based on vehicle type
def calculate_end_date(start_date, vehicle_type):
    if vehicle_type == "CARGO":
        return start_date + datetime.timedelta(days=2)  # Cargo flight takes 2 days
    elif vehicle_type == "SHIP":
        return start_date + datetime.timedelta(days=random.randint(20, 30))  # Ship takes 20-30 days

# Insert data into the table with real distances
vehicle_id = 1
for (from_loc, to_loc), distance in location_distances.items():
    for vehicle in vehicle_types:
        start_date = random_date()
        end_date = calculate_end_date(start_date, vehicle)
        cursor.execute("""
            INSERT INTO vehicles (FROM_LOCATION, TO_LOCATION, START_DATE, END_DATE, DISTANCE, VEHICLE_TYPE, OCCUPIED)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (from_loc, to_loc, start_date, end_date, distance, vehicle, "NOT OCCUPIED"))
        vehicle_id += 1

# Commit changes and close connection
conn.commit()
print(f"Inserted {cursor.rowcount} rows into the vehicles table.")
cursor.close()
conn.close()
