from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import random
from decimal import Decimal

app = Flask(__name__)
no_data = 0

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'OOAD'
}

class Meth:
    def __init__(self, order_id):
        self.order_id = order_id
        self.connection = mysql.connector.connect(**db_config)
        self.cursor = self.connection.cursor(dictionary=True)
        self.cursor.execute("SELECT * FROM ORDERS WHERE order_id = %s", (self.order_id,))
        self.order = self.cursor.fetchone()

    def update(self):
        if request.method == 'POST' and self.order['status'] == 'Pending':
            self.cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Unloaded', self.order_id,))
            self.connection.commit()
            return redirect(url_for('order_details', order_id=self.order_id))
        
        if request.method == 'POST' and self.order['status'] == 'Unloaded':
            self.cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Assessed', self.order_id,))
            self.connection.commit()
            return redirect(url_for('order_details', order_id=self.order_id))
        
        if request.method == 'POST' and self.order['status'] == 'Assessed':
            approve_assessment = request.form.get('approve_assessment')
            if approve_assessment == 'yes':
                self.cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Approved', self.order_id,))
            else:
                self.cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Disapproved', self.order_id,))
            self.connection.commit()
            return redirect(url_for('order_details', order_id=self.order_id))
        
    def data(self):
        self.cursor.execute("SELECT * FROM ORDER_ITEMS WHERE order_id = %s", (self.order_id,))
        order_items = self.cursor.fetchall()

        query = """
        SELECT *
        FROM ORDER_ITEMS oi
        JOIN PRODUCTS p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        GROUP BY p.product_type;
        """
        self.cursor.execute(query, (self.order_id,))
        results = self.cursor.fetchall()


        query = """
        SELECT p.product_name, p.product_type, SUM(oi.quantity) AS total_quantity
        FROM ORDER_ITEMS oi
        JOIN PRODUCTS p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        GROUP BY p.product_type;
        """
        self.cursor.execute(query, (self.order_id,))
        product_data = self.cursor.fetchall()

        self.order_items = order_items
        self.results = results
        self.product_data = product_data

    def graph(self):
        fixed_product_types = ['Electronics', 'Clothing', 'Automobile', 'Staple']
        quantities = [0] * 4  # Initialize with zeros for each type

        for item in self.product_data:
            if item['product_type'] == 'Electronics':
                quantities[0] = item['total_quantity']
            elif item['product_type'] == 'Clothing':
                quantities[1] = item['total_quantity']
            elif item['product_type'] == 'Automobile':
                quantities[2] = item['total_quantity']
            elif item['product_type'] == 'Staple':
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
        
    def defect(self):
        self.cursor.execute('''
            SELECT COUNT(*) as c
            FROM final_product
            WHERE order_id = %s
        ''', (self.order_id,))
        count = self.cursor.fetchone()['c']
        damage_data = []
        if count == 0:
            if self.order['status'] == 'Assessed' or self.order['status'] == 'Approved' or self.order['status'] == 'Disapproved':
                for product in self.product_data:
                    product_name = product['product_name']
                    total_quantity = product['total_quantity']
                    max_damage = int(total_quantity * Decimal(5))  # Max damage can be 15% of the total quantity
                    damaged_quantity = random.randint(4, max_damage)
                    damaged_percent = (damaged_quantity / total_quantity) * 100

                    damage_data.append({
                        'product_name': product_name,
                        'total_quantity': total_quantity,
                        'damaged_quantity': damaged_quantity,
                        'damaged_percent': round(damaged_percent, 2)
                    })

                # Insert data from damage_data into the final_product table
                for data in damage_data:
                    self.cursor.execute('''
                        INSERT INTO final_product (order_id, product_name, total_quantity, damaged_quantity, damaged_percent)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (self.order_id, data['product_name'], data['total_quantity'], data['damaged_quantity'], data['damaged_percent']))
                self.connection.commit()
        else:
            self.cursor.execute('''
            SELECT order_id, product_name, total_quantity, damaged_quantity, damaged_percent
            FROM final_product
            WHERE order_id = %s
        ''', (self.order_id,))
            rows = self.cursor.fetchall()
            for row in rows:
                damage_data.append({
                    'order_id': row['order_id'],
                    'product_name': row['product_name'],
                    'total_quantity': row['total_quantity'],
                    'damaged_quantity': row['damaged_quantity'],
                    'damaged_percent': row['damaged_percent']
                })
        self.damage_data = damage_data

@app.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_details(order_id):
    obj = Meth(order_id)
    obj.update()
    obj.data()
    obj.graph()
    obj.defect()
    return render_template('order_details.html', order=obj.order, order_items=obj.order_items, results=obj.results, graph_url=obj.graph_url, damage_data=obj.damage_data)

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
