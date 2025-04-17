from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
import hashlib
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from functools import wraps
import os
from sqlalchemy import cast, Text
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://campus_bites_ihhx_user:gbpThtkEKB3r1K3LYrZMzSwuzPJkWWe0@dpg-cvdao4bv2p9s73cd9mrg-a.oregon-postgres.render.com/campus_bites_ihhx"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


db = SQLAlchemy(app)

class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    campus = db.Column(db.String(100), nullable=False)

    # Additional profile fields
    mobile_number = db.Column(db.String(15), nullable=True)
    mobile_verified = db.Column(db.Boolean, default=False)
    upi_number = db.Column(db.String(50), nullable=True)
    upi_id = db.Column(db.String(150), nullable=True)  # Increased length
    unique_shop_id = db.Column(db.String(100), unique=True, nullable=False)  # Now required
    qr_image = db.Column(db.String(255), nullable=True)  # Stores filename, not path


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    campus = db.Column(db.String(100), nullable=False)

    # Additional fields
    dob = db.Column(db.Date, nullable=True)  # Date of Birth
    phone_number = db.Column(db.String(15), unique=True, nullable=True)  # Phone Number
    payment_choice = db.Column(db.Enum('COD', 'UPI', name='payment_choice_enum'), nullable=True)  # Payment Preference

    
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

