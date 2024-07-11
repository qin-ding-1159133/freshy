from app import app                    # Import the Flask application instance named 'app' from the 'app' module            
from flask import render_template      # Import necessary modules from Flask
from flask import request
from flask import redirect
from flask import url_for
from flask import session
from datetime import datetime          # Import datetime module for date and time manipulation
import mysql.connector                 # Import MySQL Connector module
import connect                         # Import the connect module containing database connection details
from flask_hashing import Hashing  
    # Import the Hashing class from Flask Hashing extension
import base64
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime, timedelta
from flask import flash
from datetime import date


from apscheduler.schedulers.background import BackgroundScheduler

hashing = Hashing(app)  #create an instance of hashing
app.secret_key = 'hello'

UPLOAD_FOLDER = 'app/static/assets/img'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialise global variables for database connection
dbconn = None
connection = None

# Function to establish database connection and return cursor
def getCursor():
    global dbconn
    global connection
    connection = mysql.connector.connect(user=connect.dbuser, \
    password=connect.dbpass, host=connect.dbhost, auth_plugin='mysql_native_password',\
    database=connect.dbname, autocommit=True)
    dbconn = connection.cursor()
    return dbconn


@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if user is logged in
    if 'loggedin' in session:
        role = session.get('role')  # Get the user's role from the session
        # Redirect based on user's role
        if role == 1:  
            # Get the user's ID from the session
            user_id = session.get('user_id')
            # Get a cursor object to interact with the database
            cursor = getCursor()
            # Execute a SQL query to fetch the admin's role 
            cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
            admin_info = cursor.fetchone()
            # Render the manager dashboard template with location data

            # Fetch summary info for accounts and customers across all depots
            cursor.execute('''SELECT 
                                (SELECT COUNT(*) FROM customers) AS total_customers,
                                (SELECT COUNT(*) FROM orders JOIN customers ON orders.user_id = customers.user_id) AS total_orders,
                                (SELECT SUM(p.amount) FROM payments p JOIN orders o ON p.payment_id = o.payment_id JOIN customers c ON o.user_id = c.user_id) AS total_revenue,
                                (SELECT COUNT(*) FROM subscription_records sr JOIN customers c ON sr.user_id = c.user_id) AS total_subscriptions
                            FROM dual''')
            customer_summary_info = cursor.fetchone()

            cursor.execute('''SELECT 
                                (SELECT COUNT(*) FROM accounts) AS total_account_holders,
                                (SELECT COUNT(*) FROM orders JOIN accounts ON orders.user_id = accounts.user_id) AS total_orders,
                                (SELECT SUM(p.amount) FROM payments p JOIN orders o ON p.payment_id = o.payment_id JOIN accounts a ON o.user_id = a.user_id) AS total_revenue,
                                (SELECT COUNT(*) FROM subscription_records sr JOIN accounts a ON sr.user_id = a.user_id) AS total_subscriptions
                            FROM dual''')
            account_summary_info = cursor.fetchone()

            # Combine summaries, handling None values gracefully
            total_customers = (customer_summary_info[0] or 0) + (account_summary_info[0] or 0)
            total_orders = (customer_summary_info[1] or 0) + (account_summary_info[1] or 0)
            total_revenue = (customer_summary_info[2] or 0) + (account_summary_info[2] or 0)
            total_subscriptions = (customer_summary_info[3] or 0) + (account_summary_info[3] or 0)


            cursor.execute('''
                SELECT 
                    orders.order_id,
                    CONCAT(customers.given_name, ' ', customers.family_name) AS full_name,
                    orders.order_date,
                    ROUND((SUM(order_lines.product_quantity * products.product_price * IFNULL(promotion_types.discount, 1)) + IFNULL(shippments.shippment_price, 0)), 2) AS total_amount,
                    ost.order_status_type_name AS delivery_status,
                    customers.pic AS customer_pic,
                    accounts.account_name AS account_holder_name,
                    accounts.pic AS account_pic,
                    CASE 
                        WHEN customers.user_id IS NOT NULL THEN 1
                        ELSE 0
                    END AS is_customer
                FROM 
                    orders 
                    LEFT JOIN customers ON customers.user_id = orders.user_id
                    LEFT JOIN payments ON payments.payment_id = orders.payment_id
                    LEFT JOIN (
                        SELECT 
                            order_id, 
                            MAX(order_status_type_id) AS latest_status_id 
                        FROM 
                            order_assignments 
                        GROUP BY 
                            order_id
                    ) oa ON orders.order_id = oa.order_id
                    LEFT JOIN order_status_types ost ON oa.latest_status_id = ost.order_status_type_id
                    LEFT JOIN accounts ON accounts.user_id = orders.user_id
                    LEFT JOIN order_lines ON order_lines.order_id = orders.order_id
                    LEFT JOIN products ON products.product_id = order_lines.product_id
                    LEFT JOIN promotion_types ON promotion_types.promotion_type_id = products.promotion_type_id
                    LEFT JOIN shippments ON shippments.shippment_id = orders.shippment_id
                GROUP BY
                    orders.order_id,
                    customers.given_name,
                    customers.family_name,
                    orders.order_date,
                    ost.order_status_type_name,
                    customers.pic,
                    accounts.account_name,
                    accounts.pic,
                    shippments.shippment_price
                ORDER BY 
                    orders.order_date DESC,
                    orders.order_id DESC
                LIMIT 4;
            ''')

            recent_orders = cursor.fetchall()


            # Process the results into a list of dictionaries for easier access in the template
            orders = []
            for row in recent_orders:
                orders.append({
                    'order_id': row[0],
                    'full_name': row[1],
                    'order_date': row[2],
                    'total_amount': row[3],
                    'delivery_status': row[4],
                    'customer_pic': row[5],
                    'account_holder_name': row[6],
                    'account_pic': row[7],
                    'is_customer': row[8]
                })

            cursor.execute('''SELECT products.product_id, product_categories.product_category_name, CONCAT(product.product_name, " ", units.unit_name) AS produce_name,
                               round(stock.quantity, 0), CONCAT(round(products.product_price * promotion_types.discount, 2)) AS final_price, product.pic FROM products
                               LEFT JOIN  product_categories ON products.product_category_id=product_categories.product_category_id
                               LEFT JOIN product ON products.SKU=product.SKU
                               LEFT JOIN units ON product.unit=units.unit_id
                               LEFT JOIN stock ON products.product_id=stock.product_id
                               LEFT JOIN promotion_types ON products.promotion_type_id=promotion_types.promotion_type_id
                               WHERE products.product_status=1 AND product_categories.product_category_id !=8 AND product_categories.product_category_id !=7
                               ORDER BY products.product_id DESC
                               LIMIT 4;
                               ''', )
            recent_products = cursor.fetchall()

            cursor.execute('''SELECT products.product_id, boxes.box_name, CONCAT(units.unit_name, " ",product_categories.product_category_name) AS unit_name,
                               round(stock.quantity, 0), CONCAT(round(products.product_price * promotion_types.discount, 2)) AS final_price, boxes.pic FROM products
                               LEFT JOIN  product_categories ON products.product_category_id=product_categories.product_category_id
                               LEFT JOIN boxes ON products.SKU=boxes.SKU
                               LEFT JOIN units ON boxes.unit=units.unit_id
                               LEFT JOIN stock ON products.product_id=stock.product_id
                               LEFT JOIN promotion_types ON products.promotion_type_id=promotion_types.promotion_type_id
                               WHERE products.product_status=1 AND product_categories.product_category_id !=8 AND product_categories.product_category_id =7
                               ORDER BY products.product_id DESC
                               LIMIT 4; 
                               ''')
            recent_boxes = cursor.fetchall()

            cursor.execute('''SELECT subscription_records.*,
                                CONCAT(customers.title, ' ', customers.given_name, ' ', customers.family_name) AS customer_full_name,
                                accounts.account_name AS account_name, accounts.account_id
                                FROM subscription_records 
                                LEFT JOIN accounts ON subscription_records.user_id = accounts.user_id
                                LEFT JOIN customers ON subscription_records.user_id = customers.user_id
                                WHERE subscription_records.subscription_status ='active' 
                                ORDER BY subscription_records.record_id DESC
                                LIMIT 4
                                ;''')
            recent_subscription = cursor.fetchall()

            cursor.execute('''SELECT users.user_id, staff.title, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic, staff.email, staff.phone_number
                                FROM users LEFT JOIN staff ON users.user_id=staff.user_id
                                WHERE users.role_id = 3 or users.role_id = 2
                                LIMIT 4
                               ;''')
            staff_list = cursor.fetchall()

            cursor.execute('''SELECT * FROM customers ORDER BY user_id DESC LIMIT 4''')
            recent_customers = cursor.fetchall()

            cursor.execute('''SELECT * FROM accounts WHERE balance <0 LIMIT 4''')
            recent_accounts = cursor.fetchall()

            cursor.execute('''SELECT 
                                    news.news_id,
                                    news.title,
                                    news.publish_date,
                                    CONCAT(staff.given_name, ' ', staff.family_name) AS full_name, 
                                    news.pic
                                FROM 
                                    news
                                INNER JOIN 
                                    staff ON news.created_by = staff.user_id
                                ORDER BY 
                                    news.publish_date DESC,
                                    news.news_id DESC
                                LIMIT 4''')
            
            recent_news = cursor.fetchall()

            cursor.execute('''SELECT return_authorization.*, COALESCE(CONCAT(customers.title, " ", customers.given_name, " ", customers.family_name), accounts.account_name) as user_name, orders.order_id
                                FROM return_authorization LEFT JOIN orders on return_authorization.order_id=orders.order_id
                                LEFT JOIN customers ON customers.user_id=orders.user_id
                                LEFT JOIN accounts on accounts.user_id=orders.user_id
                                WHERE return_authorization.return_status='pending'
                                ORDER BY applied_date ASC LIMIT 4''')
            refund_request = cursor.fetchall()

            todaydate = date.today()
            cursor.execute('select max(fresh_date) from daily_fresh_subscriptions')
            max_fresh_date = cursor.fetchone()
            if max_fresh_date[0]< todaydate:
                fresh = 'yes'
            else:
                fresh = 'no'


            return render_template('admin-dashboard.html', admin_info=admin_info, recent_orders=orders, 
                                   total_customers=total_customers, total_orders=total_orders, total_revenue=total_revenue, 
                                   total_subscriptions=total_subscriptions, recent_products=recent_products, recent_boxes=recent_boxes, 
                                   staff_list=staff_list, recent_customers=recent_customers, recent_accounts=recent_accounts, 
                                   recent_news=recent_news, refund_request=refund_request, fresh=fresh, recent_subscription=recent_subscription)
        else:
            # Handle case where manager details are not found
            return render_template('error.html', error="Access denied. You do not have permission to access this page.")
      
    # User is not logged in redirect to home page
    return redirect(url_for('logout'))


@app.route('/admin/password-update', methods=['GET', 'POST'])
def admin_password_update():
    role = session.get('role')
    cart = session.get('cart', {})

    # Ensure the user is logged in and has the right role
    if 'loggedin' not in session or session.get('role') != 1:
        return redirect(url_for('logout'))

    user_id = session['user_id']
    msg = ''
    
    # Establish database connection
    cursor = getCursor()

    # Fetch admin information for use in the template
    cursor.execute('''
        SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
        FROM roles 
        JOIN users ON roles.role_id = users.role_id 
        JOIN staff ON staff.user_id = users.user_id 
        WHERE users.user_id = %s
    ''', (user_id,))
    admin_info = cursor.fetchone()

    if request.method == 'POST':
        old_password = request.form.get('oldPassword')
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')

        # Fetch the old hashed password from the database
        cursor.execute('SELECT password_hashed FROM users WHERE user_id = %s', (user_id,))
        stored_password_hash = cursor.fetchone()[0]

        # Validate the old password
        if not hashing.check_value(stored_password_hash, old_password, salt='c639'):
            msg = 'Old password is incorrect!'
        elif not new_password or not confirm_password:
            msg = 'Please fill all the fields!'
        elif new_password != confirm_password:
            msg = 'New password and confirm password do not match!'
        elif not (len(new_password) >= 8 and re.search(r'[A-Z]', new_password) and re.search(r'\d', new_password)):
            msg = 'Password must be at least 8 characters long and contain an uppercase letter and a number.'
        else:
            hashed_new_password = hashing.hash_value(new_password, salt='c639')
            cursor.execute('UPDATE users SET password_hashed = %s WHERE user_id = %s', (hashed_new_password, user_id))
            msg = 'Password has been successfully updated!'
            return redirect(url_for('admin_profile',cart=cart,location=session['location'][0],role=role,msg=msg, admin_info=admin_info))  # Redirect to the admin profile page after successful update

    # If admin_info is None, handle appropriately
    if not admin_info:
        return render_template('error.html', error="Admin details not found")

    return render_template('admin-password_update.html', cart=cart,location=session['location'][0], role=role,msg=msg, admin_info=admin_info)


@app.route('/admin/stafflist',methods=['get','post'])
def admin_stafflist():
    role = session.get('role')
    if 'loggedin' in session and role == 1:
        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()
        #get all depots info
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()
        # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (2,))
        profile_image_url = cursor.fetchone()
        if request.method=='GET':

            cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where role_id=%s or role_id=%s',(2,3,))
            staffinfo= cursor.fetchall()
           
            return render_template('admin_staff_list.html', msg=msg,depot_all=depot_all,location=session['location'][0], admin_info=admin_info,allprofile=staffinfo, profile_image_url=profile_image_url)
        else:
            searchinput = request.form['searchinput']
            all= searchinput.split()
            selected_depot_id = request.form.get('depot_id')
            if selected_depot_id!='all':
                cursor=getCursor()
                cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.depot_id=%s and (role_id=%s or role_id=%s)',(selected_depot_id,2,3,))
                allprofile=cursor.fetchall()
                return render_template('admin_staff_list.html',msg=msg, depot_all=depot_all,location=session['location'][0], admin_info=admin_info,allprofile=allprofile, profile_image_url=profile_image_url)

            elif len(all)==0:
                cursor=getCursor()
                cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where role_id=%s or role_id=%s',(2,3,))
                allprofile=cursor.fetchall()
                return render_template('admin_staff_list.html', msg=msg,depot_all=depot_all,location=session['location'][0], admin_info=admin_info,allprofile=allprofile, profile_image_url=profile_image_url)

            elif len(all)==1:
                cursor=getCursor()
                parameter = ("%"+all[0]+"%")
                cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where (role_id=%s or role_id=%s) and (given_name like %s or family_name like %s)',(2,3,parameter,parameter,))
                allprofile=cursor.fetchall()
                return render_template('admin_staff_list.html',msg=msg,depot_all=depot_all, location=session['location'][0], admin_info=admin_info,allprofile=allprofile, profile_image_url=profile_image_url)

            elif len(all)==2:
                cursor=getCursor()
                parameter1 = ("%"+all[0]+"%")
                parameter2 = ("%"+all[1]+"%")
                cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where (role_id=%s or role_id=%s) and ((given_name like %s and family_name like %s) or (given_name like %s and family_name like %s))',(2,3,parameter1,parameter2,parameter2,parameter1,))
                allprofile=cursor.fetchall()
                return render_template('admin_staff_list.html',msg=msg,depot_all=depot_all, location=session['location'][0], admin_info=admin_info,allprofile=allprofile, profile_image_url=profile_image_url)
    else: 
        return redirect(url_for('logout'))


@app.route("/admin/staffprofile/<user_id1>")
def admin_staff_profile(user_id1):
    role = session.get('role')
    cart = session.get('cart', {})

    if 'loggedin' in session and role == 1:
        cursor =  getCursor()
        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()
        # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()

        cursor.execute("""
                         select s.*, d.location,u.status,r.responsibility_name,roles.role_name
                            from staff as s 
                            join depots as d 
                            on s.depot_id=d.depot_id 
                            join users as u 
                            on s.user_id=u.user_id 
                            join roles on roles.role_id=u.role_id
                            join responsibilities as r 
                            on s.responsibility_id=r.responsibility_id 
                            where s.user_id=%s 
                       """
                       ,(user_id1,))
        profile = cursor.fetchone()
        return render_template ('admin-staff-profile.html', cart=cart,msg=msg,location=session['location'][0], admin_info=admin_info,profile=profile, profile_image_url=profile_image_url)       
    else: 
        return redirect(url_for('logout'))
 
