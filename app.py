from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'  # Set your MySQL password
app.config['MYSQL_DB'] = 'train_management'

mysql = MySQL(app)

# Admin default credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# --------------------- ROUTES --------------------- #

@app.route('/')
def index():
    return redirect('/login')

# --------------------- USER REGISTRATION --------------------- #
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        account = cursor.fetchone()
        if account:
            flash('Username already exists!', 'error')
            return redirect('/register')

        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s,%s,%s)",
                       (username, email, password))
        mysql.connection.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect('/login')

    return render_template('register.html')


# --------------------- USER LOGIN --------------------- #
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            session['role'] = 'admin'
            return redirect('/admin')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        account = cursor.fetchone()
        if account:
            session['username'] = account['username']
            session['role'] = 'user'
            return redirect('/user')
        else:
            flash('Invalid username or password', 'error')
            return redirect('/login')

    return render_template('login.html')


# --------------------- LOGOUT --------------------- #
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('Logged out successfully', 'success')
    return redirect('/login')


# --------------------- ADMIN DASHBOARD --------------------- #
@app.route('/admin')
def admin():
    if 'role' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM trains")
        trains = cursor.fetchall()
        return render_template('admin.html', trains=trains)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- ADD TRAIN --------------------- #
@app.route('/add_train', methods=['GET', 'POST'])
def add_train():
    if 'role' in session and session['role'] == 'admin':
        if request.method == 'POST':
            train_name = request.form['train_name']
            source_station = request.form['source_station']
            destination_station = request.form['destination_station']
            departure_time = request.form['departure_time']
            arrival_time = request.form['arrival_time']
            total_seats = request.form['total_seats']

            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO trains (train_name, source_station, destination_station, departure_time, arrival_time, total_seats, available_seats, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (train_name, source_station, destination_station, departure_time, arrival_time, total_seats, total_seats, 'On Time'))
            mysql.connection.commit()
            flash('Train added successfully', 'success')
            return redirect('/admin')

        return render_template('add_train.html')
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- VIEW USER DASHBOARD --------------------- #
@app.route('/user')
def user():
    if 'role' in session and session['role'] == 'user':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM trains WHERE available_seats > 0")
        trains = cursor.fetchall()
        return render_template('user.html', trains=trains)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- BOOK TICKET --------------------- #
@app.route('/book_ticket/<int:train_id>', methods=['GET', 'POST'])
def book_ticket(train_id):
    if 'role' in session and session['role'] == 'user':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM trains WHERE id=%s", (train_id,))
        train = cursor.fetchone()

        if request.method == 'POST':
            seats = int(request.form['seats'])
            if seats > train[7]:  # available_seats
                flash('Not enough seats available', 'error')
                return redirect(f'/book_ticket/{train_id}')

            total_amount = seats * 100  # Assume ₹100 per seat
            cursor.execute("""
                INSERT INTO bookings (username, train_id, seats_booked, total_amount, status)
                VALUES (%s,%s,%s,%s,%s)
            """, (session['username'], train_id, seats, total_amount, 'Booked'))

            # Update available seats
            cursor.execute("UPDATE trains SET available_seats = available_seats - %s WHERE id=%s", (seats, train_id))
            mysql.connection.commit()
            flash('Booking successful! Proceed to payment.', 'success')

            # Get the booking id
            cursor.execute("SELECT LAST_INSERT_ID()")
            booking_id = cursor.fetchone()[0]
            return redirect(f'/payment/{booking_id}')

        return render_template('book_ticket.html', train=train)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- PAYMENT --------------------- #
@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if 'role' in session and session['role'] == 'user':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM bookings WHERE id=%s AND username=%s", (booking_id, session['username']))
        booking = cursor.fetchone()

        if not booking:
            flash('Booking not found', 'error')
            return redirect('/user')

        if request.method == 'POST':
            cursor.execute("UPDATE bookings SET status='Paid' WHERE id=%s", (booking_id,))
            mysql.connection.commit()
            flash('Payment successful!', 'success')
            return redirect(f'/ticket/{booking_id}')

        return render_template('payment.html', booking=booking)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- TICKET --------------------- #
@app.route('/ticket/<int:booking_id>')
def ticket(booking_id):
    if 'role' in session and session['role'] == 'user':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM bookings WHERE id=%s AND username=%s", (booking_id, session['username']))
        booking = cursor.fetchone()
        if not booking:
            flash('Booking not found', 'error')
            return redirect('/user')

        cursor.execute("SELECT * FROM trains WHERE id=%s", (booking[2],))  # train_id
        train = cursor.fetchone()

        return render_template('ticket.html', booking=booking, train=train)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- DOWNLOAD TICKET --------------------- #
@app.route('/download_ticket/<int:booking_id>')
def download_ticket(booking_id):
    if 'role' in session and session['role'] == 'user':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM bookings WHERE id=%s AND username=%s", (booking_id, session['username']))
        booking = cursor.fetchone()
        if not booking:
            flash('Booking not found', 'error')
            return redirect('/user')

        cursor.execute("SELECT * FROM trains WHERE id=%s", (booking[2],))
        train = cursor.fetchone()

        ticket_text = f"""
        -------- Train Ticket --------
        Booking ID: {booking[0]}
        Username: {booking[1]}
        Train Name: {train[1]}
        Source: {train[2]}
        Destination: {train[3]}
        Departure: {train[4]}
        Arrival: {train[5]}
        Seats Booked: {booking[3]}
        Total Amount: ₹{booking[4]}
        Status: {booking[5]}
        ------------------------------
        """

        # Send as a text file
        return send_file(BytesIO(ticket_text.encode()), as_attachment=True, download_name=f'ticket_{booking[0]}.txt', mimetype='text/plain')
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- VIEW BOOKINGS (ADMIN) --------------------- #
@app.route('/view_bookings')
def view_bookings():
    if 'role' in session and session['role'] == 'admin':
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM bookings")
        bookings = cursor.fetchall()
        return render_template('view_bookings.html', bookings=bookings)
    else:
        flash('Access denied', 'error')
        return redirect('/login')


# --------------------- RUN APP --------------------- #
if __name__ == '__main__':
    app.run(debug=True)