class Shop(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    owner_id=db.Column(db.Integer,db.ForeignKey('owner.id'),nullable=False)
    name=db.Column(db.String(100),nullable=False)
    description=db.Column(db.Text,nullable=True)
    shop_logo=db.Column(db.String(255),nullable=True)
    address=db.Column(db.String(255),nullable=False)
    category=db.Column(db.String(50),nullable=False)
    dining_availability=db.Column(db.Boolean,default=False)
    shop_capacity=db.Column(db.Integer,nullable=True)
    processing_power=db.Column(db.Integer,nullable=True)
    shop_open=db.Column(db.String(10),nullable=True)
    shop_close=db.Column(db.String(10),nullable=True)
    contact_number=db.Column(db.String(20),nullable=False)
    payment_methods=db.Column(db.JSON,nullable=True)
    closed_days=db.Column(db.JSON,nullable=True)
    discount=db.Column(db.Float,default=0.0)
    feedback=db.Column(db.Text,nullable=True)
    rating=db.Column(db.Float,default=0.0)
    status=db.Column(db.String(20),default='open')  # New field: 'open', 'closed', etc.

class MenuItem(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    shop_id=db.Column(db.Integer,db.ForeignKey('shop.id'),nullable=False)
    item_name=db.Column(db.String(100),nullable=False)
    cook_time=db.Column(db.Integer,nullable=True)
    category=db.Column(db.String(50),nullable=True)
    discount=db.Column(db.Float,default=0.0)
    status=db.Column(db.Enum('Available','Out of Stock',name='item_status_enum'),default='Available')
    spicy_level=db.Column(db.Integer,default=0)
    popularity_tag=db.Column(db.String(50),nullable=True)
    type=db.Column(db.Enum('Veg','Non-Veg',name='item_type_enum'),nullable=False)
    rating=db.Column(db.Float,default=0.0)
    item_photo=db.Column(db.String(255),nullable=True)  # 🆕 Optional image path

    shop=db.relationship('Shop',backref=db.backref('menu_items',lazy=True))


class ServingOption(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    menu_item_id=db.Column(db.Integer,db.ForeignKey('menu_item.id'),nullable=False)
    serving_size=db.Column(db.String(50),nullable=False)  # e.g., Half, Full
    price=db.Column(db.Float,nullable=False)

    menu_item=db.relationship('MenuItem',backref=db.backref('serving_options',lazy=True))

class Cart(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    customer_id=db.Column(db.Integer,db.ForeignKey('customer.id'))
    shop_id=db.Column(db.Integer,db.ForeignKey('shop.id'))
    status=db.Column(db.String(20),default='active') # active, ordered
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    cart_items=db.relationship('CartItem',backref='cart',cascade='all, delete-orphan')

class CartItem(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    cart_id=db.Column(db.Integer,db.ForeignKey('cart.id'))
    menu_item_id=db.Column(db.Integer,db.ForeignKey('menu_item.id'))
    serving_option_id=db.Column(db.Integer,db.ForeignKey('serving_option.id'))
    quantity=db.Column(db.Integer,default=1)

    menu_item=db.relationship('MenuItem')
    serving_option=db.relationship('ServingOption')



class CustomerOrder(db.Model):
    id=db.Column(db.Integer,primary_key=True)

    customer_id=db.Column(db.Integer,db.ForeignKey('customer.id'),nullable=False)
    customer=db.relationship('Customer',backref='orders')

    shop_id=db.Column(db.Integer,db.ForeignKey('shop.id'),nullable=False)
    shop=db.relationship('Shop',backref='orders')

    items=db.Column(db.JSON,nullable=False)  # [{item_id, name, quantity, serving, price}]
    total_price=db.Column(db.Float,nullable=False)
    cook_time=db.Column(db.Integer,nullable=False)  # Max cook time among items
    status=db.Column(db.String(20),default='pending')  # 'pending', 'accepted', 'denied', 'completed'

    order_time=db.Column(db.DateTime,default=datetime.utcnow)
    wait_time=db.Column(db.Integer,nullable=True)  # Minutes



def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_otp(email):
    otp = random.randint(100000, 999999)
    session['otp'] = otp
    try:
        sender_email = "campusbites.in01@gmail.com"
        password = "oytb qkrp xdki irse"
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = email
        message["Subject"] = "Your OTP Code"
        message.attach(MIMEText(f"Your OTP code is {otp}", "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, email, message.as_string())
        return True
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False
    

def get_or_create_cart(customer_id,shop_id):
    cart=Cart.query.filter_by(customer_id=customer_id,shop_id=shop_id,status='active').first()
    if not cart:
        cart=Cart(customer_id=customer_id,shop_id=shop_id)
        db.session.add(cart)
        db.session.commit()
    return cart

def calculate_wait_time(shop_id,cook_time):
    shop=Shop.query.get(shop_id)
    active_orders=CustomerOrder.query.filter_by(shop_id=shop_id,status='accepted').all()
    stove_count=shop.processing_power or 1
    stove_times=[0]*stove_count

    for order in active_orders:
        # assign to stove with minimum load
        idx=min(range(stove_count),key=lambda i:stove_times[i])
        stove_times[idx]+=order.cook_time

    min_stove=min(stove_times)
    return min_stove+cook_time



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_otp', methods=['POST'])
def send_otp_route():
    email = request.form['email']
    
    # ✅ Store email in session
    session['email'] = email

    if send_otp(email):
        return {'success': True}  # ✅ No jsonify, as you requested
    else:
        return {'success': False}
    
@app.route('/register_owner', methods=['GET', 'POST'])
def register_owner():
    if request.method == 'GET':
        return render_template('register_owner.html')  # Ensure this template exists

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        campus = request.form['campus']
        unique_shop_id = request.form['unique_shop_id']
        otp = request.form['otp']

        # Predefined shop ID for validation
        VALID_SHOP_ID = "shopid123"

        # Verify unique_shop_id matches predefined value
        if unique_shop_id != VALID_SHOP_ID:
            flash("Invalid Shop ID. Please enter the correct Shop ID to proceed.", "danger")
            return redirect(url_for('register_owner'))

        # OTP verification
        if 'otp' not in session or str(session['otp']) != otp:
            flash("Invalid OTP. Please try again.", "danger")
            return redirect(url_for('register_owner'))

        # Hash the password before storing
        hashed_password = hash_password(password)

        # Check if email or unique_shop_id already exists
        existing_owner = Owner.query.filter(
            (Owner.email == email) | (Owner.unique_shop_id == unique_shop_id)
        ).first()
        if existing_owner:
            flash("Email or Shop ID already exists. Try a different one.", "danger")
            return redirect(url_for('register_owner'))

        # Create new owner entry
        new_owner = Owner(
            name=name,
            email=email,
            password=hashed_password,
            campus=campus,
            unique_shop_id=unique_shop_id
        )

        try:
            db.session.add(new_owner)
            db.session.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login_owner'))
        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {str(e)}", "danger")
            return redirect(url_for('register_owner'))

    return redirect(url_for('register_owner'))


@app.route('/login_owner', methods=['GET', 'POST'])
def login_owner():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Hash the entered password for comparison
        hashed_password = hash_password(password)

        # Find owner in database
        owner = Owner.query.filter_by(email=email).first()

        if owner and owner.password == hashed_password:
            session['owner_id'] = owner.id  # Store user session
            session['owner_name'] = owner.name
            flash("Login successful! Welcome, " + owner.name, "success")
            return redirect(url_for('owner_dashboard'))  # Redirect to owner dashboard
        else:
            flash("Invalid email or password. Please try again.", "danger")
            return redirect(url_for('login_owner'))

    return render_template('login_owner.html')

@app.route('/owner_dashboard')
def owner_dashboard():
    if 'owner_id' not in session:
        flash("Please log in to access your dashboard.", "danger")
        return redirect(url_for('login_owner'))
    
    flash("Welcome back to your dashboard!", "success")
    return render_template('owner_dashboard.html')

@app.route('/owner_profile', methods=['GET', 'POST'])
def owner_profile():
    owner = Owner.query.get(session['owner_id'])
    if request.method == 'POST':
        owner.mobile_number = request.form.get('mobile_number')
        owner.upi_number = request.form.get('upi_number')
        owner.upi_id = request.form.get('upi_id')
        unique_shop_id = request.form.get('unique_shop_id')
        if unique_shop_id:
            # Check if the unique shop ID is already taken by another owner
            existing = Owner.query.filter_by(unique_shop_id=unique_shop_id).first()
            if existing and existing.id != owner.id:
                flash("The Unique Shop ID is already taken. Please choose another.", "danger")
                return redirect(url_for('owner_profile'))
            owner.unique_shop_id = unique_shop_id
        # Handle QR image upload if provided
        if 'qr_image' in request.files:
            file = request.files['qr_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                owner.qr_image = filename
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('owner_profile'))
    
    # Calculate profile completion percentage for these additional fields:
    # (mobile_number, upi_number, upi_id, unique_shop_id, qr_image)
    required_fields = [owner.mobile_number, owner.upi_number, owner.upi_id, owner.unique_shop_id, owner.qr_image]
    filled_count = sum(1 for field in required_fields if field)
    profile_completion = int((filled_count / len(required_fields)) * 100)
    
    return render_template('owner_profile.html', owner=owner, profile_completion=profile_completion)

@app.route('/create_shop', methods=['GET', 'POST'])
def create_shop():
    if 'owner_id' not in session:
        flash("Please log in to create a shop.", "danger")
        return redirect(url_for('login_owner'))

    if request.method == 'POST':
        shop_logo=request.files.get('shop_logo')
        name=request.form['name']
        description=request.form.get('description','')
        address=request.form['address']
        category=request.form['category']
        dining_availability=request.form.get('dining_availability')=='true'
        shop_capacity=request.form.get('shop_capacity')
        processing_power=request.form.get('processing_power')
        shop_open=request.form['shop_open']
        shop_close=request.form['shop_close']
        contact_number=request.form['contact_number']
        payment_methods=request.form.getlist('payment_methods[]')
        closed_days=request.form.getlist('closed_days[]')
        discount=request.form.get('discount',0.0)

        shop_capacity=int(shop_capacity) if shop_capacity else None
        processing_power=int(processing_power) if processing_power else None
        discount=float(discount) if discount else 0.0

        logo_path=None
        if shop_logo and shop_logo.filename!='':
            filename=secure_filename(shop_logo.filename)
            upload_folder='static/uploads'
            os.makedirs(upload_folder,exist_ok=True)
            logo_path=os.path.join(upload_folder,filename)
            shop_logo.save(logo_path)

        owner_id=session['owner_id']

        new_shop=Shop(
            owner_id=owner_id,
            name=name,
            description=description,
            shop_logo=logo_path,
            address=address,
            category=category,
            dining_availability=dining_availability,
            shop_capacity=shop_capacity,
            processing_power=processing_power,
            shop_open=shop_open,
            shop_close=shop_close,
            contact_number=contact_number,
            payment_methods=payment_methods,
            closed_days=closed_days,
            discount=discount
        )

        db.session.add(new_shop)
        db.session.commit()

        flash("Shop created successfully!", "success")
        return redirect(url_for('owner_dashboard'))

    return render_template('create_shop.html')


@app.route('/manage_shop')
def manage_shop():
    if 'owner_id' not in session:
        flash('Please log in to manage your shop.', 'warning')
        return redirect(url_for('owner_login'))

    shops=Shop.query.filter_by(owner_id=session['owner_id']).all()
    return render_template('manage_shop.html', shops=shops)

@app.route('/toggle_shop_status/<int:shop_id>', methods=['POST'])
def toggle_shop_status(shop_id):
    shop=Shop.query.get_or_404(shop_id)
    if 'owner_id' not in session or shop.owner_id!=session['owner_id']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('owner_login'))

    # Toggle status
    if shop.status=='open':
        shop.status='closed'
    else:
        shop.status='open'

    db.session.commit()
    flash(f"Shop status changed to {shop.status.capitalize()}.", "success")
    return redirect(url_for('manage_shop'))


@app.route('/delete_shop/<int:shop_id>', methods=['POST'])
def delete_shop(shop_id):
    if 'owner_id' not in session:
        flash('Please log in to delete your shop.', 'warning')
        return redirect(url_for('owner_login'))

    shop=Shop.query.get_or_404(shop_id)

    if shop.owner_id!=session['owner_id']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('manage_shop'))

    # Step 1: Find all menu items linked to this shop
    menu_items=MenuItem.query.filter_by(shop_id=shop.id).all()

    # Step 2: For each menu item, delete its associated serving options
    for item in menu_items:
        ServingOption.query.filter_by(menu_item_id=item.id).delete()

    # Step 3: Now delete the menu items
    for item in menu_items:
        db.session.delete(item)

    # Step 4: Finally, delete the shop
    db.session.delete(shop)
    db.session.commit()

    flash(f'Shop "{shop.name}" has been deleted successfully.', 'success')
    return redirect(url_for('manage_shop'))


@app.route('/edit_shop/<int:shop_id>', methods=['GET', 'POST'])
def edit_shop(shop_id):
    shop=Shop.query.get_or_404(shop_id)

    if request.method=='POST':
        shop.name=request.form['name']
        shop.description=request.form['description']
        shop.address=request.form['address']
        shop.category=request.form['category']
        shop.dining_availability=request.form.get('dining_availability')=='true'

        if shop.dining_availability:
            capacity=request.form.get('shop_capacity')
            if not capacity:
                flash('Capacity is required when dining is available.','danger')
                return redirect(request.url)
            shop.shop_capacity=int(capacity)
        else:
            shop.shop_capacity=None

        shop.processing_power=request.form.get('processing_power')
        shop.shop_open=request.form['shop_open']
        shop.shop_close=request.form['shop_close']
        shop.contact_number=request.form['contact_number']
        shop.payment_methods=request.form.getlist('payment_methods[]')
        shop.closed_days=request.form.getlist('closed_days[]')
        shop.discount=request.form.get('discount',0.0)

        if 'shop_logo' in request.files:
            file=request.files['shop_logo']
            if file and file.filename:
                filename=file.filename
                filepath=os.path.join('static/uploads',filename)
                file.save(filepath)
                shop.shop_logo=filename

        db.session.commit()
        flash('Shop updated successfully!','success')
        return redirect(url_for('owner_dashboard'))

    return render_template('edit_shop.html',shop=shop)


@app.route('/show_menu/<int:shop_id>')
def show_menu(shop_id):
    shop=Shop.query.get_or_404(shop_id)
    menu_items=MenuItem.query.filter_by(shop_id=shop_id).all()
    return render_template('show_menu.html',shop=shop,menu_items=menu_items)

@app.route('/addmenuitem/<int:shop_id>', methods=['GET', 'POST'])
def add_menu_item(shop_id):
    if request.method == 'POST':
        item_name=request.form.get('item_name')
        cook_time=request.form.get('cook_time')
        item_type=request.form.get('type')
        category=request.form.get('category')
        discount=request.form.get('discount')
        status=request.form.get('status')
        spicy_level=request.form.get('spicy_level')
        popularity_tag=request.form.get('popularity_tag')
        item_photo=request.files.get('item_photo')

        # Handle file upload (optional)
        filename=None
        if item_photo and item_photo.filename:
            filename=secure_filename(item_photo.filename)
            upload_path=os.path.join('static/uploads',filename)
            item_photo.save(upload_path)

        # Create MenuItem entry
        menu_item=MenuItem(
            shop_id=shop_id,
            item_name=item_name,
            cook_time=int(cook_time) if cook_time else None,
            type=item_type,
            category=category,
            discount=float(discount) if discount else 0.0,
            status=status,
            spicy_level=int(spicy_level) if spicy_level else 0,
            popularity_tag=popularity_tag,
            item_photo=filename
        )
        db.session.add(menu_item)
        db.session.commit()

        # Add serving options
        serving_sizes=request.form.getlist('serving_size[]')
        prices=request.form.getlist('price[]')

        for size,price in zip(serving_sizes,prices):
            serving=ServingOption(
                menu_item_id=menu_item.id,
                serving_size=size,
                price=float(price)
            )
            db.session.add(serving)

        db.session.commit()
        flash('Menu item added successfully.')
        return redirect(url_for('show_menu',shop_id=shop_id))

    return render_template('addmenuitem.html', shop_id=shop_id)

@app.route('/edit_menu_item/<int:item_id>', methods=['GET', 'POST'])
def edit_menu_item(item_id):
    item=MenuItem.query.get_or_404(item_id)

    if request.method=='POST':
        item.item_name=request.form['item_name']
        item.cook_time=request.form.get('cook_time')
        item.type=request.form['type']
        item.category=request.form['category']
        item.discount=request.form.get('discount')
        item.status=request.form['status']
        item.spicy_level=request.form.get('spicy_level')
        item.popularity_tag=request.form['popularity_tag']

        photo=request.files.get('item_photo')
        if photo and photo.filename:
            filename=secure_filename(photo.filename)
            filepath=os.path.join('static/uploads', filename)
            photo.save(filepath)
            item.photo_path=filepath

        ServingOption.query.filter_by(menu_item_id=item.id).delete()
        sizes=request.form.getlist('serving_size[]')
        prices=request.form.getlist('price[]')

        for size,price in zip(sizes,prices):
            if size and price:
                new_option=ServingOption(serving_size=size,price=float(price),menu_item_id=item.id)
                db.session.add(new_option)

        db.session.commit()
        flash('Menu item updated successfully.')
        return redirect(url_for('show_menu', shop_id=item.shop_id))

    return render_template('edit_menu_item.html', item=item)


@app.route('/deletemenuitem/<int:item_id>')
def delete_menu_item(item_id):
    item=MenuItem.query.get_or_404(item_id)
    shop_id=item.shop_id

    # Delete all associated serving options
    ServingOption.query.filter_by(menu_item_id=item.id).delete()

    # Delete the menu item
    db.session.delete(item)
    db.session.commit()

    flash('Menu item deleted successfully.')
    return redirect(url_for('show_menu', shop_id=shop_id))

@app.route('/accept_order/<int:order_id>', methods=['POST'])
def accept_order(order_id):
    order=CustomerOrder.query.get_or_404(order_id)
    if order.status=='pending':
        order.status='accepted'
        order.wait_time=calculate_wait_time(order.shop_id,order.cook_time)
        db.session.commit()
    return redirect(url_for('owner_orders'))

@app.route('/deny_order/<int:order_id>', methods=['POST'])
def deny_order(order_id):
    order=CustomerOrder.query.get_or_404(order_id)
    if order.status=='pending':
        order.status='denied'
        db.session.commit()
    return redirect(url_for('owner_orders'))

@app.route('/owner_orders')
def owner_orders():
    owner_id=session.get('owner_id')
    if not owner_id:
        return redirect(url_for('Ownerlogin'))
    owner=Owner.query.get(owner_id)
    shops=Shop.query.filter_by(owner_id=owner_id).all()
    shop_ids=[shop.id for shop in shops]
    pending_orders=CustomerOrder.query.filter(CustomerOrder.shop_id.in_(shop_ids),CustomerOrder.status=='pending').all()
    return render_template('owner_orders.html',pending_orders=pending_orders)



@app.route('/register_customer', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = hash_password(request.form['password'])  # Secure password hashing
        campus = request.form['campus']
        otp_entered = request.form['otp']
        
        # Fetch stored session data
        session_otp = session.get('otp')
        session_email = session.get('email')

        print("Session Email:", session_email)  # Debugging
        print("Form Email:", email)  # Debugging

        if not session_otp or str(session_otp) != str(otp_entered):
            flash("Invalid OTP. Please try again.", "danger")
            return render_template('register_customer.html')

        if email != session_email:
            flash("Email mismatch! Use the email where you received OTP.", "danger")
            return render_template('register_customer.html')

        # Check if the email already exists
        existing_customer = Customer.query.filter_by(email=email).first()
        if existing_customer:
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for('login_customer'))

        # Create and save new customer
        new_customer = Customer(name=name, email=email, password=password, campus=campus)
        db.session.add(new_customer)
        db.session.commit()

        # Clear OTP and email session
        session.pop('otp', None)
        session.pop('email', None)

        flash("Customer registration successful! Please login.", "success")
        return redirect(url_for('login_customer'))
    
    return render_template('register_customer.html')  


@app.route('/login_customer', methods=['GET', 'POST'])
def login_customer():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        user = Customer.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            session['role'] = 'customer'
            return redirect(url_for('customer_dashboard'))
        flash("Invalid email or password", "danger")
    return render_template('login_customer.html')


@app.route('/customer_dashboard')
def customer_dashboard():
    if 'user_id' not in session or session.get('role') != 'customer':
        flash("Please log in to access your dashboard.", "danger")
        return redirect(url_for('login_customer'))

    flash("Welcome back to your dashboard!", "success")
    return render_template('customer_dashboard.html')

@app.route('/customer_profile', methods=['GET', 'POST'])
def customer_profile():
    if 'user_id' not in session:
        return redirect(url_for('customer_login'))

    customer=Customer.query.get(session['user_id'])

    dob_locked=bool(customer.dob)

    if request.method=='POST':
        if not customer.dob:  # Allow setting DOB only once
            dob=request.form.get('dob')
            customer.dob=dob if dob else None

        phone=request.form.get('phone_number')
        pay=request.form.get('payment_choice')

        customer.phone_number=phone if phone else None
        customer.payment_choice=pay if pay else None

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('customer_profile'))

    fields=[customer.dob, customer.phone_number, customer.payment_choice]
    filled=sum(1 for f in fields if f)
    profile_completion=int((filled/len(fields))*100)

    return render_template('customer_profile.html',
                           customer=customer,
                           profile_completion=profile_completion,
                           dob_locked=dob_locked)


@app.route('/browse_shops')
def browse_shops():
    filter_type=request.args.get('filter','Both')  # Veg, Non-Veg, or Both
    category_filter=request.args.get('category',None)

    if filter_type=='Veg':
        shops=Shop.query.filter_by(category='Veg',status='open').all()
    elif filter_type=='Non-Veg':
        shops=Shop.query.filter_by(category='Non-Veg',status='open').all()
    else:
        shops=Shop.query.filter(Shop.status=='open').all()

    shop_ids=[shop.id for shop in shops]

    menu_items=MenuItem.query.filter(MenuItem.shop_id.in_(shop_ids),MenuItem.status=='Available').all()

    # Optional category filtering (if a category chip is clicked)
    if category_filter:
        menu_items=[item for item in menu_items if item.category==category_filter]

    # Group menu items by category for display
    categorized_items={}
    for item in menu_items:
        if item.category:
            if item.category not in categorized_items:
                categorized_items[item.category]=[]
            categorized_items[item.category].append(item)

    return render_template(
        'browse_shops.html',
        shops=shops,
        categorized_items=categorized_items,
        selected_filter=filter_type,
        selected_category=category_filter
    )

@app.route('/category_items/<category>')
def category_items(category):
    # Query all shops with status 'open'
    open_shops=Shop.query.filter_by(status='open').all()

    items=[]
    for shop in open_shops:
        for item in shop.menu_items:  # Assuming backref 'menu_items' in MenuItem table
            if item.category==category:
                items.append({
                    'shop':shop,
                    'item':item
                })

    return render_template('category_items.html',category=category,items=items)


@app.route('/shop/<int:shop_id>/menu')
def customer_shop_menu(shop_id):
    shop=Shop.query.get_or_404(shop_id)
    menu_items=MenuItem.query.filter_by(shop_id=shop_id).all()
    return render_template('customer_shop_menu.html',shop=shop,menu_items=menu_items)

@app.route('/add_to_cart/<int:menu_item_id>/<int:serving_option_id>', methods=['POST'])
def add_to_cart(menu_item_id, serving_option_id):
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))

    customer_id = session['user_id']
    menu_item = MenuItem.query.get(menu_item_id)
    shop_id = menu_item.shop_id
    cart = get_or_create_cart(customer_id, shop_id)

    existing_cart = Cart.query.filter(
        Cart.customer_id == customer_id,
        Cart.status == 'active',
        Cart.shop_id != shop_id
    ).first()
    if existing_cart:
        return "You already have an active cart from another shop."

    cart_item = CartItem.query.filter_by(
        cart_id=cart.id,
        menu_item_id=menu_item_id,
        serving_option_id=serving_option_id
    ).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            menu_item_id=menu_item_id,
            serving_option_id=serving_option_id,
            quantity=1
        )
        db.session.add(cart_item)

    db.session.commit()
    return redirect(url_for('view_cart'))


@app.route('/cart')
def view_cart():
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))

    customer_id = session['user_id']
    cart = Cart.query.filter_by(customer_id=customer_id, status='active').first()
    return render_template('cart.html', cart=cart)


