import os
import pandas as pd
import xml.etree.ElementTree as ET
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import matplotlib.pyplot as plt

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sales_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Folder to save uploaded files and generated files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

# Check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Dynamic model creation based on CSV columns
def create_table_from_csv(data):
    columns = data.columns.tolist()
    column_definitions = {col: db.Column(db.String) for col in columns}
    column_definitions['id'] = db.Column(db.Integer, primary_key=True)

    # Create a dynamic class for the table
    class SalesData(db.Model):
        __tablename__ = 'sales_data'
        __table_args__ = {'extend_existing': True}
        locals().update(column_definitions)

    db.create_all()
    return SalesData

# Insert data into the table
def insert_data_into_db(data, table_class):
    # Insert each row of the DataFrame into the database
    for index, row in data.iterrows():
        row_dict = row.to_dict()
        record = table_class(**row_dict)
        db.session.add(record)
    db.session.commit()

# Route for file upload
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part", 400
        
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400
        
        if file and allowed_file(file.filename):
            filename = file.filename
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Process the uploaded file, assuming the first row is the header
            data = pd.read_csv(file_path) if filename.endswith('.csv') else pd.read_excel(file_path)
            
            # Print the columns of the uploaded CSV/Excel file (first row as header)
            print("Uploaded data columns (from header):", data.columns.tolist())

            # Optionally return column names in the response for debugging purposes
            return f"Uploaded CSV/Excel columns: {', '.join(data.columns)}"

    return render_template('upload.html')


# Route for displaying monthly profit and loss summary with a pie chart
@app.route('/dashboard', methods=['GET'])
def dashboard():
    try:
        sales_data_path = os.path.join(UPLOAD_FOLDER, 'sales_data.csv')
        sales_data = pd.read_csv(sales_data_path)

        # Print the columns of the sales data for debugging
        print("Sales data columns:", sales_data.columns.tolist())

        # Ensure 'Payment Date' column exists
        if 'Payment Date' not in sales_data.columns:
            return "Error: 'Payment Date' column not found in sales data.", 400
        
        # Convert 'Payment Date' column to datetime
        sales_data['Payment Date'] = pd.to_datetime(sales_data['Payment Date'], errors='coerce')
        sales_data['month'] = sales_data['Payment Date'].dt.to_period('M')

        # Define a dictionary to hold aggregation functions based on existing columns
        agg_funcs = {}

        # Check if required columns exist and set aggregation functions accordingly
        if 'Bank Settlement Value (Rs.)' in sales_data.columns:
            agg_funcs['settled_amount'] = ('Bank Settlement Value (Rs.)', 'sum')
        
        if 'Commission (Rs.)' in sales_data.columns:
            agg_funcs['commission_charges'] = ('Commission (Rs.)', 'sum')

        if 'Fixed Fee (Rs.)' in sales_data.columns:
            agg_funcs['fixed_charges'] = ('Fixed Fee (Rs.)', 'sum')

        if 'Shipping Fee (Rs.)' in sales_data.columns:
            agg_funcs['shipping_charges'] = ('Shipping Fee (Rs.)', 'sum')

        # Group by month and aggregate only existing fields
        summary = sales_data.groupby('month').agg(**agg_funcs)

        # Calculate total expenses and profit/loss
        summary['total_expenses'] = summary.get('commission_charges', 0) + summary.get('fixed_charges', 0) + summary.get('shipping_charges', 0)
        summary['profit_or_loss'] = summary.get('settled_amount', 0) - summary['total_expenses']

        # Generate Pie Chart
        pie_chart_path = os.path.join(UPLOAD_FOLDER, 'profit_loss_pie_chart.png')
        generate_pie_chart(summary, pie_chart_path)

        return render_template('dashboard.html', summary=summary.to_html(), pie_chart=pie_chart_path)
    
    except FileNotFoundError:
        return "Error: Sales data CSV file not found.", 404
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}", 500

# Function to generate a pie chart
def generate_pie_chart(summary, path):
    labels = summary.index.astype(str)  # Convert month Period to string for labels
    sizes = summary['profit_or_loss']  # Use profit/loss for pie chart sizes
    colors = plt.cm.Paired(range(len(sizes)))  # Generate colors

    plt.figure(figsize=(8, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
    plt.title('Monthly Profit or Loss Summary')
    plt.axis('equal')  # Equal aspect ratio ensures the pie chart is a circle.
    plt.savefig(path)  # Save the pie chart as an image
    plt.close()

if __name__ == '__main__':
    app.run(debug=True)
