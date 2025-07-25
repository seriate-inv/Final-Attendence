from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import random
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from flask import make_response
import csv
import io
from email.message import EmailMessage
import smtplib

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
app.permanent_session_lifetime = timedelta(minutes=15)

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# MySQL configuration
db = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', 'root'),
    database=os.getenv('DB_NAME', 'entry_exit_db')
)
cursor = db.cursor()

# Email configuration - Updated with your App Password
EMAIL_CONFIG = {
    "address": "seriate001archana@gmail.com",
    "password": "wyyf gduw ulql vpqz",  # Your App Password here
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465
}

ADMIN_CREDENTIALS = {
    "username": "admin-seriate",
    "password": "archanaT@4725",
    "email": "seriate001archana@gmail.com"
}

def send_otp_email(receiver_email, otp):
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Your Admin Login OTP - Seriate Access System'
        msg['From'] = EMAIL_CONFIG['address']
        msg['To'] = receiver_email
        msg.set_content(f'''Hello Admin,

Your one-time password (OTP) for Seriate Access System is: 
        
        {otp}

This OTP is valid for 15 minutes. Please do not share this with anyone.

Regards,
Seriate Security Team''')

        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as smtp:
            smtp.login(EMAIL_CONFIG['address'], EMAIL_CONFIG['password'])
            smtp.send_message(msg)
        print(f"OTP sent successfully to {receiver_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Failed to authenticate with Gmail. Please check your App Password.")
        return False
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def filter_entries(name_filter, date_filter):
    """Filter entries based on name and date parameters"""
    base_query = """
        SELECT 
            e1.name, 
            e1.email, 
            e1.timestamp AS entry_time, 
            e2.timestamp AS exit_time,
            e1.gps_location AS entry_location,
            e2.gps_location AS exit_location,
            e1.image_path AS entry_photo,
            e2.image_path AS exit_photo
        FROM entries e1
        LEFT JOIN entries e2 
            ON e1.email = e2.email 
            AND e2.type = 'exit' 
            AND DATE(e1.timestamp) = DATE(e2.timestamp)
        WHERE e1.type = 'entry'
    """
    filters = []
    values = []

    if name_filter:
        filters.append("e1.name LIKE %s")
        values.append(f"%{name_filter}%")
    if date_filter:
        filters.append("DATE(e1.timestamp) = %s")
        values.append(date_filter)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += " ORDER BY e1.timestamp DESC"
    cursor.execute(base_query, tuple(values))
    raw_entries = cursor.fetchall()

    entries = []
    for row in raw_entries:
        entry_time = row[2]
        exit_time = row[3]
        hours_worked = "—"
        if entry_time and exit_time:
            delta = exit_time - entry_time
            total_seconds = int(delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            hours_worked = f"{hours} hr {minutes} min"
        
        # Convert to dictionary format for CSV writing
        entry_dict = {
            'name': row[0],
            'email': row[1],
            'type': 'entry',
            'image_path': row[6],
            'gps_location': row[4],
            'timestamp': row[2],
            'hours_worked': hours_worked
        }
        entries.append(entry_dict)

    return entries

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/form')
def form():
    return render_template('form.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if 'verify_otp' in request.form:
            user_otp = request.form.get('otp', '')
            if 'otp' in session and user_otp == session['otp']:
                session['admin_logged_in'] = True
                session.pop('otp', None)
                flash('Login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid OTP. Please try again.', 'danger')
                return redirect(url_for('admin'))
        
        else:
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            
            if (username == ADMIN_CREDENTIALS['username'] and 
                password == ADMIN_CREDENTIALS['password']):
                otp = str(random.randint(100000, 999999))
                session['otp'] = otp
                print(f"Generated OTP: {otp}")
                
                if send_otp_email(ADMIN_CREDENTIALS['email'], otp):
                    flash('OTP sent to your registered email. Please check your inbox.', 'success')
                    return render_template('admin_otp.html')
                else:
                    flash('Failed to send OTP. Please contact support.', 'danger')
                    return redirect(url_for('admin'))
            else:
                flash('Invalid credentials', 'danger')
                return redirect(url_for('admin'))
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('admin'))

    name_filter = request.args.get('name', '').strip()
    date_filter = request.args.get('date', '').strip()

    base_query = """
        SELECT 
            e1.name, 
            e1.email, 
            e1.timestamp AS entry_time, 
            e2.timestamp AS exit_time,
            e1.gps_location AS entry_location,
            e2.gps_location AS exit_location,
            e1.image_path AS entry_photo,
            e2.image_path AS exit_photo
        FROM entries e1
        LEFT JOIN entries e2 
            ON e1.email = e2.email 
            AND e2.type = 'exit' 
            AND DATE(e1.timestamp) = DATE(e2.timestamp)
        WHERE e1.type = 'entry'
    """
    filters = []
    values = []

    if name_filter:
        filters.append("e1.name LIKE %s")
        values.append(f"%{name_filter}%")
    if date_filter:
        filters.append("DATE(e1.timestamp) = %s")
        values.append(date_filter)

    if filters:
        base_query += " AND " + " AND ".join(filters)

    base_query += " ORDER BY e1.timestamp DESC"
    cursor.execute(base_query, tuple(values))
    raw_entries = cursor.fetchall()

    entries = []
    for row in raw_entries:
        entry_time = row[2]
        exit_time = row[3]
        hours_worked = "—"
        if entry_time and exit_time:
            delta = exit_time - entry_time
            total_seconds = int(delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            hours_worked = f"{hours} hr {minutes} min"
        entries.append(row + (hours_worked,))

    return render_template('admin.html', entries=entries)

@app.route('/admin/email_csv')
def email_csv():
    name = request.args.get('name', '')
    date = request.args.get('date', '')

    # Filtered data - Now this function exists!
    filtered = filter_entries(name, date)

    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Email', 'Type', 'Image', 'Location', 'Timestamp', 'Worked Hours'])

    for entry in filtered:
        writer.writerow([entry['name'], entry['email'], entry['type'], entry['image_path'], entry['gps_location'], entry['timestamp'], entry['hours_worked']])

    csv_data = output.getvalue().encode()  # Convert to bytes
    output.close()

    # Prepare email
    msg = EmailMessage()
    msg['Subject'] = 'Filtered Entries CSV'
    msg['From'] = EMAIL_CONFIG['address']  # Use your email config
    msg['To'] = ADMIN_CREDENTIALS['email']  # Send to admin email
    msg.set_content("Please find the attached CSV file containing filtered entry-exit data.")

    # Attach CSV
    msg.add_attachment(csv_data, maintype='text', subtype='csv', filename='entries.csv')

    try:
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as smtp:
            smtp.login(EMAIL_CONFIG['address'], EMAIL_CONFIG['password'])
            smtp.send_message(msg)
        flash('Email sent successfully!', 'success')
    except Exception as e:
        flash(f'❌ Error sending email: {e}', 'danger')

    return redirect(url_for('admin_dashboard', name=name, date=date))

@app.route('/admin/download_csv')
def download_csv():
    name_filter = request.args.get('name', '').strip()
    date_filter = request.args.get('date', '').strip()

    query = """
        SELECT 
            e1.name, 
            e1.email, 
            e1.timestamp AS entry_time, 
            e2.timestamp AS exit_time,
            e1.gps_location AS entry_location,
            e2.gps_location AS exit_location
        FROM entries e1
        LEFT JOIN entries e2 
            ON e1.email = e2.email 
            AND e2.type = 'exit' 
            AND DATE(e1.timestamp) = DATE(e2.timestamp)
        WHERE e1.type = 'entry'
    """
    filters = []
    values = []

    if name_filter:
        filters.append("e1.name LIKE %s")
        values.append(f"%{name_filter}%")
    if date_filter:
        filters.append("DATE(e1.timestamp) = %s")
        values.append(date_filter)

    if filters:
        query += " AND " + " AND ".join(filters)

    cursor.execute(query, tuple(values))
    data = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Email', 'Entry Time', 'Exit Time', 'Entry Location', 'Exit Location'])
    for row in data:
        writer.writerow(row)

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=filtered_data.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('admin'))

@app.route('/submit', methods=['POST'])
def submit():
    try:
        name = request.form['name']
        email = request.form['email']
        type_ = request.form['type']
        gps = request.form['gps']
        timestamp = datetime.now()

        image = request.files['image']
        filename = secure_filename(image.filename)
        relative_path = f"uploads/{filename}"  # ✅ Use relative path
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(full_path)

        query = "INSERT INTO entries (name, email, type, image_path, gps_location, timestamp) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (name, email, type_, relative_path, gps, timestamp)
        cursor.execute(query, values)
        db.commit()

        return f"✅ Entry submitted for {name}!"
    except Exception as e:
        db.rollback()
        return f"❌ Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)