@app.route('/update_cart_item/<int:item_id>', methods=['POST'])
def update_cart_item(item_id):
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))

    new_quantity = int(request.form['quantity'])
    cart_item = CartItem.query.get(item_id)
    cart_item.quantity = new_quantity
    db.session.commit()
    return redirect(url_for('view_cart'))


@app.route('/remove_cart_item/<int:item_id>')
def remove_cart_item(item_id):
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))

    item = CartItem.query.get(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('view_cart'))

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))

    customer_id=session['user_id']
    cart=Cart.query.filter_by(customer_id=customer_id,status='active').first()

    if not cart or not cart.cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('view_cart'))

    order_items=[]
    total_price=0
    max_cook_time=0

    for i in cart.cart_items:
        menu_item=MenuItem.query.get(i.menu_item_id)
        serving=ServingOption.query.get(i.serving_option_id)

        item_detail={
            'item_id':menu_item.id,
            'name':menu_item.item_name,
            'quantity':i.quantity,
            'serving':serving.serving_size,
            'price':serving.price
        }
        total_price+=serving.price*i.quantity
        max_cook_time=max(max_cook_time,menu_item.cook_time)
        order_items.append(item_detail)

    order=CustomerOrder(
        customer_id=customer_id,
        shop_id=cart.shop_id,
        items=order_items,
        total_price=total_price,
        cook_time=max_cook_time,
        status='pending'
    )
    db.session.add(order)

    cart.status='ordered'
    db.session.commit()

    flash('Order placed successfully!', 'success')
    return redirect(url_for('customer_orders'))

