import os
import pandas as pd
import xml.etree.ElementTree as ET
from flask import Flask, request, render_template, send_file

app = Flask(__name__)

# Folder to save uploaded files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Allowable file extensions
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

# Check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for file upload
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part"
        
        file = request.files['file']
        if file.filename == '':
            return "No selected file"
        
        if file and allowed_file(file.filename):
            filename = file.filename
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Process the uploaded file
            if filename.endswith('.csv'):
                data = pd.read_csv(file_path)
            elif filename.endswith('.xlsx'):
                data = pd.read_excel(file_path)
            
            # Save the processed data to XML
            xml_file = generate_tally_xml(data)
            return send_file(xml_file, as_attachment=True)

    return render_template('upload.html')

# Generate Tally XML file from the data
def generate_tally_xml(data):
    root = ET.Element("ENVELOPE")
    tally_message = ET.SubElement(root, "TALLYMESSAGE")

    for index, row in data.iterrows():
        voucher = ET.SubElement(tally_message, "VOUCHER")
        ET.SubElement(voucher, "PLATFORM").text = str(row['platform'])
        ET.SubElement(voucher, "SALESAMOUNT").text = str(row['sales_amount'])
        ET.SubElement(voucher, "PAYMENTAMOUNT").text = str(row['payment_amount'])
        ET.SubElement(voucher, "DATE").text = str(row['date'])
    
    # Save the XML file
    xml_data = ET.tostring(root, encoding='unicode')
    xml_file = os.path.join(UPLOAD_FOLDER, 'sales_data.xml')
    with open(xml_file, 'w') as f:
        f.write(xml_data)
    
    return xml_file


# Route for displaying monthly profit and loss summary
@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Load sales data from CSV (or Excel if needed)
    sales_data = pd.read_csv(os.path.join(UPLOAD_FOLDER, 'sales_data.csv'))
    
    # Summarize monthly profit and loss
    sales_data['date'] = pd.to_datetime(sales_data['date'])
    sales_data['month'] = sales_data['date'].dt.to_period('M')

    # Group by month and aggregate the specified fields
    summary = sales_data.groupby('month').agg(
        commission_charges=pd.NamedAgg(column='commission_charges', aggfunc='sum'),
        commission_charges_tax=pd.NamedAgg(column='commission_charges_tax', aggfunc='sum'),
        fixed_charges=pd.NamedAgg(column='fixed_charges', aggfunc='sum'),
        fixed_charges_tax=pd.NamedAgg(column='fixed_charges_tax', aggfunc='sum'),
        collection_charges=pd.NamedAgg(column='collection_charges', aggfunc='sum'),
        collection_charges_tax=pd.NamedAgg(column='collection_charges_tax', aggfunc='sum'),
        other_charges=pd.NamedAgg(column='other_charges', aggfunc='sum'),
        other_charges_tax=pd.NamedAgg(column='other_charges_tax', aggfunc='sum'),
        shipping_charges=pd.NamedAgg(column='shipping_charges', aggfunc='sum'),
        shipping_charges_tax=pd.NamedAgg(column='shipping_charges_tax', aggfunc='sum'),
        settled_amount=pd.NamedAgg(column='settled_amount', aggfunc='sum'),
    )

    # Optionally calculate total profit or loss
    summary['total_expenses'] = (
        summary['commission_charges'] +
        summary['fixed_charges'] +
        summary['collection_charges'] +
        summary['other_charges'] +
        summary['shipping_charges']
    )
    summary['profit_or_loss'] = summary['settled_amount'] - summary['total_expenses']
    
    return summary.to_html()


if __name__ == '__main__':
    app.run(debug=True)