@app.route("/admin/changestaffprofile/<user_id1>",methods=["GET","POST"])
def admin_change_staff_profile(user_id1):
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg=""
    role = session.get('role')
    user_id = session['user_id']

    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    cursor.execute('select * from responsibilities')
    resp_all = cursor.fetchall()
    cursor.execute('select * from depots')
    depot_all = cursor.fetchall()
    cursor.execute('select * from roles')
    role_all = cursor.fetchall()
    if 'loggedin' in session and role == 1:
        cursor=getCursor()

        # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()

        if request.method=='GET':
            
            cursor.execute("""
                         select s.*, d.location,u.status,r.responsibility_name,roles.role_name,u.role_id
                            from staff as s 
                            join depots as d 
                            on s.depot_id=d.depot_id 
                            join users as u 
                            on s.user_id=u.user_id 
                            join roles on roles.role_id=u.role_id
                            join responsibilities as r 
                            on s.responsibility_id=r.responsibility_id 
                            where s.user_id=%s 
                       """
                       ,(user_id1,))           
            profile=cursor.fetchone()
            return render_template("admin-change-staff-profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)
    
        else:

            title = request.form['title']
            first_name = request.form['first_name']
            family_name = request.form['family_name']
            phone_number = request.form['phone']
            email = request.form['email']
            status = request.form['status']
            depot  = request.form['depot']
            resp =request.form['resp']
            role = request.form['role']
            files = request.files.getlist('image1') 
        #files = request.files('image1')  

            if files:

                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        fixed_filepath = filepath.replace("\\","/")
                        file.save(fixed_filepath)

                        cursor = getCursor()
                        cursor.execute('update users set status=%s,role_id=%s where user_id=%s',(status,role,user_id1,))
                        cursor.execute("UPDATE staff set title=%s,given_name=%s,family_name=%s,email=%s,phone_number=%s,pic=%s,responsibility_id=%s,depot_id=%s where user_id=%s",(title,first_name,family_name,email,phone_number,fixed_filepath,resp,depot,user_id1,))
                        cursor.execute("""SELECT pic FROM customers WHERE user_id = %s""", (user_id1,))
    
                        profile_image_url = cursor.fetchone()
                        msg="Profile has been successfully updated!"
                        cursor.execute("""
                         select s.*, d.location,u.status,r.responsibility_name,roles.role_name
                            from staff as s 
                            join depots as d 
                            on s.depot_id=d.depot_id 
                            join users as u 
                            on s.user_id=u.user_id 
                            join roles on roles.role_id=u.role_id
                            join responsibilities as r 
                            on s.responsibility_id=r.responsibility_id 
                            where s.user_id=%s 
                       """
                       ,(user_id1,))           
                        profile=cursor.fetchone()

                        return redirect(url_for('admin_staff_profile',user_id1=user_id1,msg=msg))
                        #return render_template("admin-change-staff-profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)


                    else: #if no pic uploaded, then no need to update image in database
                        cursor = getCursor()
                        cursor.execute('update users set status=%s,role_id=%s where user_id=%s',(status,role,user_id1,))

                        cursor.execute("UPDATE staff set title=%s,given_name=%s,family_name=%s,email=%s,phone_number=%s,responsibility_id=%s,depot_id=%s where user_id=%s",(title,first_name,family_name,email,phone_number,resp,depot,user_id1,))

                        msg="Profile has been successfully updated!"
                        cursor.execute("""
                         select s.*, d.location,u.status,r.responsibility_name,roles.role_name
                            from staff as s 
                            join depots as d 
                            on s.depot_id=d.depot_id 
                            join users as u 
                            on s.user_id=u.user_id 
                            join roles on roles.role_id=u.role_id
                            join responsibilities as r 
                            on s.responsibility_id=r.responsibility_id 
                            where s.user_id=%s 
                       """
                       ,(user_id1,))           
                        profile=cursor.fetchone()


                        return redirect(url_for('admin_staff_profile',user_id1=user_id1,msg=msg))

                        # cursor.execute('select p.*,u.status from profiles as p join users as u on p.user_id=u.user_id where p.user_id=%s',(user_id1,))
                        # profile=cursor.fetchone()
                        #return render_template("admin-change-staff-profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)
    else: 
        return redirect(url_for('logout'))
    
@app.route("/admin/deletestaffimg/<user_id1>")
def admin_deletestaffimg(user_id1):
    user_id = session['user_id']

    cursor=getCursor()
    #update pic to default one if deleting
    cursor.execute("update staff set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",user_id1,))
    msg="Image has been successfully deleted!"
    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    cursor.execute('select * from responsibilities')
    resp_all = cursor.fetchall()
    cursor.execute('select * from depots')
    depot_all = cursor.fetchall()
    cursor.execute('select * from roles')
    role_all = cursor.fetchall()
    cursor.execute("""
                         select s.*, d.location,u.status,r.responsibility_name,roles.role_name
                            from staff as s 
                            join depots as d 
                            on s.depot_id=d.depot_id 
                            join users as u 
                            on s.user_id=u.user_id 
                            join roles on roles.role_id=u.role_id
                            join responsibilities as r 
                            on s.responsibility_id=r.responsibility_id 
                            where s.user_id=%s 
                       """
                       ,(user_id1,))           
    profile=cursor.fetchone()
    cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
    profile_image_url = cursor.fetchone()
    return render_template("admin-change-staff-profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)

@app.route("/admin/addstaff",methods=["GET","POST"])
def admin_add_staff():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    if 'loggedin' in session and role == 1:
        
        user_id = session['user_id']
        cursor=getCursor()
            # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()
        if request.method=='GET':
                #give it a new staff_id
            cursor.execute('select max(staff_id) from staff')
            max_id = cursor.fetchone()
            new_staff_id=max_id[0]+1
            cursor.execute('select * from responsibilities')
            resp_list = cursor.fetchall()

            return render_template('admin-add-staff.html', location=session['location'][0], admin_info=admin_info,msg='',depot_all=depot_all,resp_list=resp_list,new_staff_id=new_staff_id,profile_image_url=profile_image_url )
        else:
            cursor.execute('select * from responsibilities')
            resp_list = cursor.fetchall()
            cursor.execute('select s.depot_id,location from staff as s join depots as d on s.depot_id=d.depot_id where user_id=%s',(user_id,))
            depot_info=cursor.fetchone()
            username = request.form['username']
            password1 = request.form['password1']
            password2 = request.form['password2']
            title = request.form['title']
            first_name = request.form['first_name']
            family_name = request.form['family_name']
            phone_number = request.form['phone']
            email = request.form['email']
            status = request.form['status']
            responsibility1 =request.form['responsibility1']
            depot_id=request.form['depot_id']
            files = request.files.getlist('image1')  

            #Check if account exists using MySQL
            cursor = getCursor()
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            account = cursor.fetchone()
            cursor=getCursor()
            cursor.execute('select * from staff where email=%s',(email,))
            email_all = cursor.fetchone()
            #If account exists show error and validation checks
            if account:
                msg = 'Account/email already exists!'
            elif email_all:
                msg='Account/email already exists!'
            elif password1 !=password2:
                msg="Password doesn't match"
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                msg = 'Invalid email address!'
            elif not re.match(r'[A-Za-z0-9]+', username):
                msg = 'Username must contain only characters and numbers!'
            elif not username or not password1 or not email:
                msg = 'Please fill out the form!'
            else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
                hashed = hashing.hash_value(password1, salt='c639')
                cursor.execute('select max(user_id) from users')
                max_user_id=cursor.fetchone()
                if max_user_id[0] is None:
                    new_userid=1
                else:
                    new_userid=max_user_id[0]+1

                cursor.execute('INSERT INTO users VALUES (%s, %s, %s,%s,%s)', (new_userid,username, hashed,3,status,))

                #get new staff id
                cursor.execute('select max(staff_id) from staff')
                max_id = cursor.fetchone()
                staff_id=max_id[0]+1


                if files:

                    for file in files:
                    #if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        if filename=='':  # if no new image uploaded
                            cursor = getCursor()
                            cursor.execute('INSERT INTO staff VALUES (%s, %s, %s,%s,%s,%s, %s,%s,%s,%s)', (staff_id,new_userid,title,first_name,family_name,email,phone_number,"app/static/assets/img/avatar.jpg",responsibility1,depot_id,))

                        else:
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            fixed_filepath = filepath.replace("\\","/")
                            file.save(fixed_filepath)

                            cursor = getCursor()
                            cursor.execute('INSERT INTO staff VALUES (%s, %s, %s,%s,%s,%s, %s,%s,%s, %s)', (staff_id,new_userid,title,first_name,family_name,email,phone_number,fixed_filepath,responsibility1,depot_id,))
                msg="Profile has been successfully added!"
            return redirect(url_for('admin_stafflist',msg=msg))
            #return render_template("admin-add-staff.html", depot_all=depot_all,location=session['location'][0],  admin_info=admin_info,depot_info=depot_info,resp_list=resp_list,new_staff_id='',msg=msg, profile_image_url=profile_image_url)
    # else: 
    #     return redirect(url_for('error'))

#admin customer list
@app.route('/admin/customerlist',methods=['get','post'])
def admin_customerlist():
    role = session.get('role')
    if 'loggedin' in session and role == 1:
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()
        #get all depots info
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()
        # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (2,))
        profile_image_url = cursor.fetchone()
        if request.method=='GET':

            cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4
                      """)
            customerinfo= cursor.fetchall()
           
            return render_template('admin_customer_list.html', depot_all=depot_all,location=session['location'][0], admin_info=admin_info,allprofile=customerinfo, profile_image_url=profile_image_url)
        else:
            searchinput = request.form['searchinput']
            all= searchinput.split()
            selected_depot_id = request.form.get('depot_id')
            if selected_depot_id!='all':
                cursor=getCursor()
                cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4 and depot_id=%s   
                      """,(selected_depot_id,))                
                allprofile=cursor.fetchall()
                return render_template('admin_customer_list.html', depot_all=depot_all,location=session['location'][0], admin_info=admin_info,allprofile=allprofile, profile_image_url=profile_image_url)
                 
            elif len(all)==0:
                cursor=getCursor()
                cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4      
                      """)                
                allprofile=cursor.fetchall()
                return render_template('admin_customer_list.html', depot_all=depot_all,location=session['location'][0], admin_info=admin_info,allprofile=allprofile, profile_image_url=profile_image_url)
            
            elif len(all)==1:
                cursor=getCursor()
                parameter = ("%"+all[0]+"%")
                cursor.execute(""" 
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4   
                        and (given_name like %s or family_name like %s)""",(parameter,parameter,))
                allprofile=cursor.fetchall()
                return render_template('admin_customer_list.html',depot_all=depot_all ,location=session['location'][0], admin_info=admin_info,allprofile=allprofile, profile_image_url=profile_image_url)

            elif len(all)==2:
                cursor=getCursor()
                parameter1 = ("%"+all[0]+"%")
                parameter2 = ("%"+all[1]+"%")
                cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4 
                                and ((given_name like %s and family_name like %s) or (given_name like %s and family_name like %s))""",
                                (parameter1,parameter2,parameter2,parameter1,))
                allprofile=cursor.fetchall()
                return render_template('admin_customer_list.html', depot_all=depot_all,location=session['location'][0], admin_info=admin_info,allprofile=allprofile, profile_image_url=profile_image_url)
    else: 
        return redirect(url_for('logout'))


@app.route("/admin/customerprofile/<user_id1>")
def admin_customer_profile(user_id1):
    role = session.get('role')
    if 'loggedin' in session and role == 1:
        cursor =  getCursor()
        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()
        # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()

        cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where c.user_id=%s 
                       """
                       ,(user_id1,))
        profile = cursor.fetchone()
        return render_template ('admin-customer-profile.html', msg=msg,location=session['location'][0], admin_info=admin_info,profile=profile, profile_image_url=profile_image_url)       
    else: 
        return redirect(url_for('logout'))
 
@app.route("/admin/changecustomerprofile/<user_id1>",methods=["GET","POST"])
def admin_change_customer_profile(user_id1):
    msg=""
    role = session.get('role')
    user_id = session['user_id']

    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()

    cursor.execute('select * from depots')
    depot_all = cursor.fetchall()

    if 'loggedin' in session and role == 1:
        cursor=getCursor()

        # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()

        if request.method=='GET':
            
            cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where c.user_id=%s 
                       """
                       ,(user_id1,))
            profile = cursor.fetchone()
            return render_template("admin-change-customer-profile.html", location=session['location'][0], depot_all=depot_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)
    
        else:

            title = request.form['title']
            first_name = request.form['first_name']
            family_name = request.form['family_name']
            phone_number = request.form['phone']
            email = request.form['email']
            status = request.form['status']
            depot  = request.form['depot']
            files = request.files.getlist('image1') 
        #files = request.files('image1')  

            if files:

                for file in files:
                    # if pic uploaded
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        fixed_filepath = filepath.replace("\\","/")
                        file.save(fixed_filepath)

                        cursor = getCursor()
                        cursor.execute('update users set status=%s where user_id=%s',(status,user_id1,))
                        cursor.execute("UPDATE customers set title=%s,given_name=%s,family_name=%s,email=%s,phone_number=%s,pic=%s,city=%s where user_id=%s",(title,first_name,family_name,email,phone_number,fixed_filepath,depot,user_id1,))
                        cursor.execute("""SELECT pic FROM customers WHERE user_id = %s""", (user_id1,))
    
                        profile_image_url = cursor.fetchone()
                        msg="Profile has been successfully updated!"
                        cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where c.user_id=%s 
                       """
                       ,(user_id1,))
                        profile = cursor.fetchone()
                        return redirect(url_for('admin_customer_profile',user_id1=user_id1,msg=msg))

                        #return render_template("admin-change-customer-profile.html", location=session['location'][0], depot_all=depot_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)


                    else: #if no pic uploaded, then no need to update image in database
                        cursor = getCursor()
                        cursor.execute('update users set status=%s where user_id=%s',(status,user_id1,))

                        cursor.execute("UPDATE customers set title=%s,given_name=%s,family_name=%s,email=%s,phone_number=%s,city=%s where user_id=%s",(title,first_name,family_name,email,phone_number,depot,user_id1,))

                        msg="Profile has been successfully updated!"
                        cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where c.user_id=%s 
                       """
                       ,(user_id1,))
                        profile = cursor.fetchone()


                        return redirect(url_for('admin_customer_profile',user_id1=user_id1,msg=msg))
                        # cursor.execute('select p.*,u.status from profiles as p join users as u on p.user_id=u.user_id where p.user_id=%s',(user_id1,))
                        # profile=cursor.fetchone()
                        #return render_template("admin-change-customer-profile.html", location=session['location'][0], depot_all=depot_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)
    else: 
        return redirect(url_for('logout'))
    
@app.route("/admin/deletecustomerimg/<user_id1>")
def admin_deletecustomerimg(user_id1):
    user_id = session['user_id']

    cursor=getCursor()
    # update pic to default one
    cursor.execute("update customers set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",user_id1,))
    msg="Image has been successfully deleted!"
    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    cursor.execute('select * from responsibilities')
    resp_all = cursor.fetchall()
    cursor.execute('select * from depots')
    depot_all = cursor.fetchall()
    cursor.execute('select * from roles')
    role_all = cursor.fetchall()
    cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where c.user_id=%s 
                       """
                       ,(user_id1,))
    profile = cursor.fetchone()
    cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
    profile_image_url = cursor.fetchone()
    return render_template("admin-change-customer-profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)

@app.route('/admin/profileupdate',methods= ['get','post'])
def admin_profileupdate():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor=getCursor()
    cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
    profile_image_url = cursor.fetchone()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    if 'loggedin' in session and role == 1: 


        if request.method=='GET':
            
            msg = ''
            cursor=getCursor()
            cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.user_id=%s',(user_id,))
            profileinfo= cursor.fetchone()


            return render_template("admin-profile-update.html", location=session['location'][0], admin_info=admin_info,profileinfo=profileinfo,msg=msg,profile_image_url= profile_image_url)
        else:
            title = request.form['title']
            first_name = request.form['first_name']
            family_name = request.form['family_name']
            phone_number = request.form['phone']
            email = request.form['email']
            #depot=request.form['city']
            files = request.files.getlist('image1')



            if files:

                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        fixed_filepath = filepath.replace("\\","/")
                        file.save(fixed_filepath)

                        cursor = getCursor()
                        cursor.execute("UPDATE staff set title=%s,given_name=%s,family_name=%s,email=%s,phone_number=%s,pic=%s where user_id=%s",(title,first_name,family_name,email,phone_number,fixed_filepath,user_id,))

                        msg="Profile has been successfully updated!"

                        return redirect(url_for('admin_profile',msg=msg))
                        #return render_template("admin-profile-update.html", location=session['location'][0], admin_info=admin_info,profileinfo="",msg=msg,profile_image_url=profile_image_url)

                    else: #if no pic uploaded, then no need to update image in database
                        cursor = getCursor()
                        cursor.execute("UPDATE staff set title=%s,given_name=%s,family_name=%s,email=%s,phone_number=%s where user_id=%s",(title,first_name,family_name,email,phone_number,user_id,))
                        msg="Profile has been successfully updated!"
                        
                        return redirect(url_for('admin_profile',msg=msg))

                        #return render_template("admin-profile-update.html", location=session['location'][0], admin_info=admin_info,profileinfo="",msg=msg,profile_image_url=profile_image_url)
    # else: 
    #     return redirect(url_for('error'))



@app.route("/admin/deleteimg")
def admin_deleteimg():
    cursor=getCursor()
    role = session.get('role')
    user_id = session.get('user_id')
    # update pic to default one if deleting
    cursor.execute("update staff set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",user_id,))
    msg="Image has been successfully deleted!"
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    return render_template("admin-profile-update.html",  location=session['location'][0], admin_info=admin_info,profileinfo="",msg=msg,profile_image_url='')



@app.route("/admin/profile")
def admin_profile():
    role = session.get('role')

    if 'loggedin' in session and role==1:
        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''
        cursor =  getCursor()
        user_id = session.get('user_id')

        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                                FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                                INNER JOIN staff ON staff.user_id = users.user_id 
                                WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()

        cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.user_id=%s',(user_id,))
        profileinfo= cursor.fetchone()

        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()
        
        return render_template ('admin_profile.html', msg=msg, role=role,admin_info=admin_info,profile=profileinfo, profile_image_url=profile_image_url, location=session['location'][0])

    else:
        return redirect(url_for('logout'))   

@app.route('/admin/account-holder-list',methods=['GET','POST'])
def admin_account_holder_list():
    role = session.get('role')
    if 'loggedin' in session and role == 1:
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute("""SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic FROM roles INNER JOIN users ON roles.role_id = users.role_id INNER JOIN staff ON staff.user_id = users.user_id WHERE users.user_id = %s""", (user_id,))
        admin_info = cursor.fetchone()
      
        if request.method=='GET':

            cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5""")
            accountHolderList= cursor.fetchall()
           
            return render_template('admin-account_holder_list.html',admin_info=admin_info,accountHolderList=accountHolderList)
        else:
            searchinput = request.form['searchinput']
            all= searchinput.split()
            if len(all)==0:
                cursor=getCursor()
                cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5""")                
                accountHolderList=cursor.fetchall()
                return render_template('admin-account_holder_list.html',admin_info=admin_info,accountHolderList=accountHolderList)

            elif len(all)==1:
                cursor=getCursor()
                parameter = ("%"+all[0]+"%")
                cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5 AND a.account_name LIKE %s""",(parameter,))
                accountHolderList=cursor.fetchall()
                return render_template('admin-account_holder_list.html',admin_info=admin_info,accountHolderList=accountHolderList)

            
    else: 
        return redirect(url_for('logout'))