@app.route('/customer_orders')
def customer_orders():
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login_customer'))

    customer_id=session['user_id']
    orders=CustomerOrder.query.filter_by(customer_id=customer_id).order_by(CustomerOrder.id.desc()).all()

    return render_template('customer_orders.html', orders=orders)


@app.route('/customer_favorites')
def customer_favorites():
    return render_template('customer_favorites.html')  # or the correct file name

@app.route('/track_order')
def track_order():
    return render_template('track_order.html')  # Make sure this template exists


# Route for About Us page
@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        new_message = ContactMessage(name=name, email=email, message=message)
        db.session.add(new_message)
        db.session.commit()
        flash("Thank you for reaching out! We'll get back to you shortly.", "success")
        return redirect(url_for('contact_us'))
    return render_template('contact_us.html')

# Additional route to handle form submissions explicitly if needed
@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    # Save the message to the database
    new_message = ContactMessage(name=name, email=email, message=message)
    db.session.add(new_message)
    db.session.commit()
    return jsonify({"message": "Thank you for your message! We'll get in touch soon."})

# Route for Privacy Policy page
@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.get_table_names():  # Check if tables exist
            db.create_all()
            print("Tables created successfully")
        else:
            print("Tables already exist, skipping creation.")
    app.run(debug=True)

