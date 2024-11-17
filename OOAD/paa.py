from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import random
from decimal import Decimal
import math
import os

app = Flask(__name__)
no_data = 0

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'OOADP'
}
#RECEIVE GOODS
class Meth:
    def __init__(self, order_id):
        self.order_id = order_id
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ORDERS WHERE order_id = %s", (order_id,))
        self.order = cursor.fetchone()
        self.product_data = ''

    def update(self, order_id):
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        if request.method == 'POST' and self.order['status'] == 'Pending':
            cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Unloaded', order_id,))
            connection.commit()
            return redirect(url_for('order_details', order_id=order_id))
        
        if request.method == 'POST' and self.order['status'] == 'Unloaded':
            cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Assessed', order_id,))
            connection.commit()
            return redirect(url_for('order_details', order_id=order_id))
        
    def data(self, order_id):
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ORDERITEMS WHERE order_id = %s", (order_id,))
        order_items = cursor.fetchall()

        query = """
        SELECT *
        FROM ORDERITEMS oi
        JOIN PRODUCTS p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        """
        cursor.execute(query, (order_id,))
        results = cursor.fetchall()

        query = """
        SELECT p.product_name, p.product_id, p.category, p.price, oi.count AS total_quantity
        FROM ORDERITEMS oi
        JOIN PRODUCTS p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        """
        cursor.execute(query, (order_id,))
        product_data = cursor.fetchall()

        query = """
        SELECT products.category, SUM(orderitems.count) AS total_quantity
        FROM orderitems
        JOIN products ON orderitems.product_id = products.product_id
        GROUP BY products.category;
        """
        
        cursor.execute(query)
        category = cursor.fetchall()  # Fetch the aggregated data

        self.order_items = order_items
        self.results = results
        self.product_data = product_data
        self.category = category

    def graph(self, order_id):
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        fixed_product_types = ['Electronics', 'Clothing', 'Automobile', 'Staple']
        quantities = [0] * 4  # Initialize with zeros for each type

        for item in self.product_data:
            if item['category'] == 'Electronics':
                quantities[0] = item['total_quantity']
            elif item['category'] == 'Clothing':
                quantities[1] = item['total_quantity']
            elif item['category'] == 'Automobile':
                quantities[2] = item['total_quantity']
            elif item['category'] == 'Staple':
                quantities[3] = item['total_quantity']

        graph_url = ''
        if self.order['status'] == 'Unloaded' or self.order['status'] == 'Assessed' or self.order['status'] == 'Approved' or self.order['status'] == 'Disapproved':
            plt.figure(figsize=(8, 6))
            plt.bar(fixed_product_types, quantities)
            plt.xlabel('Product Type')
            plt.ylabel('Quantity')
            plt.title('Quantity of Goods by Product Type')

            img = BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            graph_url = base64.b64encode(img.getvalue()).decode('utf-8')
            img.close()
        self.graph_url = graph_url
        
    def defect(self, order_id):
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute('''
            SELECT COUNT(*) as c
            FROM final_product
            WHERE order_id = %s
        ''', (order_id,))
        count = cursor.fetchone()['c']
        damage_data = []
        ds = 0
        if count == 0:
            if self.order['status'] == 'Assessed' or self.order['status'] == 'Approved' or self.order['status'] == 'Disapproved':
                for product in self.product_data:
                    product_id = product['product_id']
                    product_name = product['product_name']
                    total_quantity = product['total_quantity']
                    total_price = product['total_quantity'] * product['price']
                    damaged_percent = random.randint(5, 11)
                    damaged_quantity = math.ceil(total_quantity * Decimal(damaged_percent) / Decimal(100))  # Convert damaged_percent to Decimal
                    damage_data.append({
                        'product_id' : product_id,
                        'product_name': product_name,
                        'total_quantity': total_quantity,
                        'total_price' : total_price,
                        'damaged_quantity': damaged_quantity,
                        'damaged_percent': round(damaged_percent, 2)
                    })
                    ds += damaged_percent

                for data in damage_data:
                    cursor.execute('''
                        INSERT INTO final_product (order_id, product_id, product_name, total_quantity, total_price, damaged_quantity, damaged_percent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (order_id, data['product_id'], data['product_name'], data['total_quantity'], data['total_price'], data['damaged_quantity'], data['damaged_percent']))

                if ds < 20:
                    cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Approved', order_id,))
                    connection.commit()
                else:
                    cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Disapproved', order_id,))
                    connection.commit()
        else:
            cursor.execute('''
            SELECT order_id, product_name, total_quantity, total_price, damaged_quantity, damaged_percent
            FROM final_product
            WHERE order_id = %s
        ''', (order_id,))
            rows = cursor.fetchall()
            for row in rows:
                damage_data.append({
                    'order_id': row['order_id'],
                    'product_name': row['product_name'],
                    'total_quantity': row['total_quantity'],
                    'total_price' : row['total_price'],
                    'damaged_quantity': row['damaged_quantity'],
                    'damaged_percent': row['damaged_percent']
                })

        self.damage_data = damage_data
        cursor.execute(''' select * from finAL_product join orders on orders.order_id = final_product.product_id;''')
        self.final_product = cursor.fetchall()
@app.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_details(order_id):
    obj = Meth(order_id)
    obj.update(order_id)
    obj.data(order_id)
    obj.graph(order_id)
    obj.defect(order_id)
    return render_template('order_details.html', order=obj.order, order_items=obj.order_items, results=obj.results, graph_url=obj.graph_url, damage_data=obj.damage_data)

#STORE INVENTORY
class BaseInventory:
    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.cursor = db_connection.cursor(dictionary=True)

    def insert_order(self, order):
        raise NotImplementedError("Subclasses must implement this method")

    def get_data(self):
        raise NotImplementedError("Subclasses must implement this method")
class USAInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO USA_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))
    def get_data(self):
        query = "SELECT DISTINCT * FROM USA_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()  
class UKInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO UK_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))
    def get_data(self):
        query = "SELECT DISTINCT * FROM UK_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()
class FranceInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO FRANCE_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM FRANCE_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()   
class GermanyInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO GERMANY_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'],  order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM GERMANY_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall() 
class RussiaInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO RUSSIA_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM RUSSIA_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall() 
class ChennaiInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO CHENNAI_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM CHENNAI_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()
class MumbaiInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO MUMBAI_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM MUMBAI_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()   
class DelhiInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO DELHI_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT  * FROM DELHI_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()  
class KolkataInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO KOLKATA_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))
    def get_data(self):
        query = "SELECT DISTINCT * FROM KOLKATA_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall() 
class BangaloreInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO BANGALORE_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM BANGALORE_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()   
class InventoryManager:
    def __init__(self, db_config):
        self.db_connection = mysql.connector.connect(**db_config)
        self.cursor = self.db_connection.cursor(dictionary=True)

    def fetch_orders(self):
        query = """
        SELECT 
            CUSTOMERS.CUSTOMER_ID, 
            ORDERS.ORDER_ID, 
            ORDERS.FROM_LOCATION, 
            ORDERS.TO_LOCATION, 
            ORDERS.ORDER_DATE, 
            ORDERS.DELIVERY_DATE, 
            FINAL_PRODUCT.PRODUCT_ID, 
            FINAL_PRODUCT.PRODUCT_NAME, 
            FINAL_PRODUCT.TOTAL_QUANTITY,
            FINAL_PRODUCT.DAMAGED_QUANTITY, 
            FINAL_PRODUCT.TOTAL_PRICE AS COST
        FROM CUSTOMERS
        JOIN ORDERS ON CUSTOMERS.CUSTOMER_ID = ORDERS.CUSTOMER_ID
        JOIN FINAL_PRODUCT ON ORDERS.ORDER_ID = FINAL_PRODUCT.ORDER_ID
        WHERE ORDERS.STATUS = 'Approved';
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def insert_into_inventory(self, order):
        # Dynamically choose the correct inventory subclass based on the `TO_LOCATION`
        inventory_classes = {
            'USA': USAInventory,
            'UK': UKInventory,
            'FRANCE': FranceInventory,
            'GERMANY': GermanyInventory,
            'RUSSIA': RussiaInventory,
            'CHENNAI': ChennaiInventory,
            'MUMBAI': MumbaiInventory,
            'DELHI': DelhiInventory,
            'KOLKATA': KolkataInventory,
            'BANGALORE': BangaloreInventory
        }
        
        # Select the correct subclass based on the order's destination (TO_LOCATION)
        inventory_class = inventory_classes.get(order['TO_LOCATION'])
        if inventory_class:
            inventory = inventory_class(self.db_connection)
            inventory.insert_order(order)

    def get_inventory_data(self):
        # Collect data from all inventories (regions)
        inventory_classes = {
            'USA': USAInventory,
            'UK': UKInventory,
            'FRANCE': FranceInventory,
            'GERMANY': GermanyInventory,
            'RUSSIA': RussiaInventory,
            'CHENNAI': ChennaiInventory,
            'MUMBAI': MumbaiInventory,
            'DELHI': DelhiInventory,
            'KOLKATA': KolkataInventory,
            'BANGALORE': BangaloreInventory
        }

        data = {}
        for region, inventory_class in inventory_classes.items():
            inventory = inventory_class(self.db_connection)
            data[region] = inventory.get_data()

        return data

    def commit_changes(self):
        self.db_connection.commit()

    def close_connection(self):
        self.cursor.close()
        self.db_connection.close()
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'OOADP'
    }    
    inventory_manager = InventoryManager(db_config)

    try:
        orders_data = inventory_manager.fetch_orders()
        for order in orders_data:
            inventory_manager.insert_into_inventory(order)
        inventory_manager.commit_changes()
        data = inventory_manager.get_inventory_data()

    finally:
        inventory_manager.close_connection()

    return render_template('inventory.html', data=data)


class InventoryMonitor(Meth):
    def __init__(self, db_config):
        self.db_config = db_config
        inventory_tables = [
            'USA_INV', 'UK_INV', 'FRANCE_INV', 'RUSSIA_INV',
            'GERMANY_INV', 'CHENNAI_INV', 'MUMBAI_INV', 'DELHI_INV',
            'KOLKATA_INV', 'BANGALORE_INV'
        ]

        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT ORDER_ID FROM ORDERS;")
        ids =  cursor.fetchall()
        self.t = []
        self.u = []
        for i in ids:
            order_id = i['ORDER_ID']
            super().__init__(order_id)   
            self.data(order_id)
            self.defect(order_id)
            self.t.append(self.category)    
            self.u.append(self.final_product)       

    def fetch_inventory_data(self):
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        inventory_tables = [
            'USA_INV', 'UK_INV', 'FRANCE_INV', 'RUSSIA_INV',
            'GERMANY_INV', 'CHENNAI_INV', 'MUMBAI_INV', 'DELHI_INV',
            'KOLKATA_INV', 'BANGALORE_INV'
        ]
        inventory_data = {}
        for table in inventory_tables:
            query = f"SELECT SUM(TOTAL_QUANTITY) AS total_quantity FROM {table};"
            cursor.execute(query)
            result = cursor.fetchone()
            total_quantity = result['total_quantity'] if result['total_quantity'] else 0
            inventory_data[table] = total_quantity
        cursor.close()
        connection.close()
        return inventory_data

    def generate_bar_graph(self, inventory_data):
        inventories = list(inventory_data.keys())
        quantities = list(inventory_data.values())
        plt.figure(figsize=(10, 6))
        plt.bar(inventories, quantities, color='skyblue')
        plt.xlabel('Inventory Location')
        plt.ylabel('Total Product Quantity')
        plt.title('Product Quantities in Each Inventory')
        plt.xticks(rotation=45, ha='right')
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf8')
        return plot_url
    
    def plot_inventory_pie(self):
        category_data = self.t[-1]
        categories = [item['category'] for item in category_data]
        quantities = [item['total_quantity'] for item in category_data]
        fig, ax = plt.subplots()
        ax.pie(quantities, labels=categories, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        static_folder = os.path.join(os.getcwd(), 'static')  # Get the path to the static folder
        if not os.path.exists(static_folder):  # Ensure the static folder exists
            os.makedirs(static_folder)
        
        image_path = os.path.join(static_folder, 'inventory_pie_chart.png')  # Full path to save image
        plt.savefig(image_path)
        plt.close()
        return image_path
@app.route('/monitoring', methods=['GET'])
def monitoring():
    monitor = InventoryMonitor(db_config)
    inventory_data = monitor.fetch_inventory_data()
    plot_url = monitor.generate_bar_graph(inventory_data)
    image_path = monitor.plot_inventory_pie()
    return render_template('monitor.html', k = monitor.product_data, plot_url=plot_url, image_path=image_path)


class Shipment():
    def __init__(self, db_config):
        self.db_config = db_config
        self.location_table_map = {
            "CHENNAI": "CHENNAI_INV",
            "MUMBAI": "MUMBAI_INV",
            "DELHI": "DELHI_INV",
            "KOLKATA": "KOLKATA_INV",
            "BANGALORE": "BANGALORE_INV",
            "USA" : "USA_INV",
            "UK" : "UK_INV",
            "FRANCE" : "FRANCE_INV",
            "GERMANY" : "GERMANY_INV",
            "RUSSIA" : "RUSSIA_INV"
        }
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ORDERS")
        orders = cursor.fetchall()
        cursor.close()
        connection.close()
        self.orders = orders

    def fetch(self, floc, tloc, date):
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        table_name = self.location_table_map.get(tloc.upper())
        if not table_name:
            return f"Error: No inventory table found for location '{tloc}'"

        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)

        try:
            query = f"""
                SELECT DISTINCT * 
                FROM {table_name} WHERE FROM_LOCATION = '{floc}'
            """
            cursor.execute(query)
            results = cursor.fetchall()
            return results

        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return []

        finally:
            cursor.close()
            connection.close()

    def veh(self, floc, tloc, date):
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        try:
            query = """
            SELECT *
            FROM vehicles
            WHERE FROM_LOCATION = %s
              AND TO_LOCATION = %s
            """
            cursor.execute(query, (floc, tloc, ))
            return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Error: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

@app.route('/shipping', methods=['GET'])
def shipping():
    ship = Shipment(db_config)
    return render_template('shipping.html', orders=ship.orders)

@app.route('/locaction/<string:floc>/<string:tloc>/<string:date>', methods=['GET'])
def location(floc, tloc, date):
    # Create an instance of Shipment
    ship = Shipment(db_config)
    
    res = ship.fetch(floc, tloc, date)
    vd = ship.veh(floc, tloc, date)
    # Render the template with the results
    return render_template('location.html', res=res, vd = vd)


@app.route('/')
def home():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM ORDERS")
    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('index.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)