@app.route('/admin/account-holder-list/profile',methods=['get','post'])
def admin_view_account_holder_profile():
    
    role = session.get('role')
    account_holder_id = request.args.get('account_holder_id')

    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg = ''
    
    if 'loggedin' in session and role == 1:
       cursor =  getCursor()
       user_id = session['user_id']
       cursor.execute("""SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic FROM roles INNER JOIN users ON roles.role_id = users.role_id INNER JOIN staff ON staff.user_id = users.user_id WHERE users.user_id = %s""", (user_id,))
       admin_info = cursor.fetchone()

       cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name, u.username FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE a.account_id = %s""", (account_holder_id,))

       profile= cursor.fetchone()


       return render_template ('admin-account_holder_profile.html',admin_info=admin_info, profile=profile, msg=msg)
    
    else:
        return redirect(url_for('login'))



@app.route('/admin/account-holder-list/profile/update',methods=['GET','POST'])

def admin_account_holder_profile_update():

    role = session.get('role')
    msg=''
    cursor=getCursor()
    cursor.execute('select * from depots')
    depot_all=cursor.fetchall()
    user_id = session['user_id']
    account_user_id = request.args.get('account_user_id')
    print(account_user_id)

    cursor.execute("""SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic FROM roles INNER JOIN users ON roles.role_id = users.role_id INNER JOIN staff ON staff.user_id = users.user_id WHERE users.user_id = %s""", (user_id,))
    admin_info = cursor.fetchone()


    if 'loggedin' in session and role == 1:
       

        
       

       if request.method=='GET':
            
            cursor.execute("""select a.*,d.location,u.status,roles.role_name from accounts as a join depots as d on a.city = d.depot_id join users as u on a.user_id=u.user_id join roles on u.role_id = roles.role_id where a.user_id=%s """,(account_user_id,))
            profile = cursor.fetchone()
           
            return render_template("admin-change_account_holder_profile.html", location=session['location'][0], depot_all=depot_all,admin_info=admin_info,profileinfo=profile,msg=msg)
    
       else:

            name = request.form['name']
            phone_number = request.form['phone']
            email = request.form['email']
            status = request.form['status']
            depot  = request.form['depot']
            files = request.files.getlist('image1') 
      

            if files:

                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        fixed_filepath = filepath.replace("\\","/")
                        file.save(fixed_filepath)

                        cursor = getCursor()
                        
                        cursor.execute('UPDATE users set status=%s where user_id=%s',(status,account_user_id,))
                        cursor.execute("UPDATE accounts set account_name=%s,email=%s,phone_number=%s,pic=%s,city=%s where user_id=%s",(name,email,phone_number,fixed_filepath,depot,account_user_id,))
                        cursor.execute("""SELECT pic FROM accounts WHERE user_id = %s""", (account_user_id,))
                        profile_image_url = cursor.fetchone()
    
                        msg="Profile has been successfully updated!"
                        cursor.execute("""select a.*, d.location,u.status,roles.role_name from accounts as a
                        join depots as d on a.city = d.depot_id
                        join users as u on a.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where a.user_id=%s 
                       """
                       ,(account_user_id,))
                        profile = cursor.fetchone()
                        #return redirect(url_for('admin_view_account_holder_profile',msg = msg))
                        return redirect(url_for("admin_view_account_holder_profile", msg=msg, account_holder_id=profile[0]))


                    else: #if no pic uploaded, then no need to update image in database
                        cursor = getCursor()
                        cursor.execute('update users set status=%s where user_id=%s',(status,account_user_id,))

                        cursor.execute("UPDATE accounts set account_name=%s,email=%s,phone_number=%s,city=%s where user_id=%s",(name,email,phone_number,depot,account_user_id,))

                        msg="Profile has been successfully updated!"
                        cursor.execute("""
                        select a.*,d.location,u.status,roles.role_name from accounts as a
                        join depots as d on a.city = d.depot_id
                        join users as u on a.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where a.user_id=%s 
                       """,(account_user_id,))
                        profile = cursor.fetchone()

                        #return redirect(url_for('admin_view_account_holder_profile',msg = msg))

                        return redirect(url_for("admin_view_account_holder_profile", msg=msg, account_holder_id=profile[0]))
 
    else:
        return redirect(url_for('login'))



@app.route("/admin/account-holder-list/profile/delete-account-holder-img")
def admin_delete_account_holder_img():
    user_id = session['user_id']

    account_user_id = request.args.get('account_user_id')

    cursor=getCursor()
    # update pic to default one if deleting
    cursor.execute("update accounts set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",account_user_id,))
    msg="Image has been successfully deleted!"
    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    cursor.execute('select * from responsibilities')
    resp_all = cursor.fetchall()
    cursor.execute('select * from depots')
    depot_all = cursor.fetchall()
    cursor.execute('select * from roles')
    role_all = cursor.fetchall()
    cursor.execute("""
                        select a.*,d.location,u.status,roles.role_name from accounts as a
                        join depots as d on a.city = d.depot_id
                        join users as u on a.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where a.user_id=%s 
                       """
                       ,(account_user_id,))
    profile = cursor.fetchone()
    cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
    profile_image_url = cursor.fetchone()
    return render_template("admin-change_account_holder_profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,admin_info=admin_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)

@app.route('/admin/product-list', methods=['GET', 'POST'])
def admin_product_list():
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg= ''
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor = getCursor()
    # Fetch admin information for use of admin.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()

    # Fetch all distinct locations from the database
    cursor.execute('''SELECT DISTINCT location FROM depots''')
    locations = [row[0] for row in cursor.fetchall()]

    # Fetch all distinct categories from the database
    cursor.execute('''SELECT DISTINCT product_category_name FROM product_categories where product_category_id !="7" and product_category_id !="8"''')
    categories = [row[0] for row in cursor.fetchall()]

    # Check if the user is logged in and has admin role
    if 'loggedin' in session and role == 1:
        # If it's a POST request, process the form data
        # filter
        if request.method == 'POST':
            searchinput = request.form.get('searchinput', '').strip()
            selected_location = request.form.get('location')
            selected_category = request.form.get('category')
        else:
            # If it's a GET request, get search input, selected location, and selected category from query parameters
            searchinput = request.args.get('searchinput', '').strip()
            selected_location = request.args.get('location')
            selected_category = request.args.get('category')

        # If search input is provided, perform search in the database
        if searchinput:
            query = '''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id
                        FROM product p 
                        LEFT JOIN products pro ON p.SKU = pro.SKU
                        LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                        LEFT JOIN stock on stock.product_id = pro.product_id 
                        LEFT JOIN depots d on d.depot_id = pro.depot_id
                        Left join units on p.unit = units.unit_id
                        WHERE product_status="1" AND pro.product_category_id != "7" AND pro.product_category_id != "8" AND (p.SKU LIKE %s OR pc.product_category_name LIKE %s OR p.product_name LIKE %s)
                        ORDER BY pro.product_id DESC'''
            params = (f'%{searchinput}%', f'%{searchinput}%', f'%{searchinput}%')
            if selected_location:
                query += " AND d.location = %s"
                params += (selected_location,)
            if selected_category and selected_category != 'all':
                query += " AND pc.product_category_name = %s"
                params += (selected_category,)
            cursor.execute(query, params)
            products = cursor.fetchall()
        # If no search input is provided, fetch all products
        else:
            if selected_location:
                cursor.execute('''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM product p 
                                    LEFT JOIN products pro ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id
                                    WHERE product_status="1"  AND pro.product_category_id != "7" AND pro.product_category_id != "8"  AND d.location = %s
                                    ORDER BY pro.product_id DESC''', (selected_location,))
            elif selected_category:
                cursor.execute('''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM product p 
                                    LEFT JOIN products pro ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id
                                    WHERE product_status="1" AND product_origins != "Digital card" AND pro.product_category_id != "7" AND pro.product_category_id != "8"  AND pc.product_category_name = %s
                                    ORDER BY pro.product_id DESC''', (selected_category,))
            else:
                cursor.execute('''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM product p 
                                    LEFT JOIN products pro ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id
                                    WHERE product_status="1" AND product_origins != "Digital card" AND pro.product_category_id != "7" AND pro.product_category_id != "8" 
                                    ORDER BY pro.product_id DESC''')
            products = cursor.fetchall()

        # Sorting logic based on query parameters
        sort_by = request.args.get('sort_by')
        if sort_by:
            reverse = request.args.get('reverse')  # Get the 'reverse' parameter from the request
            if reverse == 'True':
                reverse = True
            else:
                reverse = False

            if sort_by == 'SKU':
                products.sort(key=lambda x: x[0], reverse=reverse)
            elif sort_by == 'Category':
                products.sort(key=lambda x: x[1], reverse=reverse)
            elif sort_by == 'Product Name':
                products.sort(key=lambda x: x[2], reverse=reverse)
            elif sort_by == 'Price':
                products.sort(key=lambda x: x[3], reverse=reverse)
            elif sort_by == 'Unit':
                products.sort(key=lambda x: x[4], reverse=reverse)
            elif sort_by == 'Stock Quantity':
                products.sort(key=lambda x: x[5] if x[5] is not None else 0, reverse=reverse)
            elif sort_by == 'Location':
                products.sort(key=lambda x: x[6], reverse=reverse)

        # Render template with the list of products, locations, and search input
        return render_template('admin-product_list.html', products=products, admin_info=admin_info, role=role, locations=locations, categories=categories, searchinput=searchinput, selected_location=selected_location, selected_category=selected_category, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))
    
@app.route('/admin/product-list/product', methods=["GET","POST"])
def admin_product_details():
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor=getCursor()
    # Fetch admin information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    if 'loggedin' in session and role == 1: 
        cursor=getCursor()

        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''

        product_id = request.args.get('product_id')

        cursor.execute("""SELECT p.SKU, p.product_name, pro.product_price, units.unit_name, p.pic, p.product_des, p.product_origins, d.location, pro.product_id 
                       FROM product p 
                       LEFT JOIN products pro ON p.SKU = pro.SKU 
                       LEFT JOIN depots d on d.depot_id = pro.depot_id
                       left join units on p.unit = units.unit_id
                       WHERE pro.product_id = %s""", (product_id,)) 
        product = cursor.fetchall()

        return render_template('admin-product_details.html', admin_info=admin_info, product=product, role=role, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))
   
@app.route('/admin/product-list/add-product', methods = ['GET', 'POST'])
def admin_add_new_product():
    role = session.get('role')
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories where product_category_id !="7" and product_category_id !="8"')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    if 'loggedin' in session and role == 1:
        if request.method == 'GET':

            if request.args.get('msg'):
                msg = request.args.get('msg')
            else:
                msg = ''
            cursor.execute('SELECT * FROM units WHERE status = "Active";')
            list_unit = cursor.fetchall()

            cursor.execute('SELECT max(product_id) FROM products')
            max_product_id = cursor.fetchone()
            new_product_id = max_product_id[0]+1 if max_product_id[0] is not None else 1
            cursor.execute('SELECT * FROM depots')
            depot_info = cursor.fetchall()
            return render_template('admin-add_new_product.html', list_unit=list_unit, msg=msg, new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, admin_info=admin_info, depot_info=depot_info, role=role )
        else:
            new_product_id = request.form.get('new_product_id')
            product_category_id = request.form.get('product_category_id')
            product_name = request.form.get('product_name')
            sku = request.form.get('sku')
            unit = request.form.get('unit')
            product_des = request.form.get('product_des')
            product_price = request.form.get('product_price')
            promotion_type_id = request.form.get('promotion_type_id')
            product_origins = request.form.get('product_origins')
            depot_id = request.form.get('depot_id')
            stock_quantity = request.form.get('stock_quantity')
            files = request.files.getlist('image1')

            # Check if product with the same SKU already exists
            cursor.execute('SELECT * FROM products WHERE sku = %s', (sku,))
            existing_product = cursor.fetchone()
            if existing_product:
                msg = 'Product with this SKU already exists!'
                cursor.execute('SELECT max(product_id) FROM products')
                max_product_id = cursor.fetchone()
                new_product_id = max_product_id[0] + 1 if max_product_id[0] is not None else 1
                location = session['location'][0]
                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (location,))
                depot_id = cursor.fetchall()
                return redirect(url_for('admin_add_new_product', new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, admin_info=admin_info, depot_id=depot_id[0], msg=msg, role=role))
            if files:
                for file in files:
                    if file:
                        if allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            fixed_filepath = filepath.replace("\\", "/")
                            file.save(fixed_filepath)
                        else:
                            msg = 'Invalid file format! Please upload files with extensions: png, jpg, jpeg, gif.'
                            return redirect( url_for('admin_add_new_product', msg=msg))
                    else:
                        fixed_filepath = "app/static/assets/img/product_avatar.png"

            cursor.execute('INSERT INTO product VALUES (%s, %s, %s, %s, %s, %s);', (product_name, sku, unit, fixed_filepath, product_des, product_origins))
            cursor.execute('INSERT INTO union_skus VALUES (%s, "product");', (sku, ))
            cursor.execute('INSERT INTO products VALUES (%s, %s, %s, %s, %s, %s, "1");', (new_product_id, sku, product_price, product_category_id, promotion_type_id, depot_id))
            cursor.execute('Insert into stock values (%s, %s, %s);', (new_product_id, depot_id, stock_quantity,))
            msg = 'Product has been added successfully!'
            return redirect(url_for('admin_product_list', msg=msg))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/admin/product-list/product/update', methods = ['GET', 'POST'])
def admin_edit_product():
    role = session.get('role')
    msg=''
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories where product_category_id !="7" and product_category_id !="8"')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    if 'loggedin' in session and role == 1:
        if request.method == 'GET':
            product_id = request.args.get('product_id')
            cursor.execute('SELECT product.*, products.* from products left join product on products.SKU=product.SKU where products.product_id = %s;', (product_id,))
            product_info = cursor.fetchone()

            cursor.execute('SELECT * FROM units WHERE status = "Active";')
            list_unit = cursor.fetchall()

            cursor.execute('SELECT * FROM stock WHERE product_id = %s;', (product_id,))
            stock_info = cursor.fetchone()

            cursor.execute('Select depot_id from products where SKU=%s', (product_info[1],))
            existing_depot = cursor.fetchall()
            existing_depot = [item[0] for item in existing_depot]

            cursor.execute('SELECT * FROM depots')
            depot_list = cursor.fetchall()
            depots = []
            for depot in depot_list:
                if depot[0] not in existing_depot:
                    depots.append(depot)

            if request.args.get('msg'):
                msg = request.args.get('msg')

            cursor.execute('SELECT max(product_id) FROM products')
            max_product_id = cursor.fetchone()
            new_product_id = max_product_id[0]+1 if max_product_id[0] is not None else 1
            
            return render_template('admin-update_product.html', list_unit=list_unit, stock_info=stock_info, new_product_id=new_product_id, depots=depots, product_id=product_info[6], product_categories=product_categories, promotion_type=promotion_type, admin_info=admin_info, role=role, product_info=product_info, msg=msg)

        else:
            sku = request.form.get('sku')
            product_id = request.form.get('product_id')
            product_category_id = request.form.get('product_category_id')
            product_name = request.form.get('product_name')
            unit = request.form.get('unit')
            product_des = request.form.get('product_des')
            product_price = request.form.get('product_price')
            promotion_type_id = request.form.get('promotion_type_id')
            product_origins = request.form.get('product_origins')
            stock_quantity = request.form.get('stock_quantity')
            files = request.files.getlist('image1')

            cursor.execute('SELECT product.*, products.* from products left join product on products.SKU=product.SKU where products.product_id = %s;', (product_id,))
            product_info = cursor.fetchone()

            cursor.execute('SELECT max(product_id) FROM products')
            max_product_id = cursor.fetchone()
            new_product_id = max_product_id[0]+1 if max_product_id[0] is not None else 1

            cursor.execute('SELECT * FROM stock WHERE product_id = %s;', (product_id,))
            stock_info = cursor.fetchone()

            if files:
                for file in files:
                    if file:
                        if allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            fixed_filepath = filepath.replace("\\", "/")
                            file.save(fixed_filepath)
                        else:
                            msg = 'Invalid file format! Please upload files with extensions: png, jpg, jpeg, gif.'
                            return redirect(url_for('admin_edit_product', msg=msg, product_id=product_id))
                    else:
                        fixed_filepath = request.form.get('old_image')
            cursor.execute('UPDATE products SET SKU = %s, product_price = %s, product_category_id = %s, promotion_type_id = %s where product_id = %s;', (sku, product_price, product_category_id, promotion_type_id, product_id))
            cursor.execute('UPDATE product SET product_name = %s, unit = %s, pic = %s, product_des = %s, product_origins = %s WHERE SKU = %s;', (product_name, unit, fixed_filepath, product_des, product_origins, sku))
            cursor.execute('UPDATE stock SET quantity = %s WHERE product_id = %s;', (stock_quantity, product_id))
            msg = 'You have successfully updated the product.'
            return redirect(url_for('admin_product_details', msg=msg, product_id=product_id))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/admin/product-list/delete')
def admin_product_delete():
    product_id = request.args.get('product_id')
    cursor = getCursor()
    cursor.execute('UPDATE products SET product_status="0" WHERE product_id = %s;', (product_id,))
    msg = 'Product has been deleted successfully.'
    return redirect( url_for('admin_product_list', msg=msg))

@app.route('/admin/product-list/product/move_to_depot', methods=['POST'])
def admin_move_product():
    cursor = getCursor()
    depot_id = request.form.get('depot_id')
    new_product_id = request.form.get('new_product_id')
    product_category_id = request.form.get('product_category_id')
    stock_quantity = request.form.get('stock_quantity')
  
    sku = request.form.get('sku')
    product_price = request.form.get('product_price')
    promotion_type_id = request.form.get('promotion_type_id')


    cursor.execute('INSERT INTO products VALUES (%s, %s, %s, %s, %s, %s, "1");', (new_product_id, sku, product_price, product_category_id, promotion_type_id, depot_id))
    cursor.execute('INSERT INTO stock values (%s, %s, %s);', (new_product_id, depot_id, stock_quantity,))
    msg = 'Product has been successfully replicated between depots!'
    return redirect(url_for('admin_product_list', msg=msg))


#     cursor.execute('SELECT * FROM promotion_types')
#     promotion_type = cursor.fetchall()

#     if 'loggedin' in session and role == 3:
#         if request.method == 'GET':
#             depot_info = session.get('location')
#             cursor.execute('select depot_id from depots where location = %s', (depot_info[0],))
#             depot_id = cursor.fetchone()  # Fetch the result immediately and extract the value
#             sku = request.args.get('sku')
#             cursor.execute('SELECT * FROM product WHERE SKU = %s;', (sku,))
#             product_info = cursor.fetchone()

#             cursor.execute('SELECT * FROM products WHERE SKU = %s and depot_id = %s;', (sku, depot_id[0]))
#             products_info = cursor.fetchone()
#             return render_template('staff-update_product.html', product_id=products_info[0], product_categories=product_categories, promotion_type=promotion_type, staff_info=staff_info, depot_id=depot_id[0], role=role, location=session['location'][0], product_info=product_info, products_info=products_info)

#         else:
#             sku = request.form.get('sku')
#             product_id = request.form.get('product_id')
#             product_category_id = request.form.get('product_category_id')
#             product_name = request.form.get('product_name')
#             unit = request.form.get('unit')
#             product_des = request.form.get('product_des')
#             product_price = request.form.get('product_price')
#             promotion_type_id = request.form.get('promotion_type_id')
#             product_origins = request.form.get('product_origins')
#             depot_id = request.form.get('depot_id')
#             files = request.files.getlist('image1')
#             if files:
#                 for file in files:
#                     if file:
#                         if allowed_file(file.filename):
#                             filename = secure_filename(file.filename)
#                             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                             fixed_filepath = filepath.replace("\\", "/")
#                             file.save(fixed_filepath)
#                         else:
#                             msg = 'Invalid file format! Please upload files with extensions: png, jpg, jpeg, gif.'
#                             return render_template('staff-update_product.html', product_id=product_id, product_categories=product_categories, promotion_type=promotion_type, staff_info=staff_info, depot_id=depot_id[0], msg=msg, role=role, location=session['location'][0])
#                     else:
#                         fixed_filepath = request.form.get('old_image')
#             cursor.execute('UPDATE products SET SKU = %s, product_price = %s, product_category_id = %s, promotion_type_id = %s where product_id = %s;', (sku, product_price, product_category_id, promotion_type_id, product_id))
#             cursor.execute('UPDATE product SET product_name = %s, unit = %s, pic = %s, product_des = %s, product_origins = %s WHERE SKU = %s;', (product_name, unit, fixed_filepath, product_des, product_origins, sku))
#             return redirect(url_for('staff_product_list'))
#     else:
#         # If user is not logged in or doesn't have the required role, redirect to home page
#         return redirect('homepage')

# @app.route('/staff/product-list/delete')
# def staff_product_delete():
#     sku = request.args.get('sku')
#     cursor = getCursor()
#     cursor.execute('DELETE FROM products where SKU = %s;', (sku,))
#     msg = 'Product has been deleted successfully.'
#     return redirect( url_for(staff_product_list, msg=msg))

@app.route('/admin/shippmentlist',methods=['get','post'])
def admin_shippmentlist():
    role = session.get('role')
    msg=''
    if 'loggedin' in session and role == 1:
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()
        #get all depots info
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()
        
        # # Fetch profile images
        # cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (2,))
        # profile_image_url = cursor.fetchone()
        if request.method=='GET':
            cursor.execute('select s.*,d.location from shippments as s join depots as d on s.depot_id=d.depot_id')
            shippments = cursor.fetchall()
           
            return render_template('admin_shippment_list.html', msg=msg,depot_all=depot_all,location=session['location'][0], admin_info=admin_info,shippments = shippments)
        else:
            cursor=getCursor()
            cursor.execute('select shippment_id from shippments')
            shippment_id_all = cursor.fetchall()
            for id in shippment_id_all:
                n = id[0]
                shipid = request.form.get('id_n')
                price = request.form.get('price_n')
                cursor.execute('update shippments set shippment_price =%s where shippment_id=%s',(price,shipid,))
            msg= 'Shippment has been updated successfully!'
            cursor.execute('select s.*,d.location from shippments as s join depots as d on s.depot_id=d.depot_id')
            shippments = cursor.fetchall()
            return render_template('admin_shippment_list.html', price=price,id=id,msg=msg,depot_all=depot_all,location=session['location'][0], admin_info=admin_info,shippments = shippments)

    else: 
        return redirect(url_for('logout'))

@app.route('/admin/changeshippment/<shippment_id1>',methods=['post'])
def admin_changeshippment(shippment_id1):
    role = session.get('role')
    msg=''
    if 'loggedin' in session and role == 1:
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()
        #get all depots info
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()


        shipid = request.form.get('id')
        price = request.form.get('price')
        cursor.execute('update shippments set shippment_price =%s where shippment_id=%s',(price,shippment_id1,))
        msg= 'Shippment has been updated successfully!'

        cursor.execute('select s.*,d.location from shippments as s join depots as d on s.depot_id=d.depot_id')
        shippments = cursor.fetchall()
        return render_template('admin_shippment_list.html', msg=msg,depot_all=depot_all,location=session['location'][0], admin_info=admin_info,shippments = shippments)


    
@app.route('/admin/addshippment',methods=['get','post'])
def admin_addshippment():
    role = session.get('role')
    user_id = session['user_id']
    cursor= getCursor()

    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    if 'loggedin' in session and role == 1:


        if request.method=='GET':
            cursor= getCursor()
            cursor.execute('select max(shippment_id) from shippments')
            max_shippment_id = cursor.fetchone()
            new_shippment_id = max_shippment_id[0] +1

            cursor.execute('select * from depots')
            depot_all=cursor.fetchall()
            return render_template('admin-add-shippment.html',admin_info=admin_info,msg='',new_shippment_id=new_shippment_id,depot_all=depot_all)
        
        else:

            depot = request.form.get('depot_id')
            price = request.form.get('price')
            new_shippment_id = request.form.get('new_shippment_id')


            cursor= getCursor()

            cursor.execute('insert into shippments values (%s,%s,%s)',(new_shippment_id,price,depot,))

            msg= 'New shippment has been added successfully!'

            cursor.execute('select * from depots')
            depot_all=cursor.fetchall()
            return render_template('admin-add-shippment.html',admin_info=admin_info,msg=msg,new_shippment_id='',depot_all=depot_all)

@app.route('/admin/product-category', methods=['GET', 'POST'])
def admin_product_category():
    role = session.get('role')  # Get the user's role from the session
    if 'loggedin' in session and role == 1:  # Check if the user is logged in and has admin role (role == 1)
        cursor = getCursor()
        user_id = session['user_id']
        
        # Execute a SQL query to fetch the admin's role, full name, and profile picture
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()  # Fetch the result of the query

        if request.method == 'GET': 
            cursor.execute('SELECT * FROM product_categories')  # Execute a SQL query to fetch all product categories
            categoryinfo = cursor.fetchall()  # Fetch all results
            return render_template('admin-product_category.html', admin_info=admin_info, categoryinfo=categoryinfo)  # Render the template with fetched data
        
        if request.method == 'POST': 
            searchinput = request.form['searchinput']  # Get the search input from the form
            # Execute a SQL query to search for product categories matching the search input
            cursor.execute('SELECT * FROM product_categories WHERE product_category_name LIKE %s', ("%" + searchinput + "%",))
            categoryinfo = cursor.fetchall()  # Fetch all results
            return render_template('admin-product_category.html', admin_info=admin_info, categoryinfo=categoryinfo)  # Render the template with fetched data

    else:
        return redirect(url_for('logout'))  # Redirect to logout if the user is not logged in or doesn't have the admin role

@app.route('/admin/category/add', methods=['GET', 'POST'])
def add_category():
    if 'loggedin' in session and session.get('role') == 1:  # Check if the user is logged in and has admin role (role == 1)
        cursor = getCursor()
        user_id = session['user_id']
        
        # Execute a SQL query to fetch the admin's role, full name, and profile picture
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()  # Fetch the result of the query

        if request.method == 'POST':
            name = request.form['name']  # Get the category name from the form
            # Execute a SQL query to check if the category already exists
            cursor.execute('SELECT * FROM product_categories WHERE product_category_name = %s', (name,))
            existing_category = cursor.fetchone()  # Fetch the result of the query
            
            if existing_category:  # Check if the category already exists
                flash('Category name must be unique.', 'error')  # Show an error message if the category exists
                return redirect(url_for('add_category'))  # Redirect to the add category page
            
            # Execute a SQL query to insert the new category into the product_categories table
            cursor.execute('INSERT INTO product_categories (product_category_name) VALUES (%s)', (name,))
            flash('Category added successfully!', 'success')  # Show a success message
            return redirect(url_for('admin_product_category', admin_info=admin_info, location=session['location'][0]))  # Redirect to the product category page

        # Render the add category template with the admin information
        return render_template('admin-add_category.html', admin_info=admin_info, location=session['location'][0])
    
    return redirect(url_for('logout'))  # Redirect to logout if the user is not logged in or doesn't have the admin role

@app.route('/admin/category/edit/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if 'loggedin' in session and session.get('role') == 1:  # Check if the user is logged in and has admin role (role == 1)
        cursor = getCursor() 
        user_id = session['user_id']
        
        # Execute a SQL query to fetch the admin's role, full name, and profile picture
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()  # Fetch the result of the query

        if request.method == 'POST':
            name = request.form['name']  # Get the category name from the form
            # Execute a SQL query to check if the category name already exists and is not the current category
            cursor.execute('SELECT * FROM product_categories WHERE product_category_name = %s AND product_category_id != %s', (name, category_id))
            existing_category = cursor.fetchone()  # Fetch the result of the query
            
            if existing_category:  # Check if the category name already exists
                flash('Category name must be unique.', 'error')  # Show an error message if the category name exists
                return redirect(url_for('edit_category', category_id=category_id, admin_info=admin_info, location=session['location'][0]))  # Redirect to the edit category page
            
            # Execute a SQL query to update the category name
            cursor.execute('UPDATE product_categories SET product_category_name = %s WHERE product_category_id = %s', (name, category_id))
            flash('Category updated successfully!', 'success')  # Show a success message
            return redirect(url_for('admin_product_category', admin_info=admin_info, location=session['location'][0]))  # Redirect to the product category page

        # Execute a SQL query to fetch the category details
        cursor.execute('SELECT * FROM product_categories WHERE product_category_id = %s', (category_id,))
        category = cursor.fetchone()  # Fetch the result of the query

        # Render the edit category template with the fetched data
        return render_template('admin-edit_category.html', category=category, admin_info=admin_info, location=session['location'][0])
    
    return redirect(url_for('logout'))  # Redirect to logout if the user is not logged in or doesn't have the admin role

#@app.route('/admin/category/delete/<int:category_id>', methods=['POST'])
#def delete_category(category_id):
#    if 'loggedin' in session and session.get('role') == 1:
#        cursor = getCursor()
#        user_id = session['user_id']
#        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
#                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
#                          INNER JOIN staff ON staff.user_id = users.user_id 
#                          WHERE users.user_id = %s''', (user_id,))
#        admin_info = cursor.fetchone()
#        cursor.execute('DELETE FROM product_categories WHERE product_category_id = %s', (category_id,))
#        flash('Category deleted successfully!', 'success')
#        return redirect(url_for('admin_product_category',admin_info=admin_info))
#    return redirect(url_for('logout'))

@app.route('/admin/unitlist',methods=['get','post'])
def admin_unitlist():
    role = session.get('role')
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg= ''
    if 'loggedin' in session and role == 1:
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()
        #get all depots info
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()
        
        # # Fetch profile images
        # cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (2,))
        # profile_image_url = cursor.fetchone()
        if request.method=='GET':
            cursor.execute('select * from units')
            unit_all = cursor.fetchall()   

           
            return render_template('admin_unit_list.html', msg=msg,depot_all=depot_all,location=session['location'][0], admin_info=admin_info,unit_all=unit_all)
        else:
            cursor=getCursor()
            cursor.execute('select shippment_id from shippments')
            shippment_id_all = cursor.fetchall()
            for id in shippment_id_all:
                n = id[0]
                shipid = request.form.get('id_n')
                price = request.form.get('price_n')
                cursor.execute('update shippments set shippment_price =%s where shippment_id=%s',(price,shipid,))
            msg= 'Shippment has been updated successfully!'
            cursor.execute('select s.*,d.location from shippments as s join depots as d on s.depot_id=d.depot_id')
            shippments = cursor.fetchall()
            return render_template('admin_unit_list.html', price=price,id=id,msg=msg,depot_all=depot_all,location=session['location'][0], admin_info=admin_info,shippments = shippments)

    else: 
        return redirect(url_for('logout'))

@app.route('/admin/changeunit/<unit_id1>',methods=['post'])
def admin_changeunit(unit_id1):
    role = session.get('role')
    msg=''
    if 'loggedin' in session and role == 1:
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()
        #get all depots info
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()


        name = request.form.get('name')
        status = request.form.get('status')

        cursor.execute('update units set unit_name =%s,status=%s where unit_id=%s',(name,status,unit_id1,))
        msg= 'Unit has been updated successfully!'

        cursor.execute('select * from units')
        unit_all = cursor.fetchall()  
        
        return redirect(url_for('admin_unitlist',msg=msg))
        #return render_template('admin_unit_list.html',msg=msg,depot_all=depot_all,location=session['location'][0], admin_info=admin_info,unit_all = unit_all)


    
@app.route('/admin/addunit',methods=['get','post'])
def admin_addunit():
    role = session.get('role')
    user_id = session['user_id']
    cursor= getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    if 'loggedin' in session and role == 1:


        if request.method=='GET':
            cursor= getCursor()
            cursor.execute('select max(unit_id) from units')
            max_unit_id = cursor.fetchone()
            new_unit_id = max_unit_id[0] +1

            cursor.execute('select * from depots')
            depot_all=cursor.fetchall()
            return render_template('admin-add-unit.html',admin_info=admin_info,msg='',new_unit_id=new_unit_id,depot_all=depot_all)
        
        else:

            name = request.form.get('name')
            status = request.form.get('status')
            new_unit_id = request.form.get('new_unit_id')

            
            cursor= getCursor()
 
            cursor.execute('select unit_id from units where unit_name = %s',(name,))
            exist_id = cursor.fetchone()

            if exist_id is None:
                cursor.execute('insert into units values (%s,%s,%s)',(new_unit_id,name,status,))

                msg= 'New unit has been added successfully!'

                cursor.execute('select * from depots')
                depot_all=cursor.fetchall()
                return redirect(url_for('admin_unitlist',msg=msg))            
            
            else:
                cursor= getCursor()
                cursor.execute('select * from depots')
                depot_all=cursor.fetchall()
                msg = 'Please change unit name!'
                return render_template('admin-add-unit.html',admin_info=admin_info,msg=msg,new_unit_id=new_unit_id,depot_all=depot_all)



            #return render_template('admin-add-unit.html',admin_info=admin_info,msg=msg,new_unit_id='',depot_all=depot_all)
          
@app.route('/admin/premade-box-list', methods=['GET', 'POST'])
def admin_premade_box_list():
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg= ''
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
   
    # Fetch admin information for use of admin.html extension in the template

    cursor= getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()

    # Fetch all distinct locations from the database
    cursor.execute('''SELECT DISTINCT location FROM depots''')
    locations = [row[0] for row in cursor.fetchall()]

    # Fetch all distinct categories from the database
    cursor.execute('''SELECT DISTINCT product_category_name FROM product_categories''')
    categories = [row[0] for row in cursor.fetchall()]

    # Check if the user is logged in and has admin role
    if 'loggedin' in session and role == 1:
        # If it's a POST request, process the form data
        # filter
        if request.method == 'POST':
            searchinput = request.form.get('searchinput', '').strip()
            selected_location = request.form.get('location')
            selected_category = request.form.get('category')
        else:
            # If it's a GET request, get search input, selected location, and selected category from query parameters
            searchinput = request.args.get('searchinput', '').strip()
            selected_location = request.args.get('location')
            selected_category = request.args.get('category')

        # If search input is provided, perform search in the database
        if searchinput:
            query = '''SELECT b.SKU, pc.product_category_name, b.box_name, pro.product_price, u.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM boxes b
                                    LEFT JOIN products pro ON b.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id LEFT JOIN units u ON u.unit_id = b.unit
                        WHERE product_status="1" AND product_origins != "Digital card" AND (b.SKU LIKE %s OR pc.product_category_name LIKE %s OR b.box_name LIKE %s) AND pro.product_category_id = 7
                        ORDER BY pro.product_id DESC'''
            params = (f'%{searchinput}%', f'%{searchinput}%', f'%{searchinput}%')
            if selected_location:
                query += " AND d.location = %s"
                params += (selected_location,)
            if selected_category and selected_category != 'all':
                query += " AND pc.product_category_name = %s"
                params += (selected_category,)
            cursor.execute(query, params)
            products = cursor.fetchall()
        # If no search input is provided, fetch all products
        else:
            if selected_location:
                cursor.execute('''SELECT b.SKU, pc.product_category_name, b.box_name, pro.product_price, u.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM boxes b
                                    LEFT JOIN products pro ON b.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id LEFT JOIN units u ON u.unit_id = b.unit
                                    WHERE product_status="1" AND product_origins != "Digital card" AND d.location = %s AND pro.product_category_id = 7
                                    ORDER BY pro.product_id DESC''', (selected_location,))
            elif selected_category:
                cursor.execute('''SELECT b.SKU, pc.product_category_name, b.box_name, pro.product_price, u.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM boxes b
                                    LEFT JOIN products pro ON b.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id LEFT JOIN units u ON u.unit_id = b.unit
                                    WHERE product_status="1" AND product_origins != "Digital card" AND pc.product_category_name = %s
                                    ORDER BY pro.product_id DESC''', (selected_category,))
            else:
                cursor.execute('''SELECT b.SKU, pc.product_category_name, b.box_name, pro.product_price, u.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM boxes b
                                    LEFT JOIN products pro ON b.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id LEFT JOIN units u ON u.unit_id = b.unit
                                    WHERE product_status="1" AND pro.product_category_id = 7 AND product_origins != "Digital card"
                                    ORDER BY pro.product_id DESC''')
            products = cursor.fetchall()

        # Sorting logic based on query parameters
        sort_by = request.args.get('sort_by')
        if sort_by:
            reverse = request.args.get('reverse')  # Get the 'reverse' parameter from the request
            if reverse == 'True':
                reverse = True
            else:
                reverse = False

            if sort_by == 'SKU':
                products.sort(key=lambda x: x[0], reverse=reverse)
            elif sort_by == 'Category':
                products.sort(key=lambda x: x[1], reverse=reverse)
            elif sort_by == 'Product Name':
                products.sort(key=lambda x: x[2], reverse=reverse)
            elif sort_by == 'Price':
                products.sort(key=lambda x: x[3], reverse=reverse)
            elif sort_by == 'Unit':
                products.sort(key=lambda x: x[4], reverse=reverse)
            elif sort_by == 'Stock Quantity':
                products.sort(key=lambda x: x[5] if x[5] is not None else 0, reverse=reverse)
            elif sort_by == 'Location':
                products.sort(key=lambda x: x[6], reverse=reverse)

        # Render template with the list of products, locations, and search input
        return render_template('admin-premade_box_list.html', products=products, admin_info=admin_info, role=role, locations=locations, categories=categories, searchinput=searchinput, selected_location=selected_location, selected_category=selected_category, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/admin/premade-box-list/premade-box', methods=["GET","POST"])
def admin_premade_box_details():
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor=getCursor()
    # Fetch admin information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))

   
    admin_info = cursor.fetchone()
    if 'loggedin' in session and role == 1: 
        cursor=getCursor()

        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''

        product_id = request.args.get('product_id')

        cursor.execute("""SELECT b.SKU, b.box_name, pro.product_price, u.unit_name, b.pic, b.box_des, b.product_origins, d.location, pro.product_id 
                       FROM boxes b 
                       LEFT JOIN products pro ON b.SKU = pro.SKU 
                       LEFT JOIN depots d on d.depot_id = pro.depot_id LEFT JOIN units u ON u.unit_id = b.unit
                       WHERE pro.product_id = %s""", (product_id,)) 
        product = cursor.fetchall()

        cursor.execute("""SELECT pro.SKU FROM products AS pro JOIN boxes AS b ON b.SKU = pro.SKU WHERE pro.product_id = %s""", (product_id,))

        sku = cursor.fetchone()

        cursor.execute("""SELECT pro.SKU, p.product_name, b.quantity, u.unit_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN box_items AS b ON b.product_id = pro.product_id LEFT JOIN units AS u ON u.unit_id = p.unit WHERE b.SKU = %s""", (sku[0],))

        box_items = cursor.fetchall()

        return render_template('admin-premade_box_details.html', admin_info=admin_info, product=product, role=role, msg=msg, box_items=box_items)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))
    

@app.route('/admin/get-products')
def get_products():
    depot_id = request.args.get('depot_id')
    
    cursor = getCursor()
    
    
    cursor.execute('SELECT pro.product_id, p.product_name, u.unit_name FROM products AS pro JOIN product p ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit WHERE depot_id = %s', (depot_id,))
    products = cursor.fetchall()
    



    products_list = [{'id': product[0], 'name': f'{product[1]} ({product[2]})'} for product in products]

    print(products_list)

    return ({'products': products_list})

@app.route('/admin/get-product-quantity')
def get_product_quantity():

    product_id = request.args.get('product_id')
   
    
    cursor = getCursor()
    
    cursor.execute('SELECT quantity FROM stock WHERE product_id = %s', (product_id,))
    stock = cursor.fetchone()
    print(product_id, stock)
    
    
    if stock:
        return {'quantity': stock[0]}
    else:
        return {'quantity': 0}

   
@app.route('/admin/promade-box-list/add-premade-box', methods = ['GET', 'POST'])
def admin_add_premade_box():
    role = session.get('role')
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
   

    cursor.execute('SELECT * FROM product_categories')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    if 'loggedin' in session and role == 1:
        if request.method == 'GET':

            if request.args.get('msg'):
                msg = request.args.get('msg')
            else:
                msg = ''
            cursor.execute('SELECT max(product_id) FROM products')
            max_product_id = cursor.fetchone()
            new_product_id = max_product_id[0]+1 if max_product_id[0] is not None else 1
            cursor.execute('SELECT * FROM depots')
            depot_info = cursor.fetchall()
            cursor.execute("""SELECT pro.product_id, p.product_name, u.unit_name FROM product AS p JOIN products pro ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit""")
            pro_list = cursor.fetchall()
            return render_template('admin-add_premade_box.html', msg=msg, new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, admin_info=admin_info, depot_info=depot_info, role=role,pro_list=pro_list)
        else:
        
            cursor.execute('SELECT * FROM depots')
            depot_info = cursor.fetchall()

            cursor.execute("""SELECT pro.product_id, p.product_name, u.unit_name FROM product AS p JOIN products pro ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit""")
            pro_list = cursor.fetchall()

            new_product_id = request.form.get('new_product_id')
            product_category_id = request.form.get('product_category_id')
            product_name = request.form.get('product_name')
            sku = request.form.get('sku')
            unit = request.form.get('unit')
            product_des = request.form.get('product_des')
            product_price = request.form.get('product_price')
            promotion_type_id = request.form.get('promotion_type_id')
            product_origins = request.form.get('product_origins')
            depot_id = request.form.get('depot_id')
            pro_ids = request.form.getlist('pro_id[]')
            quantities = request.form.getlist('quantity[]')
            stock_quantity = request.form.get('stock_quantity')
            files = request.files.getlist('image1')

            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')

            # Convert start and end times to datetime objects
            start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')


            # Check if product with the same SKU already exists
            cursor.execute('SELECT * FROM products WHERE sku = %s', (sku,))
            existing_product = cursor.fetchone()
            if existing_product:
                msg = 'Premade Box with this SKU already exists!'
                cursor.execute('SELECT max(product_id) FROM products')
                max_product_id = cursor.fetchone()
                new_product_id = max_product_id[0] + 1 if max_product_id[0] is not None else 1
                location = session['location'][0]
                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (location,))
                depot_id = cursor.fetchall()
                return render_template('admin-add_premade_box.html', new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, admin_info=admin_info, depot_id=depot_id[0], msg=msg, role=role,depot_info=depot_info,pro_list=pro_list)
            if files:
                for file in files:
                    if file:
                        if allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            fixed_filepath = filepath.replace("\\", "/")
                            file.save(fixed_filepath)
                        else:
                            msg = 'Invalid file format! Please upload files with extensions: png, jpg, jpeg, gif.'
                            return redirect( url_for('admin_add_premade_box', msg=msg))
                    else:
                        fixed_filepath = "app/static/assets/img/product_avatar.png"

            
            cursor.execute('INSERT INTO boxes VALUES (%s, %s, %s, %s, %s, %s);', (sku, product_name, unit, fixed_filepath, product_des, product_origins))
            
            cursor.execute("Insert into union_skus values (%s, 'boxes');", (sku,))

            cursor.execute('INSERT INTO products VALUES (%s, %s, %s, 7, %s, %s, 0);', (new_product_id, sku, product_price, promotion_type_id, depot_id))


            for pro_id, quantity in zip(pro_ids, quantities):
              cursor.execute('INSERT INTO box_items (SKU, product_id, quantity) VALUES (%s, %s, %s);', (sku, pro_id, quantity))

            cursor.execute('Insert into stock values (%s, %s, %s);', (new_product_id, depot_id, stock_quantity,))


            cursor.execute('INSERT INTO scheduled_box (product_id, start_time, end_time) VALUES (%s, %s, %s);', (new_product_id, start_time, end_time))

            if datetime.now() >= start_time:
                set_product_in_stock(new_product_id, 1)
            else:
                schedule_product_availability(new_product_id, start_time, end_time) 
            
            msg = 'Premade box has been added successfully!'
            return redirect(url_for('admin_premade_box_list', msg=msg,depot_info=depot_info,pro_list=pro_list))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/admin/premade-box-list/premade-box/update', methods = ['GET', 'POST'])
def admin_edit_premade_box():
    role = session.get('role')
    msg=''
    cursor = getCursor()
    user_id = session['user_id']

    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()



    cursor.execute('SELECT * FROM product_categories')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    cursor.execute('SELECT * FROM depots')
    depot_info = cursor.fetchall()

    cursor.execute("""SELECT pro.product_id, p.product_name, u.unit_name FROM product AS p JOIN products pro ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit""")
    pro_list = cursor.fetchall()

    product_id = request.args.get('product_id')

    

    if 'loggedin' in session and role == 1:
        if request.method == 'GET':
            
            cursor.execute('SELECT boxes.*, products.*, units.unit_name from products left join boxes on boxes.SKU=products.SKU LEFT JOIN units ON units.unit_id = boxes.unit  where products.product_id = %s;', (product_id,))
            product_info = cursor.fetchone()


            cursor.execute('SELECT * FROM stock WHERE product_id = %s;', (product_id,))
            stock_info = cursor.fetchone()

            cursor.execute('Select depot_id from products where SKU=%s', (product_info[1],))
            existing_depot = cursor.fetchall()
            existing_depot = [item[0] for item in existing_depot]

            cursor.execute('SELECT * FROM depots')
            depot_list = cursor.fetchall()
            depots = []
            for depot in depot_list:
                if depot[0] not in existing_depot:
                    depots.append(depot)

            if request.args.get('msg'):
                msg = request.args.get('msg')

            cursor.execute('SELECT max(product_id) FROM products')
            max_product_id = cursor.fetchone()
            new_product_id = max_product_id[0]+1 if max_product_id[0] is not None else 1

            cursor.execute("""SELECT b.* FROM box_items AS b JOIN products AS pro ON pro.SKU= b.SKU WHERE pro.product_id = %s""",(product_id,))
            box_items = cursor.fetchall()

            
            
            return render_template('admin-update_premade_box.html', stock_info=stock_info, new_product_id=new_product_id, depots=depots, product_id=product_info[6], product_categories=product_categories, promotion_type=promotion_type, admin_info=admin_info, role=role, product_info=product_info, msg=msg, box_items=box_items,depot_info=depot_info,pro_list=pro_list)

        else:
            sku = request.form.get('sku')
            product_id = request.form.get('product_id')
            product_category_id = request.form.get('product_category_id')
            product_name = request.form.get('product_name')
            unit = request.form.get('unit')
            product_des = request.form.get('product_des')
            product_price = request.form.get('product_price')
            promotion_type_id = request.form.get('promotion_type_id')
            product_origins = request.form.get('product_origins')
            stock_quantity = request.form.get('stock_quantity')
            files = request.files.getlist('image1')

            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')

            pro_ids = request.form.getlist('pro_id[]')
            quantities = request.form.getlist('quantity[]')

            

            # Convert start and end times to datetime objects
            start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')

            cursor.execute('SELECT boxes.*, products.*, units.unit_name from products left join boxes on boxes.SKU=products.SKU LEFT JOIN units ON units.unit_id = boxes.unit where products.product_id = %s;', (product_id,))
            product_info = cursor.fetchone()

            cursor.execute('SELECT max(product_id) FROM products')
            max_product_id = cursor.fetchone()
            new_product_id = max_product_id[0]+1 if max_product_id[0] is not None else 1

            cursor.execute('SELECT * FROM stock WHERE product_id = %s;', (product_id,))
            stock_info = cursor.fetchone()

            if files:
                for file in files:
                    if file:
                        if allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            fixed_filepath = filepath.replace("\\", "/")
                            file.save(fixed_filepath)
                        else:
                            msg = 'Invalid file format! Please upload files with extensions: png, jpg, jpeg, gif.'
                            return redirect(url_for('admin_edit_premade_box', msg=msg, product_id=product_id, depot_info=depot_info, pro_list=pro_list, box_items=box_items))
                    else:
                        fixed_filepath = request.form.get('old_image')
            cursor.execute('UPDATE products SET SKU = %s, product_price = %s, product_category_id = 7, promotion_type_id = %s, product_status = 0 where product_id = %s;', (sku, product_price, promotion_type_id, product_id))
            cursor.execute('UPDATE boxes SET box_name = %s, unit = %s, pic = %s, box_des = %s, product_origins = %s WHERE SKU = %s;', (product_name, unit, fixed_filepath, product_des, product_origins, sku))

            cursor.execute("""SELECT b.* FROM box_items AS b INNER JOIN products AS pro ON pro.SKU= b.SKU WHERE b.SKU= %s""",(sku,))
            box_items = cursor.fetchall()

           
            for item, pro_id, quantity in zip(box_items,pro_ids, quantities):
                cursor.execute('UPDATE box_items SET product_id = %s, quantity= %s WHERE item_id = %s;', (pro_id, quantity,item[0]))
            
            
            cursor.execute('UPDATE stock SET quantity = %s WHERE product_id = %s;', (stock_quantity, product_id))
            msg = 'You have successfully updated the premade box.'
            cursor.execute('UPDATE scheduled_box SET start_time = %s, end_time = %s WHERE product_id = %s;', (start_time, end_time, product_id))


            if datetime.now() >= start_time:
                set_product_in_stock(product_id, 1)
            else:
                schedule_product_availability(product_id, start_time, end_time)
            return redirect(url_for('admin_premade_box_details', msg=msg, product_id=product_id, box_items=box_items, depot_info=depot_info,pro_list=pro_list))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/admin/premade-box/delete')
def admin_premadebox_delete():
    product_id = request.args.get('product_id')
    cursor = getCursor()
    cursor.execute('UPDATE products SET product_status="0" WHERE product_id = %s;', (product_id,))
    msg = 'Premade box has been deleted successfully.'
    return redirect( url_for('admin_premade_box_list', msg=msg))

@app.route('/admin/premade-box-list/premade-box/move_to_depot', methods=['POST'])
def admin_move_premade_box():
    cursor = getCursor()
    depot_id = request.form.get('depot_id')
    new_product_id = request.form.get('new_product_id')
    product_category_id = request.form.get('product_category_id')
    stock_quantity = request.form.get('stock_quantity')
  
    sku = request.form.get('sku')
    product_price = request.form.get('product_price')
    promotion_type_id = request.form.get('promotion_type_id')

    pro_ids = request.form.getlist('pro_id[]')
    quantities = request.form.getlist('quantity[]')

    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    # Convert start and end times to datetime objects
    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')

    
    cursor.execute("Insert into union_skus values (%s, 'boxes');", (sku,))

    cursor.execute('INSERT INTO products VALUES (%s, %s, %s, %s, %s, %s, 0);', (new_product_id, sku, product_price, product_category_id, promotion_type_id, depot_id))


    for pro_id, quantity in zip(pro_ids, quantities):
        cursor.execute('INSERT INTO box_items (SKU, product_id, quantity) VALUES (%s, %s, %s);', (sku, pro_id, quantity))

    cursor.execute('Insert into stock values (%s, %s, %s);', (new_product_id, depot_id, stock_quantity,))


    cursor.execute('INSERT INTO scheduled_box (product_id, start_time, end_time) VALUES (%s, %s, %s);', (new_product_id, start_time, end_time))

    if datetime.now() >= start_time:
        set_product_in_stock(new_product_id, 1)
    else:
         schedule_product_availability(new_product_id, start_time, end_time) 

    
    msg = 'Premade box has been successfully replicated between depots!'
    return redirect(url_for('admin_premade_box_list', msg=msg))


@app.route('/admin/discontinued-products', methods=['GET', 'POST'])
def admin_discontinued_products():
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg= ''
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor = getCursor()
    # Fetch admin information for use of admin.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()

    # Fetch all distinct locations from the database
    cursor.execute('''SELECT DISTINCT location FROM depots''')
    locations = [row[0] for row in cursor.fetchall()]

    # Fetch all distinct categories from the database
    cursor.execute('''SELECT DISTINCT product_category_name FROM product_categories''')
    categories = [row[0] for row in cursor.fetchall()]

    # Check if the user is logged in and has admin role
    if 'loggedin' in session and role == 1:
        # If it's a POST request, process the form data
        # filter
        if request.method == 'POST':
            searchinput = request.form.get('searchinput', '').strip()
            selected_location = request.form.get('location')
            selected_category = request.form.get('category')
        else:
            # If it's a GET request, get search input, selected location, and selected category from query parameters
            searchinput = request.args.get('searchinput', '').strip()
            selected_location = request.args.get('location')
            selected_category = request.args.get('category')

        # If search input is provided, perform search in the database
        if searchinput:
            query = '''SELECT pro.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id, b.box_name, us.unit_name, g.giftcard_name, pro.product_category_id
                                    FROM products pro 
                                    LEFT JOIN product p ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id LEFT JOIN boxes b ON b.SKU = pro.SKU LEFT JOIN giftcards g ON g.SKU = pro.SKU LEFT JOIN units us ON b.unit = us.unit_id
                        WHERE product_status="0"  AND (p.SKU LIKE %s OR pc.product_category_name LIKE %s OR p.product_name LIKE %s)
                        ORDER BY pro.product_id DESC'''
            params = (f'%{searchinput}%', f'%{searchinput}%', f'%{searchinput}%')
            if selected_location:
                query += " AND d.location = %s"
                params += (selected_location,)
            if selected_category and selected_category != 'all':
                query += " AND pc.product_category_name = %s"
                params += (selected_category,)
            cursor.execute(query, params)
            products = cursor.fetchall()
        # If no search input is provided, fetch all products
        else:
            if selected_location:
                cursor.execute('''SELECT pro.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id, b.box_name, us.unit_name, g.giftcard_name, pro.product_category_id
                                    FROM products pro 
                                    LEFT JOIN product p ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id LEFT JOIN boxes b ON b.SKU = pro.SKU LEFT JOIN giftcards g ON g.SKU = pro.SKU LEFT JOIN units us ON b.unit = us.unit_id
                                    WHERE product_status="0"    AND d.location = %s
                                    ORDER BY pro.product_id DESC''', (selected_location,))
            elif selected_category:
                cursor.execute('''SELECT pro.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id, b.box_name, us.unit_name, g.giftcard_name, pro.product_category_id
                                    FROM products pro 
                                    LEFT JOIN product p ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id LEFT JOIN boxes b ON b.SKU = pro.SKU LEFT JOIN giftcards g ON g.SKU = pro.SKU LEFT JOIN units us ON b.unit = us.unit_id
                                    WHERE product_status="0" AND pc.product_category_name = %s
                                    ORDER BY pro.product_id DESC''', (selected_category,))
            else:
                cursor.execute('''SELECT pro.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id, b.box_name, us.unit_name, g.giftcard_name, pro.product_category_id
                                    FROM products pro 
                                    LEFT JOIN product p ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id LEFT JOIN boxes b ON b.SKU = pro.SKU LEFT JOIN giftcards g ON g.SKU = pro.SKU LEFT JOIN units us ON b.unit = us.unit_id
                                    WHERE product_status="0"  
                                    ORDER BY pro.product_id DESC''')
            products = cursor.fetchall()

        # Sorting logic based on query parameters
        sort_by = request.args.get('sort_by')
        if sort_by:
            reverse = request.args.get('reverse')  # Get the 'reverse' parameter from the request
            if reverse == 'True':
                reverse = True
            else:
                reverse = False

            if sort_by == 'SKU':
                products.sort(key=lambda x: x[0], reverse=reverse)
            elif sort_by == 'Category':
                products.sort(key=lambda x: x[1], reverse=reverse)
            elif sort_by == 'Product Name':
                products.sort(key=lambda x: x[2], reverse=reverse)
            elif sort_by == 'Price':
                products.sort(key=lambda x: x[3], reverse=reverse)
            elif sort_by == 'Unit':
                products.sort(key=lambda x: x[4], reverse=reverse)
            elif sort_by == 'Stock Quantity':
                products.sort(key=lambda x: x[5] if x[5] is not None else 0, reverse=reverse)
            elif sort_by == 'Location':
                products.sort(key=lambda x: x[6], reverse=reverse)

        # Render template with the list of products, locations, and search input
        return render_template('admin-discontinued_products.html', products=products, admin_info=admin_info, role=role, locations=locations, categories=categories, searchinput=searchinput, selected_location=selected_location, selected_category=selected_category, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


@app.route('/admin/restore-product')
def admin_restore_product():
    product_id = request.args.get('product_id')
    cursor = getCursor()
    cursor.execute('UPDATE products SET product_status="1" WHERE product_id = %s;', (product_id,))
    msg = 'Product has been restored successfully.'
    return redirect( url_for('admin_discontinued_products', msg=msg))

@app.route('/admin/restore-premade-box', methods=['POST'])
def admin_restore_premade_box():
    product_id = request.args.get('product_id')
    cursor = getCursor()

    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    if start_time is None or end_time is None:

        msg = "Start time or end time not provided"

    # Convert start and end times to datetime objects
    start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
    
    cursor.execute('UPDATE products SET product_status="0" WHERE product_id = %s;', (product_id,))

    cursor.execute('UPDATE scheduled_box SET start_time = %s, end_time = %s WHERE product_id = %s;', (start_time, end_time, product_id))

    if datetime.now() >= start_time:
        set_product_in_stock(product_id, 1)
    else:
        schedule_product_availability(product_id, start_time, end_time)

    msg = 'Promade box has been restored successfully.'
    return redirect( url_for('admin_discontinued_products', msg=msg))


def set_product_in_stock(product_id, in_stock):
    cursor=getCursor()

    cursor.execute("UPDATE products SET product_status = %s WHERE product_id = %s", (in_stock, product_id))
    cursor.close()


def schedule_product_availability(product_id, start_time, end_time):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: set_product_in_stock(product_id, 1), 'date', run_date=start_time)
    scheduler.add_job(lambda: set_product_in_stock(product_id, 0), 'date', run_date=end_time)
    scheduler.start()



@app.route('/admin/return-request', methods=['GET', 'POST'])
def admin_return_request():
    role = session.get('role')
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    # Check if the user is logged in and has admin role
    if 'loggedin' in session and role == 1:
        if request.method == 'GET':
            if request.args.get('msg'):
                msg = request.args.get('msg')
            else:
                msg = ''
            # Fetch status filter from request arguments
            status_filter = request.args.get('status_filter', None)
            # Construct SQL query based on status filter
            if status_filter:
                cursor.execute('''SELECT return_authorization.* FROM return_authorization 
                                  WHERE return_authorization.return_status = %s''', (status_filter,))
            else:
                cursor.execute('''SELECT return_authorization.* FROM return_authorization''')
            return_list = cursor.fetchall()
            return render_template('admin-return_request.html', role=role, admin_info=admin_info, return_list=return_list, msg=msg)

        else:
            form_id = request.form.get('form_id')
            cursor.execute('''
                SELECT return_authorization.*, customers.family_name, customers.given_name, return_form.*, products.*, product.*, accounts.account_name,
                COALESCE(product.product_name, boxes.box_name) AS product_name, COALESCE(product.product_des, boxes.box_des) AS description,
                ROUND(products.product_price * IFNULL(promotion_types.discount, 1), 2) AS actual_price
                FROM return_authorization
                LEFT JOIN return_form ON return_authorization.form_id = return_form.form_id
                LEFT JOIN orders ON return_authorization.order_id = orders.order_id
                LEFT JOIN customers ON orders.user_id = customers.user_id
                LEFT JOIN products ON return_form.product_id = products.product_id
                LEFT JOIN product ON products.SKU = product.SKU
                LEFT JOIN accounts ON orders.user_id = accounts.user_id
                LEFT JOIN boxes ON products.SKU = boxes.SKU
                LEFT JOIN promotion_types ON products.promotion_type_id = promotion_types.promotion_type_id
                WHERE return_authorization.form_id = %s;
            ''', (form_id,))
            return_list = cursor.fetchall()

            total_value = 0
            for item in return_list:
                product_value = item[10] * item[27]
                total_value = total_value + product_value

            return render_template('admin-request_detail.html', total_value=total_value, role=role, admin_info=admin_info, return_list=return_list)
    else: 
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/admin/return-approve', methods = ['GET', 'POST'])
def admin_return_approve():
    role = session.get('role')
    # Check if the user is logged in and has admin role
    if 'loggedin' in session and role == 1:
        cursor = getCursor()
        form_id = request.form.get('form_id')
        return_status = request.form.get('status')
        subtotal = request.form.get('subtotal')
        subtotal_value = float(subtotal)

        # Update the return status
        cursor.execute('UPDATE return_authorization SET return_status = %s WHERE form_id = %s;', (return_status, form_id))

        if return_status == 'approved':
            # Get the user_id associated with the form_id
            cursor.execute('SELECT user_id FROM orders LEFT JOIN return_authorization ON orders.order_id = return_authorization.order_id WHERE return_authorization.form_id = %s;', (form_id,))
            user_id = cursor.fetchone()[0]

            # Check if the user_id is in the customers table
            cursor.execute('SELECT balance FROM customers WHERE user_id = %s;', (user_id,))
            customer_balance = cursor.fetchone()

            if customer_balance:
                # If user is a customer, update the customer's balance
                current_balance_value = float(customer_balance[0])
                new_balance = current_balance_value + subtotal_value
                cursor.execute('UPDATE customers SET balance = %s WHERE user_id = %s;', (new_balance, user_id))
            else:
                # If user is not a customer, check the accounts table
                cursor.execute('SELECT balance FROM accounts WHERE user_id = %s;', (user_id,))
                account_balance = cursor.fetchone()
                
                if account_balance:
                    # If user is an account holder, update the account holder's balance
                    current_balance_value = float(account_balance[0])
                    new_balance = current_balance_value + subtotal_value
                    cursor.execute('UPDATE accounts SET balance = %s WHERE user_id = %s;', (new_balance, user_id))
                else:
                    # Handle case where user_id is not found in either table (optional)
                    msg = 'User ID not found in customers or accounts.'
                    return redirect(url_for('admin_return_request', msg=msg))

        msg = 'Refund request processed, status updated.'
        return redirect(url_for('admin_return_request', msg=msg))
    else: 
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


def get_user_info(get_user_id,role):

    cursor=getCursor()

    role = session.get('role')  

    if role == 4:
        cursor.execute('''SELECT roles.role_name, CONCAT (customers.given_name, " ", customers.family_name) AS full_name, customers.pic FROM roles INNER JOIN users ON roles.role_id = users.role_id INNER JOIN customers ON customers.user_id = users.user_id WHERE users.user_id = %s''', (get_user_id,))
        user_info = cursor.fetchone()

        return user_info
    
    elif role == 5:
        # Execute a SQL query to fetch the account holder's role 
        cursor.execute("""SELECT roles.role_name, accounts.account_name, accounts.pic FROM roles INNER JOIN users ON roles.role_id = users.role_id INNER JOIN accounts ON accounts.user_id = users.user_id  WHERE users.user_id = %s""", (get_user_id,))
        user_info = cursor.fetchone()
        return user_info
    
    elif role == 3 or role ==2 or role == 1:
        # Execute a SQL query to fetch the account holder's role 
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic FROM roles INNER JOIN users ON roles.role_id = users.role_id INNER JOIN staff ON staff.user_id = users.user_id WHERE users.user_id = %s''', (get_user_id,))
        user_info = cursor.fetchone()

        return user_info


@app.route('/admin/orderlist',methods=['get','post'])
def admin_orderlist():
    role = session.get('role')
    msg=''
    order_status_all=[]
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()
    todaydate = datetime.now()



    if 'loggedin' in session and role == 1:
        # get all order status types
        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''


        if request.method=='GET':                
            cursor.execute('select * from order_status_types')
            order_status_types = cursor.fetchall() 

            cursor.execute('select d.location from depots as d')
            all_location = cursor.fetchall()
            
            #check if there's selected 
            selected_status_id = request.args.get('status_id')
            selected_location_id = request.args.get('location_id')

            cursor.execute('select s.staff_id, s.given_name,s.responsibility_id,d.location from staff as s join depots as d on s.depot_id = d.depot_id where responsibility_id !=1')
            staff_all = cursor.fetchall()
            # get all order number of the depot

            cursor.execute("""
                                select o.order_id, p.status, d.location from orders as o
                                join payments as p on o.payment_id = p.payment_id
                                join shippments as s on o.shippment_id=s.shippment_id
                                join depots as d on d.depot_id=s.depot_id
                                where p.status='Completed'
                                """)
            order_number_all = cursor.fetchall()


            cursor.execute("""
                                select o.order_id,oa.order_status_type_id as order_status, s.given_name
                                from orders as o 
                                left join order_assignments as oa on o.order_id=oa.order_id
                                left join staff as s on oa.staff_id = s.staff_id
                                left join payments as p on o.payment_id = p.payment_id
                                where p.status='Completed' order by order_id, order_status desc
                            """)
            order_process_all = cursor.fetchall()


            # get all status info
        
                # change the data to the form (id, packing,ready,out,delivered)
                # fill in 'begin' and 'to be started' when the resp_id is different

                #get different resp list
                
                #get all staff name:
            cursor.execute(' select given_name from staff')
            staff_name_all = cursor.fetchall()
                
                # if order_status_all:
                #     #return render_template('manager-order_list.html',msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=order_status_all)
                #     return render_template('test.html',order_status_all=order_status_all)
                # else:
                    # define a array with 5 items in a row without 'bgin' 'to start'

            order_status_all=[]
            h = len(order_number_all)
            order_status_all = [['' for x in range(6)] for y in range(h)] 

            # get max_order status list
            cursor.execute("""
                                        select o.order_id,max(oa.order_status_type_id) as order_status
                                        from orders as o 
                                        left join order_assignments as oa on o.order_id=oa.order_id
                                        left join payments as p on o.payment_id = p.payment_id
                                        where p.status='Completed' 
                                        group by o.order_id order by o.order_id, order_status desc;
                                    """)
            max_status= cursor.fetchall()  
#test OK      
            # return render_template('test.html',max_status=max_status)
                    #fill in the array 
            i = 0
            for order_number in order_number_all:
                #insert depot name
                order_status_all[i].insert(0,order_number[0])
                order_status_all[i].insert(0,order_number[2])                
                
# test OK
                # fill in 'begin' and 'to be started' when the resp_id is different
                for status in max_status:

                    if status[0] == order_number[0]:

                    # check if there's no assignment 
                    # fill in 'begin' 
                        order_status_all[i].insert(2,'Begin')              



                        #insert name into the list
                for order_process in order_process_all:
                    if order_process[0] == order_number[0]:
                        for staff_name in staff_name_all:
                            if order_process[2] == staff_name[0]:
                                order_status_all[i].insert(2,order_process[2])


                        #increase i         
                i = i +1

            # return render_template('test.html',order_status_all=order_status_all)        
            return render_template('admin-order_list.html',all_location=all_location,msg=msg,selected_location_id=selected_location_id,selected_status_id=selected_status_id,order_status_types=order_status_types,order_status_all=order_status_all,staff_all=staff_all,order_number_all=order_number_all,admin_info=admin_info)
            
# for POST method
        else: 

                        # get all orders processing data
            cursor.execute("""
                                select o.order_id,oa.order_status_type_id as order_status, s.given_name
                                from orders as o 
                                left join order_assignments as oa on o.order_id=oa.order_id
                                left join staff as s on oa.staff_id = s.staff_id
                                left join payments as p on o.payment_id = p.payment_id
                                where p.status='Completed' order by order_id, order_status desc
                            """)
            order_process_all = cursor.fetchall()
            cursor.execute('select * from order_status_types')
            order_status_types = cursor.fetchall()
            #to get order_status_all
                    # get all status info
    
            # get manager's depot_id
            cursor.execute('select depot_id from staff where user_id=%s', (user_id,))
            depot = cursor.fetchone()            
        # get all order number of the depot
    #filter function script by location, function OK
            selected_location_id = request.form.get('location_id')

            #get all locations
            cursor.execute('select d.location from depots as d')
            all_location = cursor.fetchall()
             # function OK
            if selected_location_id:
                cursor.execute("""
                                    select o.order_id, p.status, d.location from orders as o
                                    join payments as p on o.payment_id = p.payment_id
                                    join shippments as s on o.shippment_id=s.shippment_id
                                    join depots as d on d.depot_id=s.depot_id
                                    where p.status='Completed' and d.location = %s
                                    """,(selected_location_id,))
                            
                order_number_all = cursor.fetchall()            

            else:
 
                cursor.execute("""
                                    select o.order_id, p.status, d.location from orders as o
                                    join payments as p on o.payment_id = p.payment_id
                                    join shippments as s on o.shippment_id=s.shippment_id
                                    join depots as d on d.depot_id=s.depot_id
                                    where p.status='Completed'
                                    """)
                            
                order_number_all = cursor.fetchall()
            #return render_template('test.html',order_number_all=order_number_all)

            # change the data to the form (id, packing,ready,out,delivered)

            # define a array with 6 items in a row without 'bgin' 
            order_status_all=[]
            h = len(order_number_all)
            order_status_all = [['' for x in range(6)] for y in range(h)] 

            #get different resp list

        # get packing and delivery personnel list 
            cursor.execute('select s.staff_id, s.given_name,s.responsibility_id,d.location from staff as s join depots as d on s.depot_id = d.depot_id where responsibility_id !=1')
            staff_all = cursor.fetchall()
            
            #get all staff name:
            cursor.execute(' select given_name from staff')
            staff_name_all = cursor.fetchall()

            # get max_order status list
            cursor.execute("""
                                        select o.order_id,max(oa.order_status_type_id) as order_status
                                        from orders as o 
                                        left join order_assignments as oa on o.order_id=oa.order_id
                                        left join payments as p on o.payment_id = p.payment_id
                                        where p.status='Completed' 
                                        group by o.order_id order by o.order_id, order_status desc;
                                    """)
            max_status= cursor.fetchall()         

            #fill in the array 
            i = 0
#compare with manager

            for order_number in order_number_all:                
                order_status_all[i].insert(0,order_number[2])                
                order_status_all[i].insert(1,order_number[0])
                ## fill in 'begin' 
                for status in max_status:

                    if status[0] == order_number[0]:

                        # check if there's no assignment 
            
                        order_status_all[i].insert(2,'Begin')              


                #insert name into the list
                for order_process in order_process_all:
                    if order_process[0] == order_number[0]:
                        for staff_name in staff_name_all:
                            if order_process[2] == staff_name[0]:
                                order_status_all[i].insert(2,order_process[2])


                #increase i         
                i = i +1
            #return render_template('test.html',order_status_all=order_status_all)
            # return render_template('manager-order_list.html',msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=order_status_all)
            #  # order_status_all ends
        #filter function script
            selected_status_id = request.form.get('status_id')
            # #create another given name list for the loop
            staff_name_all1 = staff_name_all
            #test OK
            # return render_template('test.html',order_status_all=order_status_all)
            staffid= request.form.get('staffid')
            orderid= request.form.get('orderid')
            rowid= request.form.get('rowid')

            # #if there's selected filter item
            if selected_status_id:
                status_filter_result =[]
                # check if index position 4 has staff name or not
                if selected_status_id == 'Delivered':       
                    #test OK        
                    # return render_template('test.html',order_status_all=order_status_all,status_filter_result=selected_status_id)

                    for status in order_status_all:
                        # test OK
                        # return render_template('test.html',status_filter_result=2)
                
                        for staff in staff_name_all:
                            if status[5] == staff[0]:                        
                                status_filter_result.append(status)
                    #    test OK 
                    # return render_template('test.html',status_filter_result=status_filter_result)
                    # return render_template('test.html',order_status_all=order_status_all)
                    #return redirect(url_for('manager_orderlist',order_status_all=status_filter_result))
                    #nok
                    return render_template('admin-order_list.html',msg=msg,all_location=all_location,selected_location_id=selected_location_id,selected_status_id=selected_status_id,order_status_types=order_status_types,staff_all=staff_all,order_number_all=order_number_all,admin_info=admin_info,order_status_all=status_filter_result)


                elif selected_status_id == 'On delivery vehicle':
                    # check if index position has staff name and index+1 doesn't have staff name
                    for status in order_status_all:
                        # status_filter_result.append([status])
                        for staff in staff_name_all:
                            if status[4] == staff[0] and status[5] == 'Begin':
                                #test 
                                # return render_template('test.html',status_filter_result=status[int(selected_status_id)])
                                status_filter_result.append(status)
                    return render_template('admin-order_list.html',msg=msg,all_location=all_location,selected_location_id=selected_location_id,selected_status_id=selected_status_id,order_status_types=order_status_types,staff_all=staff_all,order_number_all=order_number_all,admin_info=admin_info,order_status_all=status_filter_result)

                
                elif selected_status_id =='Ready for delivery':
                    # check if index position has staff name and index+1 doesn't have staff name
                    for status in order_status_all:
                        # status_filter_result.append([status])
                        for staff in staff_name_all:
                            if status[3] == staff[0] and status[4] == 'Begin':
                                #test 
                                # return render_template('test.html',status_filter_result=status[int(selected_status_id)])
                                status_filter_result.append(status)
                    return render_template('admin-order_list.html',msg=msg,all_location=all_location,selected_location_id=selected_location_id,selected_status_id=selected_status_id,order_status_types=order_status_types,staff_all=staff_all,order_number_all=order_number_all,admin_info=admin_info,order_status_all=status_filter_result)


                elif selected_status_id =='Preparing':
                    # check if index position has staff name and index+1 doesn't have staff name
                    for status in order_status_all:
                        # status_filter_result.append([status])
                        for staff in staff_name_all:
                            if status[2] == staff[0] and status[3] == 'Begin':
                                #test 
                                # return render_template('test.html',status_filter_result=status[int(selected_status_id)])
                                status_filter_result.append(status)
                        
                    # # test
                    # return render_template('test.html',status_filter_result=status_filter_result)



                    return render_template('admin-order_list.html',msg=msg,all_location=all_location,selected_location_id=selected_location_id,selected_status_id=selected_status_id,order_status_types=order_status_types,staff_all=staff_all,order_number_all=order_number_all,admin_info=admin_info,order_status_all=status_filter_result)

                    # return redirect(url_for('manager_orderlist',order_status_all=status_filter_result))
                else:
                    return render_template('admin-order_list.html',msg=msg,all_location=all_location,selected_location_id=selected_location_id,selected_status_id=selected_status_id,order_status_types=order_status_types,staff_all=staff_all,order_number_all=order_number_all,admin_info=admin_info,order_status_all=order_status_all)

            
            elif staffid:
                cursor.execute('insert into order_assignments values (%s,%s,%s,%s)', (orderid,rowid,staffid,todaydate,))
                
                if rowid == '2':
                    # reduce stock when ready for deliver
                    #get order info
                    cursor.execute("""
                                    select o.order_id,ol.product_id,ol.product_quantity,s.depot_id from orders as o 
                                    join order_lines as ol on o.order_id=ol.order_id
                                    join shippments as s on o.shippment_id=s.shippment_id
                                    where o.order_id=%s;
                                   """,(orderid,))
                    order_product_all = cursor.fetchall()
                    # test OK
                    # return render_template('test.html',order_product_all=order_product_all)
                    for product in order_product_all:
                        cursor.execute('select quantity from stock where product_id=%s and depot_id=%s',(product[1],depot[0],))
                        stock_quantity = cursor.fetchone()
                        if stock_quantity is None:
                            continue
                        else:
                            new_stock_quantity = stock_quantity[0] - product[2]
                            cursor.execute('update stock set quantity=%s where product_id=%s and depot_id=%s',(new_stock_quantity,product[1],depot[0],) )


                msg='You have successfully changed the task!'
                #return render_template('test.html',staffid=staffid,orderid=orderid,rowid=rowid)
                return redirect(url_for('admin_orderlist',msg=msg))
            else:
                return render_template('admin-order_list.html',msg=msg,all_location=all_location,selected_location_id=selected_location_id,selected_status_id=selected_status_id,order_status_types=order_status_types,staff_all=staff_all,order_number_all=order_number_all,admin_info=admin_info,order_status_all=order_status_all)

        
def set_product_in_stock(product_id, in_stock):
    cursor=getCursor()

    cursor.execute("UPDATE products SET product_status = %s WHERE product_id = %s", (in_stock, product_id))
    cursor.close()


def schedule_product_availability(product_id, start_time, end_time):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: set_product_in_stock(product_id, 1), 'date', run_date=start_time)
    scheduler.add_job(lambda: set_product_in_stock(product_id, 0), 'date', run_date=end_time)
    scheduler.start()

@app.route('/admin/order_incoming', methods=['GET', 'POST'])
def admin_order_incoming():
    msg = request.args.get('msg', '')
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 1:  # Check if the user is logged in and has admin role (role == 1)
        # Execute a SQL query to fetch the admin's role, full name, and profile picture
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()  # Fetch the result of the query

        searchinput = request.args.get('searchinput', '').strip()  # Get the search input from the request, default to an empty string if not present
        selected_order_status = request.args.get('order_status')  # Get the selected order status from the request
        order_date_str = request.args.get('order_date')  # Get the order date from the request

        order_date = None
        if order_date_str:  # Convert the order date string to a date object if provided
            order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()

        sort_by = request.args.get('sort_by', 'order_date')  # Get the sorting column, default to 'order_date'
        reverse = request.args.get('reverse', 'False') == 'True'  # Determine if sorting should be in reverse order

        sort_column_map = {
            'order_date': 'order_date',
            'order_id': 'order_id',
            'full_name': 'full_name',
            'delivery_status': 'delivery_status',
        }
        sort_column = sort_column_map.get(sort_by, 'order_date')  # Get the actual column name for sorting

        # Construct the SQL query to fetch incoming orders with various filters
        query = '''
            SELECT 
                orders.order_id,
                IFNULL(CONCAT(customers.given_name, ' ', customers.family_name), accounts.account_name) AS full_name,
                COALESCE(ost.order_status_type_name, 'Pending') AS delivery_status,
                orders.order_date
            FROM 
                orders 
                LEFT JOIN customers ON customers.user_id = orders.user_id
                LEFT JOIN accounts ON accounts.user_id = orders.user_id
                LEFT JOIN (
                    SELECT 
                        order_id, 
                        MAX(order_status_type_id) as latest_status_id 
                    FROM 
                        order_assignments 
                    GROUP BY 
                        order_id
                ) oa ON orders.order_id = oa.order_id
                LEFT JOIN order_status_types ost ON oa.latest_status_id = ost.order_status_type_id
            WHERE 1=1
        '''

        params = []

        if searchinput:  # Add search input condition to the query
            query += " AND (customers.given_name LIKE %s OR customers.family_name LIKE %s OR accounts.account_name LIKE %s)"
            params.extend([f'%{searchinput}%', f'%{searchinput}%', f'%{searchinput}%'])

        if selected_order_status:  # Add selected order status condition to the query
            query += " AND COALESCE(ost.order_status_type_name, 'Pending') = %s"
            params.append(selected_order_status)

        if order_date:  # Add order date condition to the query
            query += " AND DATE(orders.order_date) = %s"
            params.append(order_date)

        query += f" ORDER BY {sort_column} {'DESC' if reverse else 'ASC'}"  # Add ORDER BY clause to the query

        cursor.execute(query, params)  # Execute the query with the parameters
        orders = cursor.fetchall()  # Fetch all results

        # Execute a SQL query to fetch all distinct order status types including 'Pending'
        cursor.execute('''SELECT DISTINCT order_status_type_name FROM order_status_types
                          UNION SELECT 'Pending' AS order_status_type_name''')
        order_status = cursor.fetchall()  # Fetch all results

        # Render the admin-order_incoming.html template with the fetched data
        return render_template('admin-order_incoming.html', admin_info=admin_info, location=session['location'][0], orders=orders, order_status=order_status, searchinput=searchinput, selected_order_status=selected_order_status, sort_by=sort_by, reverse=reverse, msg=msg, order_date=order_date_str)
    else:
        return redirect(url_for('logout'))  # Redirect to logout if the user is not logged in or doesn't have the admin role


@app.route('/admin/order_incoming_detail/<order_id>')
def admin_order_incoming_detail(order_id):
    msg = request.args.get('msg', '')
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 1:  # Check if the user is logged in and has admin role (role == 1)
        # Execute a SQL query to fetch the admin's role, full name, and profile picture
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()  # Fetch the result of the query

        # Execute a SQL query to fetch order details including customer information, payment, and status
        cursor.execute("""
                        SELECT 
                        orders.order_id,
                        orders.order_date,
                        COALESCE(order_status_types.order_status_type_name, 'Pending') AS delivery_status,
                        IFNULL(CONCAT(customers.given_name, ' ', customers.family_name), accounts.account_name) AS full_name,
                        IFNULL(customers.customer_address, accounts.account_address) AS customer_address,
                        IFNULL(customers.phone_number, accounts.phone_number) AS phone_number,
                        IFNULL(customers.email, accounts.email) AS email,
                        payments.amount AS total_amount
                    FROM 
                        orders 
                        LEFT JOIN (
                            SELECT 
                                order_id, 
                                MAX(order_status_type_id) as latest_status_id 
                            FROM 
                                order_assignments 
                            GROUP BY 
                                order_id
                        ) latest_assignment ON orders.order_id = latest_assignment.order_id
                        LEFT JOIN order_status_types ON latest_assignment.latest_status_id = order_status_types.order_status_type_id
                        LEFT JOIN customers ON customers.user_id = orders.user_id
                        LEFT JOIN accounts ON accounts.user_id = orders.user_id
                        LEFT JOIN payments ON payments.payment_id = orders.payment_id
                    WHERE 
                        orders.order_id = %s
                       """, (order_id,))
        theorder = cursor.fetchone()  # Fetch the result of the query

        # Execute a SQL query to fetch all order lines for the current order
        cursor.execute('''SELECT 
                            COALESCE(boxes.box_name, product.product_name) AS product_name,
                            products.product_price,
                            order_lines.product_quantity
                        FROM 
                            order_lines
                            LEFT JOIN products ON products.product_id = order_lines.product_id
                            LEFT JOIN product ON products.SKU = product.SKU
                            LEFT JOIN boxes ON products.SKU = boxes.SKU
                        WHERE 
                            order_lines.order_id = %s''', (order_id,))
        order_lines = cursor.fetchall()  # Fetch all results

        # Define the order statuses
        order_statuses = [
            {"id": 0, "name": "Pending"},
            {"id": 1, "name": "Preparing"},
            {"id": 2, "name": "Ready for delivery"},
            {"id": 3, "name": "On delivery vehicle"},
            {"id": 4, "name": "Delivered"}
        ]

        # Render the admin-order_incoming_detail.html template with the fetched data
        return render_template('admin-order_incoming_detail.html', order_lines=order_lines, role=role, admin_info=admin_info, location=session['location'][0], theorder=theorder, msg=msg, order_statuses=order_statuses)       
    else: 
        return redirect(url_for('logout'))  # Redirect to logout if the user is not logged in or doesn't have the admin role

@app.route('/admin/account-holder-list/profile/manage-credit-limit', methods=['GET', 'POST'])
def admin_manage_credit_limit():
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')

    # Check if the user is logged in and has admin role
    if 'loggedin' in session and role == 1:
        # Get a cursor object to interact with the database
        cursor = getCursor()

        # Fetch admin information for extension of admin.html in the template
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()

        if request.method == 'GET':
            account_holder_id = request.args.get('account_holder_id')
            if account_holder_id:
                cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name, u.username 
                                  FROM accounts AS a 
                                  JOIN depots AS d ON a.city = d.depot_id 
                                  JOIN users AS u ON a.user_id = u.user_id 
                                  JOIN roles ON u.role_id = roles.role_id 
                                  WHERE a.account_id = %s""", (account_holder_id,))
                profile = cursor.fetchone()
                cursor.execute("""SELECT * FROM accounts WHERE account_id = %s""", (account_holder_id,))
                account_info = cursor.fetchone()
                return render_template('admin-manage_credit_limit.html', account_holder_id=account_holder_id, account_info=account_info, admin_info=admin_info, role=role, location=session['location'][0], profile=profile)
            else:
                return redirect(url_for('admin_account_holder_list'))

        elif request.method == 'POST':
            new_credit_limit = request.form['new_credit_limit']
            account_holder_id = request.form['account_holder_id']
            if account_holder_id and new_credit_limit:
                cursor.execute("""UPDATE accounts SET credit_limit_monthly = %s WHERE account_id = %s""", (new_credit_limit, account_holder_id))
                msg = "Credit limit has been successfully updated!"
                return redirect(url_for('admin_view_account_holder_profile', account_holder_id=account_holder_id, msg=msg))
            else:
                error_msg = "Failed to update credit limit. Please ensure all fields are filled out."
                cursor.execute("""SELECT * FROM accounts WHERE account_id = %s""", (account_holder_id,))
                account_info = cursor.fetchone()
                return render_template('admin-manage_credit_limit.html', account_info=account_info, admin_info=admin_info, role=role, location=session['location'][0], error_msg=error_msg)

    else:
        return redirect(url_for('logout'))

