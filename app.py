from flask import Flask, request, jsonify, render_template, redirect, url_for
import mysql.connector
import bcrypt
import random
from flask import session

# Flask App
app = Flask(__name__)
app.secret_key = 'xyzuvw123'

# MySQL Database Connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="NayaPassword",
        database="banking_system"
    )

# Home Page with Buttons
@app.route('/')
def home():
    return render_template('index.html')

# Add User Route
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        data = request.form
        name = data['name']
        dob = data['dob']
        city = data['city']
        password = data['password']
        balance = float(data['balance'])
        contact_number = data['contact_number']
        email = data['email']
        address = data['address']

        # Validate fields
        if len(password) < 8 or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
            return jsonify({"error": "Password must be at least 8 characters long, include a number, and an uppercase letter."}), 400
        if len(contact_number) != 10 or not contact_number.isdigit():
            return jsonify({"error": "Contact number must be 10 digits."}), 400
        if "@" not in email:
            return jsonify({"error": "Invalid email address."}), 400

        # Generate Account Number
        account_number = str(random.randint(1000000000, 9999999999))
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert into Database
        db = get_db_connection()
        cursor = db.cursor()
        sql = """
        INSERT INTO users (name, account_number, dob, city, password, balance, contact_number, email, address)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (name, account_number, dob, city, hashed_password, balance, contact_number, email, address)
        try:
            cursor.execute(sql, values)
            db.commit()
            return jsonify({"message": "User added successfully!", "account_number": account_number}), 201
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()
    return render_template('add_user.html')

# Show User Route
@app.route('/show_user', methods=['GET'])
def show_user():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name, account_number, dob, city, balance, contact_number, email, address, is_active FROM users")
    users = cursor.fetchall()
    db.close()
    return render_template('show_user.html', users=users)

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account_number = request.form['account_number']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE account_number = %s", (account_number,))
        user = cursor.fetchone()
        db.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return render_template('dashboard.html', user=user)  # Redirect to user dashboard
        else:
            return render_template('login.html', error="Invalid account number or password")  # Show error
    return render_template('login.html')

# Balance Route


@app.route('/show_balance', methods=['POST'])
def show_balance():
    account_number = session.get('account_number')  # Retrieve account number from session
    if not account_number:
        return redirect(url_for('login'))  # Redirect to login if user is not logged in

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name, account_number, balance FROM users WHERE account_number = %s", (account_number,))
    user = cursor.fetchone()
    db.close()

    if user:
        return render_template('dashboard.html', user=user, response=f"Your current balance is {user['balance']}")
    else:
        return render_template('dashboard.html', error="User not found.")  # Handle user not found error

# Show Transactions Route
@app.route('/show_transactions', methods=['POST'])
def show_transactions():
    account_number = session.get('account_number')
    if not account_number:
        return redirect(url_for('login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions WHERE account_number = %s", (account_number,))
    transactions = cursor.fetchall()
    db.close()

    return render_template('dashboard.html', transactions=transactions)

# Credit Amount Route
@app.route('/credit_amount', methods=['POST'])
def credit_amount():
    account_number = session.get('account_number')
    if not account_number:
        return redirect(url_for('login'))

    amount = float(request.form['amount'])
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET balance = balance + %s WHERE account_number = %s", (amount, account_number))
    db.commit()
    db.close()

    return render_template('dashboard.html', message="Amount credited successfully.")

# Debit Amount Route
@app.route('/debit_amount', methods=['POST'])
def debit_amount():
    account_number = session.get('account_number')
    if not account_number:
        return redirect(url_for('login'))

    amount = float(request.form['amount'])
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET balance = balance - %s WHERE account_number = %s AND balance >= %s", (amount, account_number, amount))
    db.commit()
    db.close()

    return render_template('dashboard.html', message="Amount debited successfully.")

# Transfer Amount Route
@app.route('/transfer_amount', methods=['POST'])
def transfer_amount():
    account_number = session.get('account_number')
    if not account_number:
        return redirect(url_for('login'))

    transfer_to_account = request.form['transfer_to_account']
    amount = float(request.form['amount'])
    
    # Debit from current user's account
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET balance = balance - %s WHERE account_number = %s AND balance >= %s", (amount, account_number, amount))
    
    # Credit to the other user's account
    cursor.execute("UPDATE users SET balance = balance + %s WHERE account_number = %s", (amount, transfer_to_account))
    
    db.commit()
    db.close()

    return render_template('dashboard.html', message="Amount transferred successfully.")

# Account Activation/Deactivation Route
@app.route('/account_status', methods=['POST'])
def account_status():
    account_number = session.get('account_number')
    if not account_number:
        return redirect(url_for('login'))

    action = request.form['action']  # 'activate' or 'deactivate'

    db = get_db_connection()
    cursor = db.cursor()

    if action == 'activate':
        cursor.execute("UPDATE users SET is_active = 1 WHERE account_number = %s", (account_number,))
    elif action == 'deactivate':
        cursor.execute("UPDATE users SET is_active = 0 WHERE account_number = %s", (account_number,))
    
    db.commit()
    db.close()

    return render_template('dashboard.html', message=f"Account {action}d successfully.")

# Change Password Route
@app.route('/change_password', methods=['POST'])
def change_password():
    account_number = session.get('account_number')
    if not account_number:
        return redirect(url_for('login'))

    old_password = request.form['old_password']
    new_password = request.form['new_password']

    # Validate new password
    if len(new_password) < 8 or not any(c.isupper() for c in new_password) or not any(c.isdigit() for c in new_password):
        return render_template('dashboard.html', error="Password must be at least 8 characters long, include a number, and an uppercase letter.")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE account_number = %s", (account_number,))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(old_password.encode('utf-8'), user['password'].encode('utf-8')):
        hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("UPDATE users SET password = %s WHERE account_number = %s", (hashed_new_password, account_number))
        db.commit()
        db.close()
        return render_template('dashboard.html', message="Password changed successfully.")
    else:
        db.close()
        return render_template('dashboard.html', error="Old password is incorrect.")

# Update Profile Route
@app.route('/update_profile', methods=['POST'])
def update_profile():
    account_number = session.get('account_number')
    if not account_number:
        return redirect(url_for('login'))

    name = request.form['name']
    dob = request.form['dob']
    city = request.form['city']
    contact_number = request.form['contact_number']
    email = request.form['email']
    address = request.form['address']

    # Validate fields
    if len(contact_number) != 10 or not contact_number.isdigit():
        return render_template('dashboard.html', error="Contact number must be 10 digits.")
    if "@" not in email:
        return render_template('dashboard.html', error="Invalid email address.")

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE users
        SET name = %s, dob = %s, city = %s, contact_number = %s, email = %s, address = %s
        WHERE account_number = %s
    """, (name, dob, city, contact_number, email, address, account_number))
    db.commit()
    db.close()

    return render_template('dashboard.html', message="Profile updated successfully.")

# Logout Route
@app.route('/logout', methods=['GET'])
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('login'))

# Exit Route
@app.route('/exit', methods=['GET'])
def exit_app():
    return "Thank you for using the Banking System! Goodbye."

@app.route('/delete_user/<account_number>', methods=['POST'])
def delete_user(account_number):
    try:
        # Establish a database connection
        db = get_db_connection()
        cursor = db.cursor()

        # Delete the user from the database
        sql = "DELETE FROM users WHERE account_number = %s"
        cursor.execute(sql, (account_number,))
        db.commit()  # Commit the transaction to apply changes

        # Check if the row was deleted
        if cursor.rowcount == 0:
            return jsonify({"error": "User not found."}), 404

        db.close()

        # Redirect back to the user list page (or any page you want)
        return redirect(url_for('show_user'))

    except Exception as e:
        db.rollback()  # Rollback the transaction in case of error
        return jsonify({"error": str(e)}), 500

# Run the App
if __name__ == '__main__':
    app.run(debug=True)
