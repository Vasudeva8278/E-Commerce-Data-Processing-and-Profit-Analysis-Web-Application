import os
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

# Function to analyze the CSV data
def analyze_data(file_path):
    df = pd.read_csv(file_path)
   
    total_price = df['final_price'].sum()
    total_tax = df['tax'].sum()
    
   
    plt.figure(figsize=(8, 6))
    df.groupby('item')['final_price'].sum().plot(kind='pie', autopct='%1.1f%%')
    plt.title('Distribution of Final Price by Item')
    plt.ylabel('')
    
    chart_path = os.path.join('static', 'images', 'price_distribution.png')
    plt.savefig(chart_path)
    plt.close()
    
    return total_price, total_tax, chart_path

@app.route('/')
def home():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file:
        file_path = os.path.join('data.csv')  # Save file temporarily
        file.save(file_path)
        
        # Analyze the uploaded CSV data
        total_price, total_tax, chart_path = analyze_data(file_path)
        
        return render_template('dashboard.html', 
                               total_price=total_price, 
                               total_tax=total_tax, 
                               chart_path=chart_path)

if __name__ == '__main__':
    app.run(debug=True)