@app.route('/admin/credit_limit_pending_requests', methods=['GET'])
def admin_credit_limit_pending_requests():
    role = session.get('role')
    user_id = session.get('user_id')
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg= ''

    if 'loggedin' in session and role == 1:
        cursor = getCursor()

        cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name, u.username 
                            FROM accounts AS a 
                            JOIN depots AS d ON a.city = d.depot_id 
                            JOIN users AS u ON a.user_id = u.user_id 
                            JOIN roles ON u.role_id = roles.role_id 
                            WHERE a.account_id = %s""", (user_id,))
        profile = cursor.fetchone()

        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()

        status_filter = request.args.get('status_filter')
        
        if status_filter:
            cursor.execute('''SELECT applications.*, accounts.account_name, accounts.credit_limit_monthly AS current_limit
                              FROM applications
                              INNER JOIN accounts ON applications.applied_by = accounts.user_id 
                              WHERE applications.status = %s''', (status_filter,))
        else:
            cursor.execute('''SELECT applications.*, accounts.account_name, accounts.credit_limit_monthly AS current_limit
                              FROM applications
                              INNER JOIN accounts ON applications.applied_by = accounts.user_id''')

        pending_requests = cursor.fetchall()

        return render_template('admin_credit_limit_pending_requests.html', msg=msg,admin_info=admin_info, pending_requests=pending_requests, profile=profile, user_id=user_id)
    else:
        return redirect(url_for('logout'))


@app.route('/admin/credit_limit_request_detail_<int:application_id>', methods=['GET', 'POST'])
def admin_credit_limit_request_detail(application_id):
    cursor = getCursor()
    user_id = session['user_id']
    role = session.get('role')

    if 'loggedin' in session and role == 1:
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()

        cursor.execute('''SELECT applications.*, accounts.account_name, accounts.credit_limit_monthly AS current_limit
                          FROM applications
                          INNER JOIN accounts ON applications.applied_by = accounts.user_id 
                          WHERE applications.application_id = %s''', (application_id,))
        request_detail = cursor.fetchone()

        if request_detail:
            if request.method == 'POST':
                action = request.form['action']
                if action == 'approve':
                    new_limit = request_detail[1]  # Requested Credit Limit
                    cursor.execute('''UPDATE applications SET status = 'Approved' WHERE application_id = %s''', (application_id,))
                    cursor.execute('''UPDATE accounts SET credit_limit_monthly = %s WHERE user_id = (SELECT applied_by FROM applications WHERE application_id = %s)''', (new_limit, application_id))
                    msg = 'You have approved the application!'                    
                    
                    
                    reason = request.form['increase_reason']
                    if reason == "new account application":                
                        cursor.execute('select applied_by from applications where application_id = %s''', (application_id,))
                        user_id_account = cursor.fetchone()
                        cursor.execute("update users set status='Active' where user_id=%s",(user_id_account[0],))
                        return redirect(url_for('admin_credit_limit_pending_requests',msg=msg))

                    return redirect(url_for('admin_credit_limit_pending_requests',msg=msg))
                
                elif action == 'decline':
                    decline_reason = request.form['decline_reason']
                    cursor.execute('''UPDATE applications SET status = 'Declined', decline_reason = %s WHERE application_id = %s''', (decline_reason, application_id))
                    msg = 'You have declined the application!'
                    return redirect(url_for('admin_credit_limit_pending_requests',msg=msg))
            return render_template('admin_credit_limit_request_detail.html', admin_info=admin_info, request_detail=request_detail)
        else:
            return render_template('admin_credit_limit_request_detail.html', admin_info=admin_info, request_detail=None)
    else:
        return redirect(url_for('logout'))

# @app.route('/manager/application-list')
# def manager_application_list():

#     role = session.get('role')
#     msg=''
#     cursor = getCursor()
#     user_id = session['user_id']
#     cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
#                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
#                           INNER JOIN staff ON staff.user_id = users.user_id 
#                           WHERE users.user_id = %s''', (user_id,))
#     manager_info = cursor.fetchone()

#     cursor.execute('''SELECT depot_id FROM staff WHERE user_id = %s''', (user_id,))
#     depot_info = cursor.fetchone()

#     if 'loggedin' in session and role == 2:
#         if request.method == 'GET':
#             cursor.execute('select a.*,accounts.account_name from applications as a join accounts on a.applied_by = accounts.user_id where accounts.city = %s',(depot_info[0],))
#             applicationlist = cursor.fetchall()

#             return render_template('manager-application_list.html',msg=msg,applicationlist=applicationlist, manager_info=manager_info)
 
#         # else:
#             # search and filter function


# @app.route('/manager/application/<application_id1>', methods=["GET","POST"])
# def manager_application_details(application_id1):
#     # Get the user's role from the session
#     role = session.get('role')
#     # Get the user's ID from the session
#     user_id = session.get('user_id')
#     # Get a cursor object to interact with the database
#     cursor=getCursor()
#     # Fetch admin information for use of staff.html extension in the template
#     cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
#                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
#                           INNER JOIN staff ON staff.user_id = users.user_id 
#                           WHERE users.user_id = %s''', (user_id,))
#     manager_info = cursor.fetchone()
#     if 'loggedin' in session and role == 2: 
#         cursor=getCursor()

#         if request.args.get('msg'):
#             msg = request.args.get('msg')
#         else: 
#             msg = ''
       
#         if request.method == 'GET':


#             cursor.execute("""select a.*,accounts.account_name from applications as a join accounts on a.applied_by = accounts.user_id
#                         WHERE application_id = %s""", (application_id1,)) 
#             application = cursor.fetchone()

