import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mars.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# -----------------------------
# Database Models
# -----------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    medical_shop = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(100), nullable=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    reserved_quantity = db.Column(db.Integer, nullable=False)
    reservation_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationships for easier access in templates
    user = db.relationship("User", backref="reservations")
    medicine = db.relationship("Medicine", backref="reservations")

# -----------------------------
# Setup Database, Admin & Seed Medicines
# -----------------------------

with app.app_context():
    # Ensure Admin Exists
    admin_email = "sayonasajan@gmail.com"
    admin_password = "sayona123"
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        hashed_password = generate_password_hash(admin_password, method='pbkdf2:sha256')
        new_admin = User(username="sayona", email=admin_email, password=hashed_password, role='admin')
        db.session.add(new_admin)
        db.session.commit()

   


# -----------------------------
# Routes
# -----------------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        admin = User.query.filter_by(email=email, role='admin').first()
        if admin and admin.username == username and check_password_hash(admin.password, password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials. Please try again.")
    return render_template('admin_login.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, role='user').first()
        if user and check_password_hash(user.password, password):
            session['user_logged_in'] = True
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid credentials. Please try again.")
    return render_template('user_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered.")
            return redirect(url_for('register'))
        new_user = User(username=username, email=email, password=password, role='user')
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.")
        return redirect(url_for('user_login'))
    return render_template('register.html')

# -----------------------------
# User Dashboard
# -----------------------------

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_logged_in' not in session:
        return redirect(url_for('user_login'))
    
    medicines = Medicine.query.all()
    low_stock_medicines = Medicine.query.filter(Medicine.quantity < 8).all()
    upcoming_date = date.today().replace(day=1)
    expiry_nearing_medicines = Medicine.query.filter(Medicine.expiry_date <= upcoming_date).all()
    user_id = session['user_id']
    user_reservations = Reservation.query.filter_by(user_id=user_id).all()

    # Define the nearby locations dictionary
    nearby_map = {
        "Adoor": ["Pathanamthitta", "Konni"],
        "Pathanamthitta": ["Adoor", "Konni", "Ranni"],
        "Konni": ["Adoor", "Pathanamthitta", "Ranni"],
        "Ranni": ["Pathanamthitta", "Kozhencherry"],
        "Kozhencherry": ["Ranni", "Pathanamthitta"],
        "Elanthoor": ["Pandalam", "Adoor"],
        "Pandalam": ["Elanthoor", "Pathanamthitta"],
        "Chenneerkara": ["Pathanamthitta", "Konni"],
        "Vazhamuttom": ["Adoor", "Konni"],
        "SCS Layout": ["Pathanamthitta", "Adoor"]
    }

    return render_template('user_dashboard.html', 
                           medicines=medicines,
                           low_stock_medicines=low_stock_medicines,
                           expiry_nearing_medicines=expiry_nearing_medicines,
                           user_reservations=user_reservations,
                           nearby_map=nearby_map)

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form.get('search_query', '').strip()
    medicines = Medicine.query.filter(Medicine.name.ilike(f"%{search_query}%")).all()

    # Define nearby locations map
    nearby_map = {
        "Adoor": ["Pathanamthitta", "Konni"],
        "Pathanamthitta": ["Adoor", "Konni", "Ranni"],
        "Konni": ["Adoor", "Pathanamthitta", "Ranni"],
        "Ranni": ["Pathanamthitta", "Kozhencherry"],
        "Kozhencherry": ["Ranni", "Pathanamthitta"],
        "Elanthoor": ["Pandalam", "Adoor"],
        "Pandalam": ["Elanthoor", "Pathanamthitta"],
        "Chenneerkara": ["Pathanamthitta", "Konni"],
        "Vazhamuttom": ["Adoor", "Konni"],
        "SCS Layout": ["Pathanamthitta", "Adoor"]
    }

    return render_template('user_dashboard.html', medicines=medicines, nearby_map=nearby_map)


#@app.route('/search_location', methods=['POST'])
@app.route('/search_location', methods=['POST'])
def search_location():
    if 'user_logged_in' not in session:
        return redirect(url_for('user_login'))
    
    location_query = request.form['location_query'].strip().title()  # Normalize input
    search_query = request.form['search_query'].strip().title()  # Medicine name

    # Define nearby locations
    nearby_map = {
        "Adoor": ["Pathanamthitta", "Konni"],
        "Pathanamthitta": ["Adoor", "Konni", "Ranni"],
        "Konni": ["Adoor", "Pathanamthitta", "Ranni"],
        "Ranni": ["Pathanamthitta", "Kozhencherry"],
        "Kozhencherry": ["Ranni", "Pathanamthitta"],
        "Elanthoor": ["Pandalam", "Adoor"],
        "Pandalam": ["Elanthoor", "Pathanamthitta"],
        "Chenneerkara": ["Pathanamthitta", "Konni"],
        "Vazhamuttom": ["Adoor", "Konni"],
        "SCS Layout": ["Pathanamthitta", "Adoor"]
    }

    # Step 1: Search in the requested location
    medicines = Medicine.query.filter(
        Medicine.location == location_query,
        Medicine.name.ilike(f"%{search_query}%")
    ).all()

    # Step 2: If not found, check nearby locations
    if not medicines and location_query in nearby_map:
        nearby_locations = nearby_map[location_query]
        medicines = Medicine.query.filter(
            Medicine.location.in_(nearby_locations),
            Medicine.name.ilike(f"%{search_query}%")
        ).all()

        if medicines:
            flash(f"Medicine not found in {location_query}. Showing results from nearby locations: {', '.join(nearby_locations)}.")
        else:
            flash(f"Medicine not found in {location_query} or its nearby locations.")

    return render_template('user_dashboard.html', medicines=medicines, nearby_map=nearby_map)

@app.route('/reserve/<int:medicine_id>', methods=['POST'])
def reserve(medicine_id):
    if 'user_logged_in' not in session:
        return redirect(url_for('user_login'))
    user_id = session['user_id']
    medicine = Medicine.query.get(medicine_id)
    quantity_to_reserve = int(request.form['quantity'])
    if medicine and medicine.quantity >= quantity_to_reserve:
        medicine.quantity -= quantity_to_reserve
        reservation = Reservation(user_id=user_id, medicine_id=medicine_id, reserved_quantity=quantity_to_reserve)
        db.session.add(reservation)
        db.session.commit()
        flash("Reservation successful!")
    else:
        flash("Not enough stock available.")
    return redirect(url_for('user_dashboard'))

# -----------------------------
# Admin Dashboard & New Features
# -----------------------------

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    # Optional: if there's a shop search query, filter by medical shop name.
    shop_search = request.args.get('shop_search')
    if shop_search:
        medicines = Medicine.query.filter(Medicine.medical_shop.ilike(f"%{shop_search}%")).all()
    else:
        medicines = Medicine.query.all()
    reservations = Reservation.query.all()
    return render_template('admin_dashboard.html', medicines=medicines, reservations=reservations)

@app.route('/delete_selected', methods=['POST'])
def delete_selected():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    selected_ids = request.form.getlist('selected_ids')
    if selected_ids:
        for med_id in selected_ids:
            med = Medicine.query.get(int(med_id))
            if med:
                db.session.delete(med)
        db.session.commit()
        flash("Selected medicines deleted successfully!")
    else:
        flash("No medicines selected.")
    return redirect(url_for('admin_dashboard'))

@app.route('/mass_add_medicines', methods=['GET', 'POST'])
def mass_add_medicines():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        data = request.form['mass_data']
        lines = data.strip().splitlines()
        added = 0
        for line in lines:
            # Expecting format: name, quantity, expiry_date, medical_shop, location
            parts = [p.strip() for p in line.split(',')]
            if len(parts) == 5:
                try:
                    name, quantity, expiry_date_str, medical_shop, location = parts
                    quantity = int(quantity)
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                    new_med = Medicine(name=name, quantity=quantity, expiry_date=expiry_date,
                                       medical_shop=medical_shop, location=location)
                    db.session.add(new_med)
                    added += 1
                except Exception as e:
                    flash(f"Error processing line: {line}. Error: {e}")
        db.session.commit()
        flash(f"Mass add complete. {added} medicines added.")
        return redirect(url_for('admin_dashboard'))
    return render_template('mass_add_medicines.html')

@app.route('/admin_search_shop', methods=['POST'])
def admin_search_shop():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    shop_search = request.form['shop_search']
    return redirect(url_for('admin_dashboard', shop_search=shop_search))

@app.route('/add_medicine', methods=['POST'])
def add_medicine():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    name = request.form['name']
    quantity = int(request.form['quantity'])
    expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
    medical_shop = request.form['medical_shop']
    location = request.form['location']
    new_medicine = Medicine(name=name, quantity=quantity, expiry_date=expiry_date,
                            medical_shop=medical_shop, location=location)
    db.session.add(new_medicine)
    db.session.commit()
    flash("Medicine added successfully!")
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_medicine/<int:medicine_id>')
def delete_medicine(medicine_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    med = Medicine.query.get(medicine_id)
    db.session.delete(med)
    db.session.commit()
    flash("Medicine deleted successfully!")
    return redirect(url_for('admin_dashboard'))
@app.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
def delete_reservation(reservation_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    reservation = Reservation.query.get(reservation_id)
    if reservation:
        # Restore the medicine quantity when a reservation is deleted
        medicine = Medicine.query.get(reservation.medicine_id)
        if medicine:
            medicine.quantity += reservation.reserved_quantity
        
        db.session.delete(reservation)
        db.session.commit()
        flash("Reservation removed successfully!")
    else:
        flash("Reservation not found.")

    return redirect(url_for('admin_dashboard'))

# -----------------------------
# Logout
# -----------------------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -----------------------------
# Run Application
# -----------------------------

if __name__ == '__main__':
    app.run(debug=True)