#             return render_template('manager-application_details.html', manager_info=manager_info, application=application, role=role, msg=msg)
#         else:
#             cursor.execute('UPDATE applications SET status="Approved" WHERE application_id = %s;', (application_id1,))
#             cursor.execute('selsect * from applications where application_id=%s',(application_id1,))
#             application_info = cursor.fetchone()
#             cursor.execute('update accounts set credit_limit_monthly=%s where user_id=%s',(application_info[1],application_info[3],))
#             msg = 'Application has been approved.'
#     else:
#         # If user is not logged in or doesn't have the required role, redirect to home page
#         return redirect(url_for('logout'))
    

# @app.route('/manager/application/reject/<application_id1>')
# def manager_application_reject(application_id1):
#     cursor = getCursor()
#     cursor.execute('UPDATE application SET status="Declined" WHERE application_id = %s;', (application_id1,))
#     msg = 'Application has been declined.'
#     return redirect( url_for('manager_application_list', msg=msg))


@app.route('/admin/news', methods=['GET', 'POST'])
def admin_news():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    # Fetch admin information for use of admin.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()

    if 'loggedin' in session and role == 1:
        if request.method == 'POST':
            searchinput = request.form.get('searchinput', '').strip()
            order = request.form.get('order')
        else:
            searchinput = request.args.get('searchinput', '').strip()
            order = request.args.get('order')
        
        msg = request.args.get('msg', '')

        # Fetch news data based on the search query
        if searchinput:
            # Perform search in the database based on the title search input
            cursor.execute('''SELECT * FROM news 
                              WHERE title LIKE %s
                              ORDER BY publish_date {}, news_id {}'''.format(order or 'DESC', order or 'DESC'), ('%' + searchinput + '%',))
            news_list = cursor.fetchall()
        else:
            # If no search input is provided, fetch all news
            cursor.execute('SELECT * FROM news ORDER BY publish_date {}, news_id {}'.format(order or 'DESC', order or 'DESC'))
            news_list = cursor.fetchall()

        # Render template with the list of news
        return render_template('admin-news.html', admin_info=admin_info, role=role, news_list=news_list, searchinput=searchinput, order=order, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


@app.route('/admin/news/<int:news_id>', methods=['GET'])
def admin_news_details(news_id):
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    # Fetch admin information for use of admin.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()

    if 'loggedin' in session and role == 1:
        cursor.execute('''SELECT news.*, CONCAT(staff.given_name, ' ', staff.family_name) AS full_name
                   FROM news 
                   INNER JOIN staff ON news.created_by = staff.user_id
                   WHERE news_id = %s''', (news_id,))
        news_item = cursor.fetchone()

        if news_item:
            return render_template('admin-news_details.html', news_item=news_item, admin_info=admin_info, role=role)
        else:
            return redirect(url_for('error', msg='News not found'))   
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))  

@app.route('/admin/news/publish', methods=['GET', 'POST'])
def admin_publish_news():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    # Fetch admin information for use of admin.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()

    if 'loggedin' in session and role == 1:
        if request.method == 'POST':
            title = request.form['title'].strip()
            content = request.form['content'].strip()
            pic = request.files.get('pic')
            msg = ''
            
            # Validate inputs
            if not title or not content:
                msg = 'Title and content are required!'
                return render_template('admin-news_publish.html', msg=msg, admin_info=admin_info, role=role)
            
            # Handle file upload
            pic_filename = None
            if pic:
                if allowed_file(pic.filename):
                    pic_filename = secure_filename(pic.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], pic_filename)
                    pic.save(filepath)
                    fixed_filepath = filepath.replace("\\", "/")
                else:
                    msg = 'Invalid file format! Please upload files with extensions: png, jpg, jpeg, gif.'
                    return render_template('admin-news_publish.html', msg=msg, admin_info=admin_info, role=role)
            else:
                fixed_filepath = "app/static/assets/img/default_news.jpg"  # Default image if none uploaded 
            
            # Insert the news into the database
            publish_date = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''INSERT INTO news (title, content, pic, publish_date, created_by, depot_id)
                              VALUES (%s, %s, %s, %s, %s, 0)''', (title, content, fixed_filepath, publish_date, user_id))
            
            msg = 'News published successfully!'
            return redirect(url_for('admin_news', msg=msg))
        
        return render_template('admin-news_publish.html', admin_info=admin_info, role=role)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/admin/balancechecking', methods=['GET', 'POST'])
def admin_balance_checking():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 1:  # Check if the user is logged in and has admin role (role == 1)
        # Execute a SQL query to fetch the admin's role, full name, and profile picture
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()  # Fetch the result of the query

        searchinput = request.args.get('searchinput', '').strip()  # Get the search input from the request, default to an empty string if not present
        selected_status = request.args.get('status')  # Get the selected status from the request
        sort_by = request.args.get('sort_by')  # Get the sorting column from the request
        reverse = request.args.get('reverse', 'False') == 'True'  # Determine if sorting should be in reverse order

        # Define the mapping of sort_by values to actual column names
        sort_column_map = {
            'account_name': 'accounts.account_name',
            'balance': 'accounts.balance',
            'status': 'users.status',
            'credit_limit': 'accounts.credit_limit_monthly'
        }
        sort_column = sort_column_map.get(sort_by, 'accounts.account_name')  # Get the actual column name for sorting

        # Construct the SQL query to fetch accounts with balance < 0 and payments not made in the last 30 days
        query = '''SELECT 
                        accounts.account_id,
                        accounts.account_name,
                        accounts.account_address,
                        accounts.email,
                        accounts.phone_number,
                        accounts.balance,
                        users.status,
                        accounts.credit_limit_monthly,
                        payments.payment_date
                    FROM 
                        accounts
                        LEFT JOIN users ON accounts.user_id = users.user_id 
                        INNER JOIN payments ON payments.user_id = accounts.user_id 
                    WHERE accounts.balance < 0 AND payments.payment_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)'''

        params = []  # Initialize the parameters list

        if searchinput:  # Add search input condition to the query
            try:
                balance_value = float(searchinput)
                query += " AND accounts.balance = %s"
                params.append(balance_value)
            except ValueError:
                query += " AND accounts.account_name LIKE %s"
                params.append(f'%{searchinput}%')

        if selected_status:  # Add selected status condition to the query
            query += " AND users.status = %s"
            params.append(selected_status)

        query += f" ORDER BY {sort_column} {'DESC' if reverse else 'ASC'}"  # Add ORDER BY clause to the query

        cursor.execute(query, params)  # Execute the query with the parameters
        accounts = cursor.fetchall()  # Fetch all results

        statuses = ["Active", "Inactive"]  # Define possible account statuses

        # Render the admin-balance_checking.html template with the fetched data
        return render_template('admin-balance_checking.html', admin_info=admin_info, accounts=accounts, statuses=statuses, searchinput=searchinput, selected_status=selected_status, sort_by=sort_by, reverse=reverse)
    else:
        return redirect(url_for('logout'))  # Redirect to logout if the user is not logged in or doesn't have the admin role


@app.route('/admin/balancechecking_detail/<int:account_id>')
def admin_balance_checking_detail(account_id):
    role = session.get('role') 
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 1:  # Check if the user is logged in and has admin role (role == 1)
        # Execute a SQL query to fetch the admin's role, full name, and profile picture
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles 
                           INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        admin_info = cursor.fetchone()  # Fetch the result of the query
        
        # Execute a SQL query to fetch account details including address, email, phone number, balance, and status
        cursor.execute('''SELECT 
                            accounts.account_id,
                            accounts.account_name,
                            accounts.account_address,
                            accounts.email,
                            accounts.phone_number,
                            accounts.balance,
                            users.status
                          FROM 
                            accounts 
                            INNER JOIN users ON accounts.user_id = users.user_id
                          WHERE accounts.account_id = %s''', (account_id,))
        account = cursor.fetchone()  # Fetch the result of the query

        # Execute a SQL query to fetch all payments related to the current account
        cursor.execute('''SELECT 
                            payments.payment_id,
                            payments.payment_date,
                            payments.amount,
                            payments.status
                          FROM 
                            payments
                          WHERE payments.user_id = (SELECT user_id FROM accounts WHERE account_id = %s)''', (account_id,))
        payments = cursor.fetchall()  # Fetch all results

        # Render the admin-balance_checking_detail.html template with the fetched data
        return render_template('admin-balance_checking_detail.html', admin_info=admin_info, account=account, payments=payments)
    else: 
        return redirect(url_for('logout'))  # Redirect to logout if the user is not logged in or doesn't have the admin role

@app.route('/admin/subscription-list', methods=['GET', 'POST'])
def admin_subscription_list():
    # Get the user's role from the session
    role = session.get('role')
    
    # Get the user's ID from the session
    user_id = session.get('user_id')
    
    # Get a cursor object to interact with the database
    cursor = getCursor()
    
    # Fetch admin information for use in the admin.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                      FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                      INNER JOIN staff ON staff.user_id = users.user_id 
                      WHERE users.user_id = %s''', (user_id,))
    admin_info = cursor.fetchone()

    if 'loggedin' in session and role == 1:
        # Base query for fetching subscription list
        base_query = '''SELECT 
                            COALESCE(CONCAT(customers.title, " ", customers.given_name, " ", customers.family_name), accounts.account_name) AS customer_name,
                            boxes.box_name AS product_name,
                            products.product_price AS price,
                            subscription_records.quantity AS quantity,
                            subscription_records.sub_date AS subscribed_date,
                            subscription_records.sub_type AS sub_type,
                            subscription_records.subscription_status
                        FROM subscription_records 
                        LEFT JOIN accounts ON subscription_records.user_id = accounts.user_id
                        LEFT JOIN customers ON subscription_records.user_id = customers.user_id
                        JOIN products ON subscription_records.product_id = products.product_id
                        JOIN boxes ON products.SKU = boxes.SKU
                        WHERE 1=1'''

        # Get status filter from request
        status_filter = request.args.get('status')
        if status_filter and status_filter != 'All Statuses':
            if status_filter == 'active':
                base_query += ' AND subscription_records.subscription_status = "active"'
            elif status_filter == 'cancelled':
                base_query += ' AND subscription_records.subscription_status = "cancelled"'

        # Get type filter from request
        type_filter = request.args.get('type')
        # Check if a subscription type filter is selected
        if type_filter and type_filter != 'All Types':
            if type_filter in ['Weekly', 'Biweekly', 'Monthly']:
                base_query += ' AND subscription_records.sub_type = %s'
                cursor.execute(base_query + ' ORDER BY subscription_records.record_id DESC;', (type_filter,))
            else:
                cursor.execute(base_query + ' ORDER BY subscription_records.record_id DESC;', ())
        else:
            cursor.execute(base_query + ' ORDER BY subscription_records.record_id DESC;', ())

        subscription_list = cursor.fetchall()

        # Sorting logic based on query parameters
        sort_by = request.args.get('sort_by')
        if sort_by:
            reverse = request.args.get('reverse') == 'True'

            if sort_by == 'Customer Name':
                subscription_list.sort(key=lambda x: x[0], reverse=reverse)
            elif sort_by == 'Product Name':
                subscription_list.sort(key=lambda x: x[1], reverse=reverse)
            elif sort_by == 'Price':
                subscription_list.sort(key=lambda x: x[2], reverse=reverse)
            elif sort_by == 'Quantity':
                subscription_list.sort(key=lambda x: x[3], reverse=reverse)
            elif sort_by == 'Subscribed Date':
                subscription_list.sort(key=lambda x: x[4], reverse=reverse)
            elif sort_by == 'Subscription Type':
                subscription_list.sort(key=lambda x: x[5], reverse=reverse)
            elif sort_by == 'Subscription Status':
                subscription_list.sort(key=lambda x: x[6], reverse=reverse)

        # Search functionality
        if request.method == 'POST':
            search_input = request.form.get('searchinput')
            if search_input:
                search_query = '''SELECT 
                                    COALESCE(CONCAT(customers.title, " ", customers.given_name, " ", customers.family_name), accounts.account_name) AS customer_name,
                                    boxes.box_name AS product_name,
                                    products.product_price AS price,
                                    subscription_records.quantity AS quantity,
                                    subscription_records.sub_date AS subscribed_date,
                                    subscription_records.sub_type AS sub_type,
                                    subscription_records.subscription_status
                                  FROM subscription_records 
                                  LEFT JOIN accounts ON subscription_records.user_id = accounts.user_id
                                  LEFT JOIN customers ON subscription_records.user_id = customers.user_id
                                  JOIN products ON subscription_records.product_id = products.product_id
                                  JOIN boxes ON products.SKU = boxes.SKU
                                  WHERE (customers.given_name LIKE %s OR customers.family_name LIKE %s OR accounts.account_name LIKE %s OR boxes.box_name LIKE %s)'''
                cursor.execute(search_query + ' ORDER BY subscription_records.record_id DESC;', (f'%{search_input}%', f'%{search_input}%', f'%{search_input}%', f'%{search_input}%'))
                subscription_list = cursor.fetchall()

        return render_template('admin_subscription_list.html', admin_info=admin_info, subscription_list=subscription_list, role=role, status_filter=status_filter, type_filter=type_filter)
    else: 
        return redirect(url_for('logout'))
