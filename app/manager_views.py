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
from datetime import date


hashing = Hashing(app)  #create an instance of hashing
from dateutil import relativedelta
from dateutil.relativedelta import relativedelta

from apscheduler.schedulers.background import BackgroundScheduler


UPLOAD_FOLDER = 'app/static/assets/img'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def getCursor():
    global dbconn
    global connection
    connection = mysql.connector.connect(user=connect.dbuser, \
    password=connect.dbpass, host=connect.dbhost, auth_plugin='mysql_native_password',\
    database=connect.dbname, autocommit=True)
    dbconn = connection.cursor()
    return dbconn

@app.route('/manager/dashboard')
def manager_dashboard():
# Check if user is logged in
    if 'loggedin' in session:
        role = session.get('role')  # Get the user's role from the session

        # Redirect based on user's role
        if role == 2:  
            # Get the user's ID from the session
            user_id = session.get('user_id')

            # Get a cursor object to interact with the database
            cursor = getCursor()

            # Execute a SQL query to fetch the manager's details including depot_id
            cursor.execute('SELECT * FROM staff WHERE user_id = %s', (user_id,))
            manager_details = cursor.fetchone()

            # Execute a SQL query to fetch the manager's role 
            cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
            manager_info = cursor.fetchone()

            if manager_details:
                # Extract depot_id from manager's details
                depot_id = manager_details[9]

                # Execute a SQL query to fetch the location based on depot_id
                cursor.execute('SELECT location FROM depots WHERE depot_id = %s', (depot_id,))
                location_result = cursor.fetchone()

                if location_result:
                    location = location_result[0]
                else:
                    location = "Location not found"

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
                    WHERE
                        customers.city = %s OR accounts.city = %s  
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
                ''', (depot_id, depot_id))

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
                               WHERE products.product_status=1 AND products.depot_id=%s AND product_categories.product_category_id !=8 AND product_categories.product_category_id !=7
                               ORDER BY products.product_id DESC
                               LIMIT 4;
                               ''', (depot_id,))
                recent_products = cursor.fetchall()


                cursor.execute('''SELECT products.product_id, boxes.box_name, CONCAT(units.unit_name, " ",product_categories.product_category_name) AS unit_name,
                               round(stock.quantity, 0), CONCAT(round(products.product_price * promotion_types.discount, 2)) AS final_price, boxes.pic FROM products
                               LEFT JOIN  product_categories ON products.product_category_id=product_categories.product_category_id
                               LEFT JOIN boxes ON products.SKU=boxes.SKU
                               LEFT JOIN units ON boxes.unit=units.unit_id
                               LEFT JOIN stock ON products.product_id=stock.product_id
                               LEFT JOIN promotion_types ON products.promotion_type_id=promotion_types.promotion_type_id
                               WHERE products.product_status=1 AND products.depot_id=%s AND product_categories.product_category_id !=8 AND product_categories.product_category_id =7
                               ORDER BY products.product_id DESC
                               LIMIT 4; 
                               ''', (depot_id,))
                recent_boxes = cursor.fetchall()
                
                # Fetch the 3 most recent news
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
                                WHERE 
                                    news.depot_id IN (0, %s)
                                ORDER BY 
                                    news.publish_date DESC,
                                    news.news_id DESC
                                LIMIT 4''', (depot_id,))
                recent_news = cursor.fetchall()

                cursor.execute('''SELECT * FROM customers WHERE city = %s ORDER BY user_id DESC LIMIT 4''', (depot_id,))
                recent_customers = cursor.fetchall()

                cursor.execute('''SELECT * FROM accounts WHERE city = %s AND balance <0 LIMIT 4''', (depot_id,))
                recent_accounts = cursor.fetchall()

                cursor.execute('''SELECT return_authorization.*, COALESCE(CONCAT(customers.title, " ", customers.given_name, " ", customers.family_name), accounts.account_name) as user_name, orders.order_id
                                FROM return_authorization LEFT JOIN orders on return_authorization.order_id=orders.order_id
                                LEFT JOIN customers ON customers.user_id=orders.user_id
                                LEFT JOIN accounts on accounts.user_id=orders.user_id
                                WHERE return_authorization.return_status='pending' AND (customers.city = %s or accounts.city = %s)
                                ORDER BY applied_date ASC LIMIT 4''', (depot_id, depot_id))
                refund_request = cursor.fetchall()


                cursor.execute('''SELECT users.user_id, staff.title, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic, staff.email, staff.phone_number
                                FROM users LEFT JOIN staff ON users.user_id=staff.user_id
                                WHERE staff.depot_id = %s AND users.role_id = 3
                                LIMIT 4
                               ;''', (depot_id,))
                staff_list = cursor.fetchall()

                # Fetch summary info for accounts and customers
                cursor.execute('''SELECT 
                                    (SELECT COUNT(*) FROM customers WHERE city = %s) AS total_customers,
                                    (SELECT COUNT(*) FROM orders o JOIN customers c ON o.user_id = c.user_id WHERE c.city = %s) AS total_orders,
                                    (SELECT SUM(p.amount) FROM payments p JOIN orders o ON p.payment_id = o.payment_id JOIN customers c ON o.user_id = c.user_id WHERE c.city = %s) AS total_revenue,
                                    (SELECT COUNT(*) FROM subscription_records sr JOIN customers c ON sr.user_id = c.user_id WHERE c.city = %s) AS total_subscriptions
                                  FROM dual;''', (depot_id, depot_id, depot_id, depot_id))
                customer_summary_info = cursor.fetchone()

                cursor.execute('''SELECT 
                                    (SELECT COUNT(*) FROM accounts WHERE city = %s) AS total_account_holders,
                                    (SELECT COUNT(*) FROM orders o JOIN accounts a ON o.user_id = a.user_id WHERE a.city = %s) AS total_orders,
                                    (SELECT SUM(p.amount) FROM payments p JOIN orders o ON p.payment_id = o.payment_id JOIN accounts a ON o.user_id = a.user_id WHERE a.city = %s) AS total_revenue,
                                    (SELECT COUNT(*) FROM subscription_records sr JOIN accounts a ON sr.user_id = a.user_id WHERE a.city = %s) AS total_subscriptions
                                  FROM dual;''', (depot_id, depot_id, depot_id, depot_id))
                account_summary_info = cursor.fetchone()

                # Combine summaries, handling None values gracefully
                total_customers = (customer_summary_info[0] or 0) + (account_summary_info[0] or 0)
                total_orders = (customer_summary_info[1] or 0) + (account_summary_info[1] or 0)
                total_revenue = (customer_summary_info[2] or 0) + (account_summary_info[2] or 0)
                total_subscriptions = (customer_summary_info[3] or 0) + (account_summary_info[3] or 0)


                cursor.execute('''SELECT subscription_records.*,
                                CONCAT(customers.title, ' ', customers.given_name, ' ', customers.family_name) AS customer_full_name,
                                accounts.account_name AS account_name, accounts.account_id
                                FROM subscription_records 
                                LEFT JOIN accounts ON subscription_records.user_id = accounts.user_id
                                LEFT JOIN customers ON subscription_records.user_id = customers.user_id
                                WHERE subscription_records.subscription_status ='active' AND customers.city = %s OR accounts.city = %s
                                ORDER BY subscription_records.record_id DESC
                                LIMIT 4
                                ;''', (depot_id, depot_id))
                recent_subscription = cursor.fetchall()

                todaydate = date.today()
                cursor.execute('select max(fresh_date) from daily_fresh_subscriptions')
                max_fresh_date = cursor.fetchone()
                if max_fresh_date[0]< todaydate:
                    fresh = 'yes'
                else:
                    fresh = 'no'



                # Render the manager dashboard template with location data
                return render_template('manager-dashboard.html', orders=orders, staff_list=staff_list, total_customers=total_customers, total_orders=total_orders, total_revenue=total_revenue, total_subscriptions=total_subscriptions, manager_details=manager_details, 
                                       manager_info=manager_info, location=location, recent_orders=recent_orders, recent_products=recent_products, recent_news=recent_news, recent_customers=recent_customers, 
                                       recent_accounts=recent_accounts, refund_request=refund_request, recent_boxes=recent_boxes,fresh=fresh, recent_subscription=recent_subscription)

            else:
                # Handle case where manager details are not found
                return render_template('error.html', error="Manager details not found")
        else:
            # Redirect to the error page since the user's role doesn't match any predefined roles
            return redirect(url_for('error'))
    # User is not logged in redirect to error page
    return redirect(url_for('logout'))


@app.route('/manager/stafflist',methods=['get','post'])
def manager_stafflist():
    role = session.get('role')
    cursor=getCursor()
    user_id = session['user_id']

            # Fetch profile images
    cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
    profile_image_url = cursor.fetchone()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    if 'loggedin' in session and role == 2:
        cursor=getCursor()
        cursor.execute("""select depot_id from staff where user_id = %s""", (user_id,))
        mydepot= cursor.fetchone()
        if request.method=='GET':
                
            cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.depot_id=%s and s.responsibility_id!=%s',(mydepot[0],1,))
            staffinfo= cursor.fetchall()
            
            return render_template('manager_staff_list.html', location=session['location'][0], manager_info=manager_info,mydepot=mydepot,allprofile=staffinfo, profile_image_url=profile_image_url)
        else:
            searchinput = request.form['searchinput']
            all= searchinput.split()
            if len(all)==0:
                cursor=getCursor()
                cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.depot_id=%s and s.responsibility_id!=%s',(mydepot[0],1,))
                allprofile=cursor.fetchall()
                return render_template('manager_staff_list.html', location=session['location'][0], manager_info=manager_info,allprofile=allprofile, profile_image_url=profile_image_url)

            elif len(all)==1:
                cursor=getCursor()
                parameter = ("%"+all[0]+"%")
                cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.depot_id=%s and s.responsibility_id!=%s and (given_name like %s or family_name like %s)',(mydepot[0],1,parameter,parameter,))
                allprofile=cursor.fetchall()
                return render_template('manager_staff_list.html', location=session['location'][0], manager_info=manager_info,allprofile=allprofile, profile_image_url=profile_image_url)

            elif len(all)==2:
                cursor=getCursor()
                parameter1 = ("%"+all[0]+"%")
                parameter2 = ("%"+all[1]+"%")
                cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.depot_id=%s and s.responsibility_id!=%s and ((given_name like %s and family_name like %s) or (given_name like %s and family_name like %s))',(mydepot[0],1,parameter1,parameter2,parameter2,parameter1,))
                allprofile=cursor.fetchall()
                return render_template('manager_staff_list.html', location=session['location'][0], manager_info=manager_info,allprofile=allprofile, profile_image_url=profile_image_url)
    else: 
        return redirect(url_for('logout'))


@app.route('/manager/profileupdate',methods= ['get','post'])
def manager_profileupdate():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor=getCursor()
    cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
    profile_image_url = cursor.fetchone()
    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    
    if 'loggedin' in session and role == 2: 
        if request.method=='GET':
            msg = ''
            cursor=getCursor()
            cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.user_id=%s',(user_id,))
            profileinfo= cursor.fetchone()


            return render_template("manager_profile_update.html", location=session['location'][0], manager_info=manager_info,profileinfo=profileinfo,msg=msg,profile_image_url= profile_image_url)
        else:
            title = request.form['title']
            first_name = request.form['first_name']
            family_name = request.form['family_name']
            phone_number = request.form['phone']
            email = request.form['email']
            depot=request.form['city']
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

                        return redirect(url_for('manager_profile',msg=msg))


                        #return render_template("manager_profile_update.html", location=session['location'][0], manager_info=manager_info,profileinfo="",msg=msg,profile_image_url=profile_image_url)

                    else: #if no pic uploaded, then no need to update image in database
                        cursor = getCursor()
                        cursor.execute("UPDATE staff set title=%s,given_name=%s,family_name=%s,email=%s,phone_number=%s where user_id=%s",(title,first_name,family_name,email,phone_number,user_id,))
                        msg="Profile has been successfully updated!"

                        return redirect(url_for('manager_profile',msg=msg))

                        #return render_template(url_for('manager_profile',msg=msg,location=session['location'][0],role=role,manager_info=manager_info))
                        #return render_template("manager_profile_update.html", location=session['location'][0], manager_info=manager_info,profileinfo="",msg=msg,profile_image_url=profile_image_url)
    else: 
        return redirect(url_for('logout'))



@app.route("/manager/deleteimg")
def manager_deleteimg():
    cursor=getCursor()
    user_id = session.get('user_id')
    cursor.execute("update staff set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",user_id,))
    msg="Image has been successfully deleted!"
    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
                            
    return render_template(url_for('manager_profile',msg=msg))

    
    #return render_template("manager_profile_update.html", location=session['location'][0], manager_info=manager_info,profileinfo="",msg=msg,profile_image_url='')



@app.route("/manager/profile")
def manager_profile():
    role = session.get('role')
    cart = session.get('cart', {})

    if request.args.get('msg'):
        msg = request.args.get('msg')
    else: 
        msg = ''

    if 'loggedin' in session and role==2:
        cursor =  getCursor()
        user_id = session.get('user_id')

        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                                FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                                INNER JOIN staff ON staff.user_id = users.user_id 
                                WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()


        
        cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.user_id=%s',(user_id,))
        profileinfo= cursor.fetchone()

        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()
        
        return render_template ('manager_profile.html', cart=cart,msg=msg,location=session['location'][0], role=role,manager_info=manager_info,profile=profileinfo, profile_image_url=profile_image_url)
        
    else:
        return redirect(url_for('logout'))

@app.route("/manager/addstaff",methods=["GET","POST"])
def manager_add_staff():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor =  getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    if 'loggedin' in session and role == 2:
        
        user_id = session['user_id']
        cursor=getCursor()
            # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()

        if request.method=='GET':
                #give it a new staff_id
            cursor.execute('select max(staff_id) from staff')
            max_id = cursor.fetchone()
            new_staff_id=max_id[0]+1
            cursor.execute('select * from responsibilities')
            resp_list = cursor.fetchall()
            cursor.execute('select s.depot_id,location from staff as s join depots as d on s.depot_id=d.depot_id where user_id=%s',(user_id,))
            depot_info=cursor.fetchone()
            return render_template('manager-add-staff.html', location=session['location'][0], manager_info=manager_info,msg='',depot_info=depot_info,resp_list=resp_list,new_staff_id=new_staff_id,profile_image_url=profile_image_url )
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

                # get depot_id that same as manager
                cursor.execute('select s.depot_id,location from staff as s join depots as d on s.depot_id=d.depot_id where user_id=%s',(user_id,))
                depot_info=cursor.fetchone()
                if files:

                    for file in files:
                    #if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        if filename=='':  # if no new image uploaded
                            cursor = getCursor()
                            cursor.execute('INSERT INTO staff VALUES (%s, %s, %s,%s,%s,%s, %s,%s,%s,%s)', (staff_id,new_userid,title,first_name,family_name,email,phone_number,"app/static/assets/img/avatar.jpg",responsibility1,depot_info[0],))

                        else:
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            fixed_filepath = filepath.replace("\\","/")
                            file.save(fixed_filepath)

                            cursor = getCursor()
                            cursor.execute('INSERT INTO staff VALUES (%s, %s, %s,%s,%s,%s, %s,%s,%s, %s)', (staff_id,new_userid,title,first_name,family_name,email,phone_number,fixed_filepath,responsibility1,depot_info[0],))
                msg="Profile has been successfully added!"

            return redirect(url_for('manager_stafflist',msg=msg))
            #return render_template("manager-add-staff.html", location=session['location'][0],  manager_info=manager_info,depot_info=depot_info,resp_list=resp_list,new_staff_id='',msg=msg, profile_image_url=profile_image_url)
    # else: 
    #     return redirect(url_for('error'))

@app.route('/manager/password_update', methods=['GET', 'POST'])
def manager_password_update():
    role = session.get('role')
    cart = session.get('cart', {})
    # Ensure the user is logged in and has the right role
    if 'loggedin' not in session or session.get('role') != 2:
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
    manager_info = cursor.fetchone()

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
            return redirect(url_for('manager_profile',cart=cart,location=session['location'][0],role=role,msg=msg,manager_info=manager_info))  # Redirect to the manager profile page after successful update


    if not manager_info:
        return render_template('error.html', error="manager details not found")

    return render_template('manager_password_update.html', cart=cart,location=session['location'][0], role=role,msg=msg,manager_info=manager_info) 

@app.route("/manager/staffprofile/<user_id1>")
def manager_staff_profile(user_id1):
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg=""
    role = session.get('role')
    if 'loggedin' in session and role == 2:
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
        manager_info = cursor.fetchone()
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

        return render_template ('manager-staff-profile.html', msg=msg, location=session['location'][0], manager_info=manager_info,profile=profile, profile_image_url=profile_image_url)       

    else: 
        return redirect(url_for('logout'))
 
@app.route("/manager/changestaffprofile/<user_id1>",methods=["GET","POST"])
def manager_change_staff_profile(user_id1):
    msg=""
    role = session.get('role')
    user_id = session['user_id']

    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    cursor.execute('select * from responsibilities')
    resp_all = cursor.fetchall()
    cursor.execute('select * from depots')
    depot_all = cursor.fetchall()
    cursor.execute('select * from roles')
    role_all = cursor.fetchall()
    if 'loggedin' in session and role == 2:
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
            return render_template("manager-change-staff-profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,manager_info=manager_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)
    
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
                    # if there's pic uploaded
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

                        return redirect(url_for('manager_staff_profile', user_id1=user_id1, msg=msg))



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



                        # cursor.execute('select p.*,u.status from profiles as p join users as u on p.user_id=u.user_id where p.user_id=%s',(user_id1,))
                        # profile=cursor.fetchone()

                        return redirect(url_for('manager_staff_profile', user_id1=user_id1, msg=msg))

    else: 
        return redirect(url_for('logout'))
    
@app.route("/manager/deletestaffimg/<user_id1>")
def manager_deletestaffimg(user_id1):
    user_id = session['user_id']

    cursor=getCursor()
    # update staff pic to default one when deleting pic
    cursor.execute("update staff set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",user_id1,))
    msg="Image has been successfully deleted!"
    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
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
    return render_template("manager-change-staff-profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,manager_info=manager_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)


#manager customer list
@app.route('/manager/customerlist',methods=['get','post'])
def manager_customerlist():
    role = session.get('role')
    user_id = session['user_id']
    cursor=getCursor()
    # Fetch the user's depot_id
    manager_depot = session.get('location')

    cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
    location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

    if 'loggedin' in session and role == 2:
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()
        # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()
        if request.method=='GET':

            cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4 and d.depot_id=%s
                      """,(location_id,))
            customerinfo= cursor.fetchall()
           
            return render_template('manager_customer_list.html', location=session['location'][0], manager_info=manager_info,allprofile=customerinfo, profile_image_url=profile_image_url)
        else:
            searchinput = request.form['searchinput']
            all= searchinput.split()
            # in case there's no search input
            if len(all)==0:
                cursor=getCursor()
                cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4  and d.depot_id=%s
                      """,(location_id,))
                allprofile=cursor.fetchall()
                return render_template('manager_customer_list.html', location=session['location'][0], manager_info=manager_info,allprofile=allprofile, profile_image_url=profile_image_url)
            #in case there's one word in search window
            elif len(all)==1:
                cursor=getCursor()
                parameter = ("%"+all[0]+"%")
                cursor.execute(""" 
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4   and d.depot_id=%s
                        and (given_name like %s or family_name like %s)""",(location_id,parameter,parameter,))
                allprofile=cursor.fetchall()
                return render_template('manager_customer_list.html', location=session['location'][0], manager_info=manager_info,allprofile=allprofile, profile_image_url=profile_image_url)
            # in case two words are input in search
            elif len(all)==2:
                cursor=getCursor()
                parameter1 = ("%"+all[0]+"%")
                parameter2 = ("%"+all[1]+"%")
                cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4 and d.depot_id=%s
                                and ((given_name like %s and family_name like %s) or (given_name like %s and family_name like %s))""",
                                (location_id,parameter1,parameter2,parameter2,parameter1,))
                allprofile=cursor.fetchall()
                return render_template('manager_customer_list.html', location=session['location'][0], manager_info=manager_info,allprofile=allprofile, profile_image_url=profile_image_url)
    else: 
        return redirect(url_for('logout'))


@app.route("/manager/customerprofile/<user_id1>")
def manager_customer_profile(user_id1):
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg=""
    role = session.get('role')
    if 'loggedin' in session and role == 2:
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
        manager_info = cursor.fetchone()
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

        return render_template ('manager-customer-profile.html', msg=msg, location=session['location'][0], manager_info=manager_info,profile=profile, profile_image_url=profile_image_url)       

    else: 
        return redirect(url_for('logout'))
 
@app.route("/manager/changecustomerprofile/<user_id1>",methods=["GET","POST"])
def manager_change_customer_profile(user_id1):
    msg=""
    role = session.get('role')
    user_id = session['user_id']

    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()

    cursor.execute('select * from depots')
    depot_all = cursor.fetchall()
    # make sure it's manager who logged in
    if 'loggedin' in session and role == 2:
        cursor=getCursor()

        # Fetch profile images
        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
        profile_image_url = cursor.fetchone()

        if request.method=='GET': # show page when 'get'
            
            cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where c.user_id=%s 
                       """
                       ,(user_id1,))
            profile = cursor.fetchone()
            return render_template("manager-change-customer-profile.html", location=session['location'][0], depot_all=depot_all,manager_info=manager_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)
    
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
                    # if pic is uploaded
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

                        return redirect(url_for('manager_customer_profile', user_id1=user_id1, msg=msg))


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

                        return redirect(url_for('manager_customer_profile',msg=msg,user_id1=user_id1))


                        # cursor.execute('select p.*,u.status from profiles as p join users as u on p.user_id=u.user_id where p.user_id=%s',(user_id1,))
                        # profile=cursor.fetchone()

                        return redirect(url_for('manager_customer_profile', user_id1=user_id1, msg=msg))

    else: 
        return redirect(url_for('logout'))
    
@app.route("/manager/deletecustomerimg/<user_id1>")
def manager_deletecustomerimg(user_id1):
    user_id = session['user_id']

    cursor=getCursor()
    # set customer pic to default one if deleting customer pic
    cursor.execute("update customers set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",user_id1,))
    msg="Image has been successfully deleted!"
    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
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
    return render_template("manager-change-customer-profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,manager_info=manager_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)


@app.route('/manager/accountlist',methods=['GET','POST'])
def manager_account_list():
    role = session.get('role')
    user_id = session['user_id']

    if 'loggedin' in session and role == 2:
        cursor=getCursor()
        cursor=getCursor()
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                            FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                            INNER JOIN staff ON staff.user_id = users.user_id 
                            WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()
      
        cursor.execute('select depot_id from staff where user_id=%s',(user_id,))
        my_depot = cursor.fetchone()
        if request.method=='GET':

            cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5 and a.city=%s""",(my_depot[0],))
            accountlist= cursor.fetchall()
           

            return render_template('manager-account_list.html', location=session['location'][0], manager_info=manager_info,cardHolderList=accountlist)
        else:
            searchinput = request.form['searchinput']
            all= searchinput.split()
            if len(all)==0:
                cursor=getCursor()
                cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5 and a.city=%s""",(my_depot[0],))              
                cardHolderList=cursor.fetchall()
                return render_template('manager-account_list.html', location=session['location'][0], manager_info=manager_info,cardHolderList=cardHolderList)

            elif len(all)==1:
                cursor=getCursor()
                parameter = ("%"+all[0]+"%")
                cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5 AND a.account_name LIKE %s""",(parameter,))
                cardHolderList=cursor.fetchall()
                return render_template('manager-account_list.html', location=session['location'][0], manager_info=manager_info,cardHolderList=cardHolderList)

            
    else: 
        return redirect(url_for('logout'))


@app.route('/manager/accountlist/profile',methods=['get','post'])
def manager_account_profile():
    
    role = session.get('role')
    account_holder_id = request.args.get('account_holder_id')

    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg = ''
    
    if 'loggedin' in session and role == 2:
        cursor =  getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                            FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                            INNER JOIN staff ON staff.user_id = users.user_id 
                            WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()

        cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name, u.username FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE a.account_id = %s""", (account_holder_id,))

        profile= cursor.fetchone()


        return render_template ('manager-account_profile.html', location=session['location'][0], manager_info=manager_info, profile=profile, msg=msg)
    
    else:
        return redirect(url_for('logout'))



@app.route('/manager/accountlist/profile/update',methods=['GET','POST'])

def manager_account_profile_update():

    role = session.get('role')
    msg=''
    cursor=getCursor()
    cursor.execute('select * from depots')
    depot_all=cursor.fetchall()
    user_id = session['user_id']
    account_user_id = request.args.get('account_user_id')
    depot_id = depot_all[0]
    print(account_user_id)

    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                            FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                            INNER JOIN staff ON staff.user_id = users.user_id 
                            WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()

    if 'loggedin' in session and role == 2:
       

        
       

       if request.method=='GET':
            
            cursor.execute("""select a.*,d.location,u.status,roles.role_name from accounts as a join depots as d on a.city = d.depot_id join users as u on a.user_id=u.user_id join roles on u.role_id = roles.role_id where a.user_id=%s and city=%s """,(account_user_id,depot_id[0],))
            profile = cursor.fetchone()
           
            return render_template("manager-change_account_profile.html", location=session['location'][0], depot_all=depot_all,manager_info=manager_info,profileinfo=profile,msg=msg)
    
       else:

            name = request.form['name']
            phone_number = request.form['phone']
            email = request.form['email']
            status = request.form['status']
            depot  = request.form['depot']
            files = request.files.getlist('image1') 
      

            if files:

                for file in files:
                    # in case new pic is uploaded
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

                        return redirect(url_for("manager_account_profile", account_holder_id=account_user_id, msg=msg))





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

                        return redirect(url_for('manager_account_profile',msg=msg))


                        return redirect(url_for("manager_account_profile", account_holder_id=profile[0], msg=msg))
 
    else:
        return redirect(url_for('logout'))



@app.route("/manager/accountlist/profile/delete-account-img")
def manager_delete_account_img():
    user_id = session['user_id']

    account_user_id = request.args.get('account_user_id')

    cursor=getCursor()
    # update account pic to default one if deleting the image
    cursor.execute("update accounts set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",account_user_id,))
    msg="Image has been successfully deleted!"
    cursor=getCursor()
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                            FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                            INNER JOIN staff ON staff.user_id = users.user_id 
                            WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
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
    return render_template("manager-change_account_profile.html", location=session['location'][0], depot_all=depot_all,role_all=role_all,resp_all=resp_all,manager_info=manager_info,profileinfo=profile,msg=msg,profile_image_url=profile_image_url)


@app.route('/manager/product-list', methods = ['GET', 'POST'])
def manager_product_list():
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else: 
        msg = ''
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor = getCursor()
    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    # Fetch all distinct categories from the database
    cursor.execute('''SELECT DISTINCT product_category_name FROM product_categories where product_category_id !="7" and product_category_id !="8"''')
    categories = [row[0] for row in cursor.fetchall()]
    if 'loggedin' in session and role == 2:
        location_id = None  # Assign a default value
        if request.method == 'POST':
            # Fetch the user's depot_id
            manager_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
            location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

            searchinput = request.form.get('searchinput', '').strip()
            selected_category = request.form.get('category')
        else:
            # If it's a GET request, get search input, and selected category from query parameters
            searchinput = request.args.get('searchinput', '').strip()
            selected_category = request.args.get('category')

        if searchinput:
            manager_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
            location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
            # Perform search in the database based on the search input
            query ='''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, pro.product_id 
                                FROM product p 
                                LEFT JOIN products pro ON p.SKU = pro.SKU
                                LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                LEFT JOIN stock on stock.product_id = pro.product_id 
                                Left join units on p.unit = units.unit_id
                                WHERE product_status="1" AND pro.product_category_id != "7" AND pro.product_category_id != "8" AND  pro.depot_id = %s
                                AND (p.SKU LIKE %s OR pc.product_category_name LIKE %s OR p.product_name LIKE %s)
                                ORDER BY pro.product_id DESC'''
            params = (location_id, f'%{searchinput}%', f'%{searchinput}%', f'%{searchinput}%')
            if selected_category and selected_category != 'all':
                query += " AND pc.product_category_name = %s"
                params += (selected_category,)
            cursor.execute(query, params)
            products = cursor.fetchall()

        # If no search input is provided, fetch all products
        else:
            if selected_category:
                # Fetch the user's depot_id
                manager_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
                location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
                cursor.execute('''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, pro.product_id
                                    FROM product p 
                                    LEFT JOIN products pro ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                               Left join units on p.unit = units.unit_id
                                    WHERE product_status="1" AND pro.product_category_id != "7" AND pro.product_category_id != "8" AND pro.depot_id = %s AND pc.product_category_name = %s
                                    ORDER BY pro.product_id DESC''', (location_id, selected_category,))
            else:
                # Fetch the user's depot_id for GET requests without form submission
                manager_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
                location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

                # Fetch all products
                cursor.execute('''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, pro.product_id  
                                    FROM product p 
                                    LEFT JOIN products pro ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN units on p.unit = units.unit_id
                                    WHERE product_status="1" AND pro.product_category_id != "7" AND pro.product_category_id != "8" AND pro.depot_id = %s
                                    ORDER BY pro.product_id DESC''', (location_id,))
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

        # Render template with the list of products
        return render_template('manager-product_list.html', location=session['location'][0], products=products, manager_info=manager_info, role=role, categories=categories, searchinput=searchinput, selected_category=selected_category, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))


@app.route('/manager/product-list/product', methods=["GET","POST"])
def manager_product_details():
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor=getCursor()
    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    if 'loggedin' in session and role == 2: 
        cursor=getCursor()

        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''

        product_id = request.args.get('product_id')

        cursor.execute("""SELECT p.SKU, p.product_name, pro.product_price, units.unit_name, p.pic, p.product_des, p.product_origins, pro.product_category_id 
                       FROM product p LEFT JOIN products pro ON p.SKU = pro.SKU 
                       left join units on p.unit = units.unit_id
                       WHERE pro.product_id = %s""", (product_id,)) 
        product = cursor.fetchall()

        return render_template('manager-product_details.html', location=session['location'][0], manager_info=manager_info, product=product, role=role, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))

    
@app.route('/manager/product-list/add-product', methods = ['GET', 'POST'])
def manager_add_new_product():
    role = session.get('role')
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories where product_category_id !="7" and product_category_id !="8"')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    if 'loggedin' in session and role == 2:
        if request.method == 'GET':
            if request.args.get('msg'):
                msg=request.args.get('msg')
            else:
                msg=''
            cursor.execute('SELECT max(product_id) FROM products')
            max_product_id = cursor.fetchone()
            new_product_id = max_product_id[0]+1 if max_product_id[0] is not None else 1
            depot_info = session['location']
            cursor.execute('SELECT depot_id FROM depots where location = %s;', (depot_info[0],))
            depot_id = cursor.fetchone()
            cursor.execute('SELECT * FROM units WHERE status = "Active";')
            list_unit = cursor.fetchall()
            return render_template('manager-add_new_product.html', msg=msg, list_unit=list_unit, new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, manager_info=manager_info, depot_id=depot_id[0], role=role, location=session['location'][0] )
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
                return redirect(url_for('manager_add_new_product', msg=msg))
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
                            return redirect(url_for('manager_add_new_product', new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, manager_info=manager_info, depot_id=depot_id[0], msg=msg, role=role, location=session['location'][0]))
                    else:
                        fixed_filepath = "app/static/assets/img/product_avatar.png"
            cursor.execute('INSERT INTO product VALUES (%s, %s, %s, %s, %s, %s);', (product_name, sku, unit, fixed_filepath, product_des, product_origins))
            cursor.execute('INSERT INTO union_skus VALUES (%s, "product");', (sku, ))
            cursor.execute('INSERT INTO products VALUES (%s, %s, %s, %s, %s, %s,"1");', (new_product_id, sku, product_price, product_category_id, promotion_type_id, depot_id))
            cursor.execute('INSERT INTO stock VALUES (%s, %s, %s);', (new_product_id, depot_id, stock_quantity,))
            msg = 'Product has been added successfully!'
            return redirect(url_for('manager_product_list', msg=msg))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))



@app.route('/manager/product-list/product/update', methods = ['GET', 'POST'])
def manager_edit_product():
    role = session.get('role')
    if request.args.get('msg'):
        msg=request.args.get('msg')
    else:
        msg=''
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories where product_category_id !="7" and product_category_id !="8"')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    if 'loggedin' in session and role == 2:
        if request.method == 'GET':
            depot_info = session.get('location')
            cursor.execute('select depot_id from depots where location = %s', (depot_info[0],))
            depot_id = cursor.fetchone()  # Fetch the result immediately and extract the value
            sku = request.args.get('sku')
            cursor.execute('SELECT * FROM product WHERE SKU = %s;', (sku,))
            product_info = cursor.fetchone()

            cursor.execute('SELECT * FROM units WHERE status = "Active";')
            list_unit = cursor.fetchall()

            cursor.execute('SELECT * FROM products WHERE SKU = %s and depot_id = %s;', (sku, depot_id[0]))
            products_info = cursor.fetchone()
            cursor.execute("SELECT * FROM stock WHERE product_id = %s;", (products_info[0],))
            stock_info = cursor.fetchone()
            return render_template('manager-update_product.html', msg=msg, list_unit=list_unit, stock_info=stock_info, product_id=products_info[0], product_categories=product_categories, promotion_type=promotion_type, manager_info=manager_info, depot_id=depot_id[0], role=role, location=session['location'][0], product_info=product_info, products_info=products_info)

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
            depot_id = request.form.get('depot_id')
            stock_quantity = request.form.get('stock_quantity')
            files = request.files.getlist('image1')

            cursor.execute('SELECT * FROM product WHERE SKU = %s;', (sku,))
            product_info = cursor.fetchone()

            cursor.execute('SELECT * FROM products WHERE SKU = %s and depot_id = %s;', (sku, depot_id[0]))
            products_info = cursor.fetchone()
            cursor.execute("SELECT * FROM stock WHERE product_id = %s;", (products_info[0],))
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
                            return redirect(url_for('manager_edit_product', sku=sku, product_id=product_id, product_categories=product_categories, promotion_type=promotion_type, manager_info=manager_info, depot_id=depot_id[0], msg=msg, role=role, location=session['location'][0], product_info=product_info, products_info=products_info, stock_info=stock_info))
                    else:
                        fixed_filepath = request.form.get('old_image')
            cursor.execute('UPDATE products SET SKU = %s, product_price = %s, product_category_id = %s, promotion_type_id = %s where product_id = %s;', (sku, product_price, product_category_id, promotion_type_id, product_id))
            cursor.execute('UPDATE product SET product_name = %s, unit = %s, pic = %s, product_des = %s, product_origins = %s WHERE SKU = %s;', (product_name, unit, fixed_filepath, product_des, product_origins, sku))
            cursor.execute('UPDATE stock SET quantity = %s WHERE product_id = %s;', (stock_quantity, product_id))
            msg = 'You have successfully updated the product.'
            return redirect(url_for('manager_product_details', msg=msg, product_id=product_id))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))


@app.route('/manager/product-list/delete')
def manager_product_delete():
    product_id = request.args.get('product_id')
    cursor = getCursor()
    cursor.execute('UPDATE products SET product_status="0" WHERE product_id = %s;', (product_id,))
    msg = 'Product has been removed successfully.'
    return redirect( url_for('manager_premade_box_list', msg=msg))


@app.route('/manager/premade-box-list', methods = ['GET', 'POST'])
def manager_premade_box_list():
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else: 
        msg = ''
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor = getCursor()
    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    # Fetch all distinct categories from the database
    cursor.execute('''SELECT DISTINCT product_category_name FROM product_categories where product_category_id !="7" and product_category_id !="8"''')
    categories = [row[0] for row in cursor.fetchall()]
    if 'loggedin' in session and role == 2:
        location_id = None  # Assign a default value
        if request.method == 'POST':
            # Fetch the user's depot_id
            manager_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
            location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

            searchinput = request.form.get('searchinput', '').strip()
            selected_category = request.form.get('category')
        else:
            # If it's a GET request, get search input, and selected category from query parameters
            searchinput = request.args.get('searchinput', '').strip()
            selected_category = request.args.get('category')

        if searchinput:
            manager_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
            location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
            # Perform search in the database based on the search input
            query ='''SELECT b.SKU, pc.product_category_name, b.box_name, pro.product_price, u.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM boxes b
                                    LEFT JOIN products pro ON b.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id LEFT JOIN units u ON u.unit_id = b.unit
                                WHERE product_status="1" AND pro.product_category_id != "8" AND  pro.depot_id = %s
                                AND (b.SKU LIKE %s OR pc.product_category_name LIKE %s OR b.box_name LIKE %s)
                                ORDER BY pro.product_id DESC'''
            params = (location_id, f'%{searchinput}%', f'%{searchinput}%', f'%{searchinput}%')
            if selected_category and selected_category != 'all':
                query += " AND pc.product_category_name = %s"
                params += (selected_category,)
            cursor.execute(query, params)
            products = cursor.fetchall()

        # If no search input is provided, fetch all products
        else:
            if selected_category:
                # Fetch the user's depot_id
                manager_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
                location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
                cursor.execute('''SELECT b.SKU, pc.product_category_name, b.box_name, pro.product_price, u.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM boxes b
                                    LEFT JOIN products pro ON b.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id LEFT JOIN units u ON u.unit_id = b.unit
                                    WHERE product_status="1" AND pro.product_category_id != "8" AND pro.depot_id = %s AND pc.product_category_name = %s
                                    ORDER BY pro.product_id DESC''', (location_id, selected_category,))
            else:
                # Fetch the user's depot_id for GET requests without form submission
                manager_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
                location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

                # Fetch all products
                cursor.execute('''SELECT b.SKU, pc.product_category_name, b.box_name, pro.product_price, u.unit_name, stock.quantity, d.location, pro.product_id
                                    FROM boxes b
                                    LEFT JOIN products pro ON b.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id LEFT JOIN units u ON u.unit_id = b.unit
                                    WHERE product_status="1" AND pro.product_category_id != "8" AND pro.depot_id = %s
                                    ORDER BY pro.product_id DESC''', (location_id,))
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

        # Render template with the list of products
        return render_template('manager-premade_box_list.html', location=session['location'][0], products=products, manager_info=manager_info, role=role, categories=categories, searchinput=searchinput, selected_category=selected_category, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))
    
@app.route('/manager/premade-box-list/premade-box', methods=["GET","POST"])
def manager_premade_box_details():
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor=getCursor()
    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    if 'loggedin' in session and role == 2: 
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

        return render_template('manager-premade_box_details.html', location=session['location'][0], manager_info=manager_info, product=product, role=role, msg=msg, box_items=box_items)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))

    


@app.route('/manager/premade-box-list/premade-box/update', methods = ['GET', 'POST'])
def manager_edit_premade_box():
    role = session.get('role')
    msg=''
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories where product_category_id !="7" and product_category_id !="8"')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    cursor.execute("""SELECT pro.product_id, p.product_name, u.unit_name FROM product AS p JOIN products pro ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit""")
    pro_list = cursor.fetchall()

  

  

    if 'loggedin' in session and role == 2:
        if request.method == 'GET':
            depot_info = session.get('location')
            cursor.execute('select depot_id from depots where location = %s', (depot_info[0],))
            depot_id = cursor.fetchone()  # Fetch the result immediately and extract the value

            cursor.execute('SELECT * FROM depots where location = %s;', (depot_info[0],))
            depot_info = cursor.fetchall()

            
    
            product_id = request.args.get('product_id')
         

            cursor.execute('SELECT boxes.*, products.*, units.unit_name from products left join boxes on boxes.SKU=products.SKU LEFT JOIN units ON units.unit_id = boxes.unit  where products.product_id = %s;', (product_id,))
            product_info = cursor.fetchone()

            cursor.execute('SELECT * FROM units WHERE status = "Active";')
            list_unit = cursor.fetchall()

            cursor.execute('SELECT * FROM products WHERE product_id = %s and depot_id = %s;', (product_id, depot_id[0]))
            products_info = cursor.fetchone()

            cursor.execute("SELECT * FROM stock WHERE product_id = %s;", (products_info[0],))
            stock_info = cursor.fetchone()
            cursor.execute("""SELECT b.* FROM box_items AS b JOIN products AS pro ON pro.SKU= b.SKU WHERE pro.product_id = %s""",(product_id,))
            box_items = cursor.fetchall()
            cursor.execute("""SELECT pro.product_id, p.product_name, u.unit_name FROM product AS p JOIN products pro ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit""")
            pro_list = cursor.fetchall()

            pro_duct_id = request.args.get('product_id')

            cursor.execute("""SELECT b.* FROM box_items AS b JOIN products AS pro ON pro.SKU= b.SKU WHERE pro.product_id = %s""",(pro_duct_id,))
            box_items = cursor.fetchall()

            return render_template('manager-update_premade_box.html', list_unit=list_unit, stock_info=stock_info, product_id=products_info[0], product_categories=product_categories, promotion_type=promotion_type, manager_info=manager_info, depot_id=depot_id[0], role=role, location=session['location'][0], product_info=product_info, products_info=products_info, depot_info=depot_info,box_items=box_items,  pro_list= pro_list)

        else:

            depot_info = session.get('location')
            cursor.execute('select depot_id from depots where location = %s', (depot_info[0],))
            depot_id = cursor.fetchone()
            sku = request.form.get('sku')
            product_id = request.form.get('product_id')
            product_category_id = request.form.get('product_category_id')
            product_name = request.form.get('product_name')
            unit = request.form.get('unit')
            product_des = request.form.get('product_des')
            product_price = request.form.get('product_price')
            promotion_type_id = request.form.get('promotion_type_id')
            product_origins = request.form.get('product_origins')
            depot_id = request.form.get('depot_id')
            stock_quantity = request.form.get('stock_quantity')
            files = request.files.getlist('image1')

            pro_ids = request.form.getlist('pro_id[]')
            quantities = request.form.getlist('quantity[]')

            cursor.execute('SELECT * FROM boxes WHERE SKU = %s;', (sku,))
            product_info = cursor.fetchone()

            cursor.execute('SELECT * FROM products WHERE SKU = %s and depot_id = %s;', (sku, depot_id[0]))
            products_info = cursor.fetchone()
            cursor.execute("SELECT * FROM stock WHERE product_id = %s;", (products_info[0],))
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
                            return render_template('manager-update_premade_box.html', product_id=product_id, product_categories=product_categories, promotion_type=promotion_type, manager_info=manager_info, depot_id=depot_id[0], msg=msg, role=role, location=session['location'][0], product_info=product_info, products_info=products_info, stock_info=stock_info, depot_info=depot_info,pro_list= pro_list)
                    else:
                        fixed_filepath = request.form.get('old_image')
            cursor.execute('UPDATE products SET SKU = %s, product_price = %s, product_category_id = 7, promotion_type_id = %s where product_id = %s;', (sku, product_price, promotion_type_id, product_id))
            cursor.execute('UPDATE product SET product_name = %s, unit = %s, pic = %s, product_des = %s, product_origins = %s WHERE SKU = %s;', (product_name, unit, fixed_filepath, product_des, product_origins, sku))

            cursor.execute("""SELECT b.* FROM box_items AS b INNER JOIN products AS pro ON pro.SKU= b.SKU WHERE b.SKU= %s""",(sku,))
            box_items = cursor.fetchall()

           
            for item, pro_id, quantity in zip(box_items,pro_ids, quantities):
                cursor.execute('UPDATE box_items SET product_id = %s, quantity= %s WHERE item_id = %s;', (pro_id, quantity,item[0]))


            cursor.execute('UPDATE stock SET quantity = %s WHERE product_id = %s;', (stock_quantity, product_id))
            msg = 'You have successfully updated the product.'
            return redirect(url_for('manager_premade_box_details', msg=msg, product_id=product_id, depot_info=depot_info,depot_id=depot_id,box_items=box_items, pro_list= pro_list,product_info=product_info))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))
    
@app.route('/manager/premade-box-list/delete')
def manager_premade_box_delete():
    product_id = request.args.get('product_id')
    cursor = getCursor()
    cursor.execute('UPDATE products SET product_status="0" WHERE product_id = %s;', (product_id,))
    msg = 'Premadebox has been removed successfully.'
    return redirect( url_for('manager_premade_box_list', msg=msg))

@app.route('/manager/discontinued-products', methods=['GET', 'POST'])
def manager_discontinued_products():
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else: 
        msg = ''
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor = getCursor()
    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    # Fetch all distinct categories from the database
    cursor.execute('''SELECT DISTINCT product_category_name FROM product_categories''')
    categories = [row[0] for row in cursor.fetchall()]
    if 'loggedin' in session and role == 2:
        location_id = None  # Assign a default value
        if request.method == 'POST':
            # Fetch the user's depot_id
            manager_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
            location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

            searchinput = request.form.get('searchinput', '').strip()
            selected_category = request.form.get('category')
        else:
            # If it's a GET request, get search input, and selected category from query parameters
            searchinput = request.args.get('searchinput', '').strip()
            selected_category = request.args.get('category')

        if searchinput:
            manager_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
            location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
            # Perform search in the database based on the search input
            query ='''SELECT pro.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id, b.box_name, us.unit_name, g.giftcard_name, pro.product_category_id
                                    FROM products pro 
                                    LEFT JOIN product p ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id LEFT JOIN boxes b ON b.SKU = pro.SKU LEFT JOIN giftcards g ON g.SKU = pro.SKU LEFT JOIN units us ON b.unit = us.unit_id
                                WHERE product_status="0" AND  pro.depot_id = %s
                                AND (p.SKU LIKE %s OR pc.product_category_name LIKE %s OR p.product_name LIKE %s)
                                ORDER BY pro.product_id DESC'''
            params = (location_id, f'%{searchinput}%', f'%{searchinput}%', f'%{searchinput}%')
            if selected_category and selected_category != 'all':
                query += " AND pc.product_category_name = %s"
                params += (selected_category,)
            cursor.execute(query, params)
            products = cursor.fetchall()

        # If no search input is provided, fetch all products
        else:
            if selected_category:
                # Fetch the user's depot_id
                manager_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
                location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
                cursor.execute('''SELECT pro.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id, b.box_name, us.unit_name, g.giftcard_name, pro.product_category_id
                                    FROM products pro 
                                    LEFT JOIN product p ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id LEFT JOIN boxes b ON b.SKU = pro.SKU LEFT JOIN giftcards g ON g.SKU = pro.SKU LEFT JOIN units us ON b.unit = us.unit_id
                                    WHERE product_status="0" AND pro.depot_id = %s AND pc.product_category_name = %s
                                    ORDER BY pro.product_id DESC''', (location_id, selected_category,))
            else:
                # Fetch the user's depot_id for GET requests without form submission
                manager_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
                location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

                # Fetch all products
                cursor.execute('''SELECT pro.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, d.location, pro.product_id, b.box_name, us.unit_name, g.giftcard_name, pro.product_category_id
                                    FROM products pro 
                                    LEFT JOIN product p ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                                    LEFT JOIN depots d on d.depot_id = pro.depot_id
                                    Left join units on p.unit = units.unit_id LEFT JOIN boxes b ON b.SKU = pro.SKU LEFT JOIN giftcards g ON g.SKU = pro.SKU LEFT JOIN units us ON b.unit = us.unit_id
                                    WHERE product_status="0" AND pro.depot_id = %s
                                    ORDER BY pro.product_id DESC''', (location_id,))
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

        # Render template with the list of products
        return render_template('manager-discontinued_products.html', location=session['location'][0], products=products, manager_info=manager_info, role=role, categories=categories, searchinput=searchinput, selected_category=selected_category, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))


@app.route('/manager/restore-product')
def manager_restore_product():
    product_id = request.args.get('product_id')
    cursor = getCursor()
    cursor.execute('UPDATE products SET product_status="1" WHERE product_id = %s;', (product_id,))
    msg = 'Product has been restored successfully.'
    return redirect( url_for('manager_discontinued_products', msg=msg))

@app.route('/manager/restore-premade-box', methods=['POST'])
def manager_restore_premade_box():
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
    return redirect( url_for('manager_discontinued_products', msg=msg))


@app.route('/manager/get-products')
def manager_get_products():
    depot_id = request.args.get('depot_id')
    
    cursor = getCursor()
    
    
    cursor.execute('SELECT pro.product_id, p.product_name, u.unit_name FROM products AS pro JOIN product p ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit WHERE depot_id = %s', (depot_id,))
    products = cursor.fetchall()
    



    products_list = [{'id': product[0], 'name': f'{product[1]} ({product[2]})'} for product in products]

    print(products_list)

    return ({'products': products_list})

@app.route('/manager/get-product-quantity')
def manager_get_product_quantity():

    product_id = request.args.get('product_id')
   
    
    cursor = getCursor()
    
    cursor.execute('SELECT quantity FROM stock WHERE product_id = %s', (product_id,))
    stock = cursor.fetchone()
    print(product_id, stock)
    
    
    if stock:
        return {'quantity': stock[0]}
    else:
        return {'quantity': 0}

@app.route('/manager/products/add-premade-box', methods = ['GET', 'POST'])
def manager_add_premade_box():
    role = session.get('role')
    cursor = getCursor()
    user_id = session['user_id']
    
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories where product_category_id !="8"')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    if 'loggedin' in session and role == 2:
        if request.method == 'GET':
            if request.args.get('msg'):
                msg=request.args.get('msg')
            else:
                msg=''
            cursor.execute('SELECT max(product_id) FROM products')
            max_product_id = cursor.fetchone()
            new_product_id = max_product_id[0]+1 if max_product_id[0] is not None else 1
            depot_info = session['location']
            cursor.execute('SELECT depot_id FROM depots where location = %s;', (depot_info[0],))
            depot_id = cursor.fetchone()
            cursor.execute('SELECT * FROM units WHERE status = "Active";')
            list_unit = cursor.fetchall()

            cursor.execute('SELECT * FROM depots where location = %s;', (depot_info[0],))
            depot_info = cursor.fetchall()

            cursor.execute("""SELECT pro.product_id, p.product_name, u.unit_name FROM product AS p JOIN products pro ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit WHERE pro.depot_id = %s""", (depot_id[0],))
            pro_list = cursor.fetchall()


            return render_template('manager-add_premade_box.html', msg=msg, list_unit=list_unit, new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, manager_info=manager_info, depot_id=depot_id[0], role=role, location=session['location'][0], depot_info=depot_info,pro_list=pro_list)
        else:
            depot_info = session['location']
            cursor.execute('SELECT depot_id FROM depots where location = %s;', (depot_info[0],))
            depot_id = cursor.fetchone()

            cursor.execute('SELECT * FROM depots where location = %s;', (depot_info[0],))
            depot_info = cursor.fetchall()
            
            cursor.execute("""SELECT pro.product_id, p.product_name, u.unit_name FROM product AS p JOIN products pro ON p.SKU = pro.SKU JOIN units u ON u.unit_id = p.unit WHERE pro.depot_id = %s""", (depot_id[0],))
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
            stock_quantity = request.form.get('stock_quantity')
            files = request.files.getlist('image1')
            pro_ids = request.form.getlist('pro_id[]')
            quantities = request.form.getlist('quantity[]')

            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')

            # Convert start and end times to datetime objects
            start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')

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
                depot_id = cursor.fetchone()
                
                return redirect(url_for('manager_add_premade_box', msg=msg, depot_info=depot_info,depot_id=depot_id[0],pro_list=pro_list))
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
                            return redirect(url_for('manager_add_premade_box', new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, manager_info=manager_info, depot_id=depot_id[0], msg=msg, role=role, location=session['location'][0]), depot_info=depot_info,pro_list=pro_list)
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

            msg = 'Product has been added successfully!'
            return redirect(url_for('manager_premade_box_list', msg=msg, depot_info=depot_info, pro_list=pro_list))
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


def set_product_in_stock(product_id, in_stock):
    cursor=getCursor()

    cursor.execute("UPDATE products SET product_status = %s WHERE product_id = %s", (in_stock, product_id))
    cursor.close()


def schedule_product_availability(product_id, start_time, end_time):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: set_product_in_stock(product_id, 1), 'date', run_date=start_time)
    scheduler.add_job(lambda: set_product_in_stock(product_id, 0), 'date', run_date=end_time)
    scheduler.start()


@app.route('/manager/return-request', methods=['GET', 'POST'])
def return_request():
    cursor = getCursor()
    role = session.get('role')
    location = session['location']
    cursor.execute('SELECT depot_id FROM depots WHERE depots.location = %s;', (location[0],))
    location_id = cursor.fetchone()

    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                      FROM roles 
                      INNER JOIN users ON roles.role_id = users.role_id 
                      INNER JOIN staff ON staff.user_id = users.user_id 
                      WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()

    if 'loggedin' in session and role == 2:
        if request.method == 'GET':
            msg = request.args.get('msg', '')

            status_filter = request.args.get('status_filter')

            if status_filter:
                cursor.execute('''
                    SELECT return_authorization.*
                    FROM return_authorization
                    LEFT JOIN orders ON return_authorization.order_id = orders.order_id
                    LEFT JOIN users ON orders.user_id = users.user_id
                    LEFT JOIN customers ON users.user_id = customers.user_id
                    LEFT JOIN accounts ON users.user_id = accounts.user_id
                    WHERE (customers.city = %s OR accounts.city = %s)
                    AND return_authorization.return_status = %s
                ''', (location_id[0], location_id[0], status_filter))
            else:
                cursor.execute('''
                    SELECT return_authorization.*
                    FROM return_authorization
                    LEFT JOIN orders ON return_authorization.order_id = orders.order_id
                    LEFT JOIN users ON orders.user_id = users.user_id
                    LEFT JOIN customers ON users.user_id = customers.user_id
                    LEFT JOIN accounts ON users.user_id = accounts.user_id
                    WHERE customers.city = %s OR accounts.city = %s
                ''', (location_id[0], location_id[0]))

            return_list = cursor.fetchall()

            return render_template('manager-return_request.html', msg=msg, role=role, manager_info=manager_info, return_list=return_list, location=session['location'][0])

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
                total_value += product_value

            return render_template('manager-request_detail.html', total_value=total_value, role=role, manager_info=manager_info, return_list=return_list, location=session['location'][0])
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


    
@app.route('/manager/return-approve', methods=['GET', 'POST'])
def return_approve():
    cursor = getCursor()
    form_id = request.form.get('form_id')
    return_status = request.form.get('status')
    subtotal = request.form.get('subtotal')
    subtotal_value = float(subtotal)
    role = session.get('role')
    if 'loggedin' in session and role == 2:

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
                    return redirect(url_for('return_request', msg=msg))

        msg = 'Refund request processed, status updated.'
        return redirect(url_for('return_request', msg=msg))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


@app.route('/manager/orderlist',methods=['get','post'])
def manager_orderlist():
    role = session.get('role')
    msg=''
    order_status_all=[]
    cursor = getCursor()
    todaydate = datetime.now()

    
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    


    if 'loggedin' in session and role == 2:
        # get all order status types
        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''
    # check if there's filter info needed
        # if request.args.get('order_status_all'):
        #     order_status_all = request.args.get('order_status_all')

        if request.method=='GET':                
            cursor.execute('select * from order_status_types')
            order_status_types = cursor.fetchall()

                # get manager's depot_id
            cursor.execute('select depot_id from staff where user_id=%s', (user_id,))
            depot = cursor.fetchone()      

            # get packing and delivery personnel list 

            cursor.execute('select staff_id, given_name from staff where depot_id = %s and responsibility_id=2',(depot[0],))
            packing_person_all= cursor.fetchall()

            cursor.execute('select staff_id, given_name from staff where depot_id = %s and responsibility_id=3',(depot[0],))
            delivery_person_all= cursor.fetchall()

            # get all order number of the depot

            cursor.execute("""
                                select o.*, p.status, s.depot_id from orders as o
                                join payments as p on o.payment_id = p.payment_id
                                join shippments as s on o.shippment_id=s.shippment_id
                                where p.status='Completed' and depot_id = %s
                                """,(depot[0],))
            order_number_all = cursor.fetchall()

            # if order_status_all:
            #     return render_template('manager-order_list.html',msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=order_status_all)

                # return render_template('test.html',order_status_all=order_status_all)
            # else:
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
            order_status_all = [['' for x in range(5)] for y in range(h)] 

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
            for order_number in order_number_all:                
                order_status_all[i].insert(0,order_number[0])
                        
                        ## fill in 'begin' 
                for status in max_status:

                    if status[0] == order_number[0]:

                                # check if there's no assignment 
                    
                        order_status_all[i].insert(1,'Begin')              


                        #insert name into the list
                for order_process in order_process_all:
                    if order_process[0] == order_number[0]:
                        for staff_name in staff_name_all:
                            if order_process[2] == staff_name[0]:
                                order_status_all[i].insert(1,order_process[2])


                        #increase i         
                i = i +1

                    
            return render_template('manager-order_list.html', location=session['location'][0],msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=order_status_all)
            
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

            cursor.execute("""
                                select o.*, p.status, s.depot_id from orders as o
                                join payments as p on o.payment_id = p.payment_id
                                join shippments as s on o.shippment_id=s.shippment_id
                                where p.status='Completed' and depot_id = %s
                                """,(depot[0],))
            order_number_all = cursor.fetchall()

            # change the data to the form (id, packing,ready,out,delivered)
            # fill in 'begin' and 'to be started' when the resp_id is different

            # define a array with 5 items in a row without 'bgin' 'to start'
            order_status_all=[]
            h = len(order_number_all)
            order_status_all = [['' for x in range(5)] for y in range(h)] 

            #get different resp list

        # get packing and delivery personnel list 

            cursor.execute('select staff_id, given_name from staff where depot_id = %s and responsibility_id=2',(depot[0],))
            packing_person_all= cursor.fetchall()

            cursor.execute('select staff_id, given_name from staff where depot_id = %s and responsibility_id=3',(depot[0],))
            delivery_person_all= cursor.fetchall()
            
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
            for order_number in order_number_all:                
                order_status_all[i].insert(0,order_number[0])
                
                ## fill in 'begin' and 'to be started' when the resp_id is different
                for status in max_status:

                    if status[0] == order_number[0]:

                        # check if there's no assignment 
            
                        order_status_all[i].insert(1,'Begin')              


                #insert name into the list
                for order_process in order_process_all:
                    if order_process[0] == order_number[0]:
                        for staff_name in staff_name_all:
                            if order_process[2] == staff_name[0]:
                                order_status_all[i].insert(1,order_process[2])


                #increase i         
                i = i +1
            # return render_template('test.html',order_status_all=order_status_all)
            # return render_template('manager-order_list.html',msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=order_status_all)
            #  # order_status_all ends
            # #filter function script
            selected_status_id = request.form.get('status_id')
            # #create another given name list for the loop
            staff_name_all1 = staff_name_all
            #test OK
            # return render_template('test.html',order_status_all=order_status_all)

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
                            if status[4] == staff[0]:                        
                                status_filter_result.append(status)
                    #    test OK 
                    # return render_template('test.html',status_filter_result=status_filter_result)
                    # return render_template('test.html',order_status_all=order_status_all)
                    #return redirect(url_for('manager_orderlist',order_status_all=status_filter_result))
                    #nok
                    return render_template('manager-order_list.html',msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=status_filter_result)


                elif selected_status_id == 'On delivery vehicle' :
                    # check if index position has staff name and index+1 doesn't have staff name
                    for status in order_status_all:
                        # status_filter_result.append([status])
                        for staff in staff_name_all:
                            if status[3] == staff[0] and status[4] == 'Begin':
                                #test 
                                # return render_template('test.html',status_filter_result=status[int(selected_status_id)])
                                status_filter_result.append(status)
                        
                    # # test
                    # return render_template('test.html',status_filter_result=status_filter_result)

                    return render_template('manager-order_list.html',msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=status_filter_result)
                elif selected_status_id == 'Ready for delivery':
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

                    return render_template('manager-order_list.html',msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=status_filter_result)
                elif selected_status_id == 'Preparing':
                    # check if index position has staff name and index+1 doesn't have staff name
                    for status in order_status_all:
                        # status_filter_result.append([status])
                        for staff in staff_name_all:
                            if status[1] == staff[0] and status[2] == 'Begin':
                                #test 
                                # return render_template('test.html',status_filter_result=status[int(selected_status_id)])
                                status_filter_result.append(status)
                        
                    # # test
                    # return render_template('test.html',status_filter_result=status_filter_result)

                    return render_template('manager-order_list.html',msg=msg,order_status_types=order_status_types,packing_person_all=packing_person_all,delivery_person_all=delivery_person_all,order_number_all=order_number_all,manager_info=manager_info,order_status_all=status_filter_result)

                    # return redirect(url_for('manager_orderlist',order_status_all=status_filter_result))
            else:                        
                staffid= request.form.get('staffid')
                orderid= request.form.get('orderid')
                rowid= request.form.get('rowid')

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
                return redirect(url_for('manager_orderlist',msg=msg))
        
@app.route('/manager/order_incoming', methods=['GET', 'POST'])
def manager_order_incoming():
    msg = request.args.get('msg', '')
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 2:
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()
        
        cursor.execute('''SELECT depot_id FROM staff WHERE user_id = %s''', (user_id,))
        depot_info = cursor.fetchone()
        depot_id = depot_info[0]

        searchinput = request.args.get('searchinput', '').strip()
        selected_order_status = request.args.get('order_status')
        order_date_str = request.args.get('order_date')

        order_date = None
        if order_date_str:
            order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()

        sort_by = request.args.get('sort_by', 'order_date')
        reverse = request.args.get('reverse', 'False') == 'True'

        sort_column_map = {
            'order_date': 'order_date',
            'order_id': 'order_id',
            'full_name': 'full_name',
            'delivery_status': 'delivery_status',
        }
        sort_column = sort_column_map.get(sort_by, 'order_date')

        query = '''
            SELECT * FROM (
                SELECT 
                    orders.order_id,
                    CONCAT(customers.given_name, " ", customers.family_name) AS full_name,
                    customers.customer_address,
                    customers.phone_number,
                    customers.email,
                    COALESCE(ost.order_status_type_name, 'Pending') AS delivery_status,
                    orders.order_date,
                    GROUP_CONCAT(COALESCE(boxes.box_name, product.product_name) SEPARATOR ', ') AS product_details
                FROM 
                    orders 
                    LEFT JOIN order_lines ON orders.order_id = order_lines.order_id
                    LEFT JOIN products ON order_lines.product_id = products.product_id
                    LEFT JOIN product ON products.SKU = product.SKU
                    LEFT JOIN boxes ON products.SKU = boxes.SKU
                    LEFT JOIN customers ON customers.user_id = orders.user_id
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
                WHERE customers.city = %s
                GROUP BY orders.order_id, customers.given_name, customers.family_name, customers.customer_address, customers.phone_number, customers.email, ost.order_status_type_name, orders.order_date
                UNION ALL
                SELECT 
                    orders.order_id,
                    accounts.account_name AS full_name,
                    accounts.account_address AS customer_address,
                    accounts.phone_number,
                    accounts.email,
                    COALESCE(ost.order_status_type_name, 'Pending') AS delivery_status,
                    orders.order_date,
                    GROUP_CONCAT(COALESCE(boxes.box_name, product.product_name) SEPARATOR ', ') AS product_details
                FROM 
                    orders 
                    LEFT JOIN order_lines ON orders.order_id = order_lines.order_id
                    LEFT JOIN products ON order_lines.product_id = products.product_id
                    LEFT JOIN product ON products.SKU = product.SKU
                    LEFT JOIN boxes ON products.SKU = boxes.SKU
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
                WHERE accounts.city = %s
                GROUP BY orders.order_id, accounts.account_name, accounts.account_address, accounts.phone_number, accounts.email, ost.order_status_type_name, orders.order_date
            ) AS combined_orders
            WHERE 1=1
        '''

        params = [depot_id, depot_id]

        if searchinput:
            query += " AND (full_name LIKE %s)"
            params.append(f'%{searchinput}%')

        if selected_order_status:
            query += " AND COALESCE(delivery_status, 'Pending') = %s"
            params.append(selected_order_status)

        if order_date:
            query += " AND DATE(order_date) = %s"
            params.append(order_date)

        query += f" ORDER BY {sort_column} {'DESC' if reverse else 'ASC'}"
        
        cursor.execute(query, params)
        orders = cursor.fetchall()

        cursor.execute('''SELECT DISTINCT order_status_type_name FROM order_status_types
                          UNION SELECT 'Pending' AS order_status_type_name''')
        order_status = cursor.fetchall()

        return render_template('manager-order_incoming.html', manager_info=manager_info, location=session['location'][0], orders=orders, order_status=order_status, searchinput=searchinput, selected_order_status=selected_order_status, sort_by=sort_by, reverse=reverse, msg=msg, order_date=order_date_str)
    else:
        return redirect(url_for('logout'))

@app.route('/manager/order_incoming_detail/<order_id>')
def manager_order_incoming_detail(order_id):
    msg = request.args.get('msg', '')
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 2:
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()

        cursor.execute('''SELECT depot_id FROM staff WHERE user_id = %s''', (user_id,))
        depot_info = cursor.fetchone()
        depot_id = depot_info[0]

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
                        orders.order_id = %s AND (customers.city = %s OR accounts.city = %s)
                       """, (order_id, depot_id, depot_id))
        theorder = cursor.fetchone()

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
        order_lines = cursor.fetchall()

        # Define the order statuses
        order_statuses = [
            {"id": 0, "name": "Pending"},
            {"id": 1, "name": "Preparing"},
            {"id": 2, "name": "Ready for delivery"},
            {"id": 3, "name": "On delivery vehicle"},
            {"id": 4, "name": "Delivered"}
        ]

        return render_template('manager-order_incoming_detail.html', order_lines=order_lines, role=role, manager_info=manager_info, location=session['location'][0], theorder=theorder, msg=msg, order_statuses=order_statuses)       
    else: 
        return redirect(url_for('logout'))

@app.route('/manager/account-holder-list/profile/manage-credit-limit', methods=['GET', 'POST'])
def manager_manage_credit_limit():
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Check if the user is logged in and has the manager role
    if 'loggedin' in session and role == 2:
        # Get a cursor object to interact with the database
        cursor = getCursor()
        # Fetch manager information for use in the template
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()

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
                return render_template('manager-manage_credit_limit.html', account_info=account_info, manager_info=manager_info, role=role, location=session['location'][0], profile=profile)
            else:
                return redirect(url_for('manager_account_list'))

        elif request.method == 'POST':
            new_credit_limit = request.form['new_credit_limit']
            account_holder_id = request.form['account_holder_id']
            if account_holder_id and new_credit_limit:
                cursor.execute("""UPDATE accounts SET credit_limit_monthly = %s WHERE account_id = %s""", (new_credit_limit, account_holder_id))
                msg = "Credit limit has been successfully updated!"
                return redirect(url_for('manager_account_profile', account_holder_id=account_holder_id, msg=msg))
            else:
                error_msg = "Failed to update credit limit. Please ensure all fields are filled out."
                cursor.execute("""SELECT * FROM accounts WHERE account_id = %s""", (account_holder_id,))
                account_info = cursor.fetchone()
                return render_template('manager-manage_credit_limit.html', account_info=account_info, manager_info=manager_info, role=role, location=session['location'][0], error_msg=error_msg)

    else:
        return redirect(url_for('logout'))



    
@app.route('/manager/application-list')
def manager_application_list():

    role = session.get('role')
    msg=''
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()

    cursor.execute('''SELECT depot_id FROM staff WHERE user_id = %s''', (user_id,))
    depot_info = cursor.fetchone()

    if 'loggedin' in session and role == 2:
        if request.method == 'GET':
            cursor.execute('select a.*,accounts.account_name from applications as a join accounts on a.applied_by = accounts.user_id where accounts.city = %s',(depot_info[0],))
            applicationlist = cursor.fetchall()

            return render_template('manager-application_list.html',msg=msg,applicationlist=applicationlist, manager_info=manager_info)
 
        # else:
            # search and filter function


@app.route('/manager/application/<application_id1>', methods=["GET","POST"])
def manager_application_details(application_id1):
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor=getCursor()
    # Fetch admin information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()
    if 'loggedin' in session and role == 2: 
        cursor=getCursor()

        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''
       
        if request.method == 'GET':


            cursor.execute("""select a.*,accounts.account_name from applications as a join accounts on a.applied_by = accounts.user_id
                        WHERE application_id = %s""", (application_id1,)) 
            application = cursor.fetchone()

            return render_template('manager-application_details.html', manager_info=manager_info, application=application, role=role, msg=msg)
        else:
            cursor.execute('UPDATE applications SET status="Approved" WHERE application_id = %s;', (application_id1,))
            cursor.execute('selsect * from applications where application_id=%s',(application_id1,))
            application_info = cursor.fetchone()
            cursor.execute('update accounts set credit_limit_monthly=%s where user_id=%s',(application_info[1],application_info[3],))
            msg = 'Application has been approved.'
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))
    

@app.route('/manager/application/reject/<application_id1>')
def manager_application_reject(application_id1):
    cursor = getCursor()
    cursor.execute('UPDATE application SET status="Declined" WHERE application_id = %s;', (application_id1,))
    msg = 'Application has been declined.'
    return redirect( url_for('manager_application_list', msg=msg))


#     else:
#         cursor.execute('INSERT INTO coupons VALUES (%s, %s, %s, %s, %s, %s,%s,%s);', (new_coupon_id, couponcode, reduce_value,thres_price,start_time, end_time, depot_id,user_id))
#         msg = 'Coupon has been successfully replicated between depots!'
#         return redirect(url_for('admin_coupon_list', msg=msg))

@app.route('/manager/credit_limit_pending_requests', methods=['GET'])
def manager_credit_limit_pending_requests():
    role = session.get('role')
    user_id = session.get('user_id')
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg= ''
    if 'loggedin' in session and role == 2:
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
        manager_info = cursor.fetchone()

        status_filter = request.args.get('status_filter')
        
        if status_filter:
            cursor.execute('''SELECT applications.*, accounts.account_name, accounts.credit_limit_monthly AS current_limit
                              FROM applications
                              INNER JOIN accounts ON applications.applied_by = accounts.user_id 
                              WHERE applications.status = %s AND accounts.city = (
                                SELECT depot_id FROM staff WHERE user_id = %s
                              )''', (status_filter, user_id))
        else:
            cursor.execute('''SELECT applications.*, accounts.account_name, accounts.credit_limit_monthly AS current_limit 
                              FROM applications
                              INNER JOIN accounts ON applications.applied_by = accounts.user_id 
                              WHERE accounts.city = (
                                SELECT depot_id FROM staff WHERE user_id = %s
                              )''', (user_id,))
        pending_requests = cursor.fetchall()

        return render_template('manager_credit_limit_pending_requests.html', msg=msg,location=session['location'][0], manager_info=manager_info, pending_requests=pending_requests, profile=profile, user_id=user_id)
    else:
        return redirect(url_for('logout'))

@app.route('/manager/credit_limit_request_detail_<int:application_id>', methods=['GET', 'POST'])
def manager_credit_limit_request_detail(application_id):
    cursor = getCursor()
    user_id = session['user_id']
    role = session.get('role')

    if 'loggedin' in session and role == 2:
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles 
                          INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()

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
                    return redirect(url_for('manager_credit_limit_pending_requests', msg=msg))
                elif action == 'decline':
                    decline_reason = request.form['decline_reason']
                    cursor.execute('''UPDATE applications SET status = 'Declined', decline_reason = %s WHERE application_id = %s''', (decline_reason, application_id))
                    msg = 'You have declined the application!'
                    return redirect(url_for('manager_credit_limit_pending_requests', msg=msg))
            return render_template('manager_credit_limit_request_detail.html', location=session['location'][0], manager_info=manager_info, request_detail=request_detail)
        else:
            return render_template('manager_credit_limit_request_detail.html', location=session['location'][0], manager_info=manager_info, request_detail=None)
    else:
        return redirect(url_for('logout'))

@app.route('/manager/news', methods=['GET', 'POST'])
def manager_news():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()

    depot_name = session['location']

    cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (depot_name[0],))
    depot_id = cursor.fetchone()

    if 'loggedin' in session and role == 2:
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
                              WHERE depot_id IN (0, %s) AND title LIKE %s
                              ORDER BY publish_date {}, news_id {}'''.format(order or 'DESC', order or 'DESC'), (depot_id[0],'%' + searchinput + '%',))
            news_list = cursor.fetchall()
        else:
            # If no search input is provided, fetch all news
            cursor.execute('SELECT * FROM news WHERE depot_id IN (0, %s) ORDER BY publish_date {}, news_id {}'.format(order or 'DESC', order or 'DESC'), (depot_id[0],))
            news_list = cursor.fetchall()

        # Render template with the list of news
        return render_template('manager-news.html', manager_info=manager_info, role=role, news_list=news_list, searchinput=searchinput, order=order, location=session['location'][0], msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


@app.route('/manager/news/<int:news_id>', methods=['GET'])
def manager_news_details(news_id):
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()

    if 'loggedin' in session and role == 2:
        cursor.execute('''SELECT news.*, CONCAT(staff.given_name, ' ', staff.family_name) AS full_name
                   FROM news 
                   INNER JOIN staff ON news.created_by = staff.user_id
                   WHERE news_id = %s''', (news_id,))
        news_item = cursor.fetchone()

        if news_item:
            return render_template('manager-news_details.html', news_item=news_item, manager_info=manager_info, role=role, location=session['location'][0])
        else:
            return redirect(url_for('error', msg='News not found'))   
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))  


@app.route('/manager/news/publish', methods=['GET', 'POST'])
def manager_publish_news():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    # Fetch manager information for use of manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                      FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                      INNER JOIN staff ON staff.user_id = users.user_id 
                      WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()

    depot_name = session['location']
    
    cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (depot_name[0],))
    depot_id = cursor.fetchone()

    if 'loggedin' in session and role == 2:
        if request.method == 'POST':
            title = request.form['title'].strip()
            content = request.form['content'].strip()
            pic = request.files.get('pic')
            msg = ''
            
            # Validate inputs
            if not title or not content:
                msg = 'Title and content are required!'
                return render_template('manager-news_publish.html', msg=msg, manager_info=manager_info, role=role, location=session['location'][0])
            
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
                    return render_template('manager-news_publish.html', msg=msg, manager_info=manager_info, role=role, location=session['location'][0])
            else:
                fixed_filepath = "app/static/assets/img/default_news.jpg"  # Default image if none uploaded 
            
            # Insert the news into the database
            publish_date = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''INSERT INTO news (title, content, pic, publish_date, created_by, depot_id)
                              VALUES (%s, %s, %s, %s, %s, %s)''', (title, content, fixed_filepath, publish_date, user_id, depot_id[0]))
            
            msg = 'News published successfully!'
            return redirect(url_for('manager_news', msg=msg))
        
        return render_template('manager-news_publish.html', manager_info=manager_info, role=role, location=session['location'][0])
    else:
        return redirect(url_for('logout'))

@app.route('/manager/balancechecking', methods=['GET', 'POST'])
def manager_balance_checking():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 2:
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()
        
        cursor.execute('''SELECT depot_id FROM staff WHERE user_id = %s''', (user_id,))
        depot_info = cursor.fetchone()
        depot_id = depot_info[0]

        searchinput = request.args.get('searchinput', '').strip()
        selected_status = request.args.get('status')
        sort_by = request.args.get('sort_by')
        reverse = request.args.get('reverse', 'False') == 'True'

        sort_column_map = {
            'account_name': 'accounts.account_name',
            'balance': 'accounts.balance',
            'status': 'users.status',
            'credit_limit': 'accounts.credit_limit_monthly'
        }
        sort_column = sort_column_map.get(sort_by, 'accounts.account_name')

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
                        INNER JOIN users ON accounts.user_id = users.user_id INNER JOIN payments ON payments.user_id = accounts.user_id
                    WHERE accounts.city = %s AND accounts.balance < 0 AND payments.payment_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY);'''

        params = [depot_id]

        if searchinput:
            try:
                balance_value = float(searchinput)
                query += " AND accounts.balance = %s"
                params.append(balance_value)
            except ValueError:
                query += " AND (accounts.account_name LIKE %s)"
                params.append(f'%{searchinput}%')

        if selected_status:
            query += " AND users.status = %s"
            params.append(selected_status)

        query += f" ORDER BY {sort_column} {'DESC' if reverse else 'ASC'}"
        
        cursor.execute(query, params)
        accounts = cursor.fetchall()

        statuses = ["Active", "Inactive"]

        return render_template('manager-balance_checking.html', location=session['location'][0], manager_info=manager_info, accounts=accounts, statuses=statuses, searchinput=searchinput, selected_status=selected_status, sort_by=sort_by, reverse=reverse)
    else:
        return redirect(url_for('logout'))


@app.route('/manager/balancechecking_detail/<int:account_id>')
def manager_balance_checking_detail(account_id):
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 2:
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        manager_info = cursor.fetchone()
        
        cursor.execute('''SELECT depot_id FROM staff WHERE user_id = %s''', (user_id,))
        depot_info = cursor.fetchone()
        depot_id = depot_info[0]

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
                          WHERE accounts.account_id = %s AND accounts.city = %s''', (account_id, depot_id))
        account = cursor.fetchone()

        cursor.execute('''SELECT 
                            payments.payment_id,
                            payments.payment_date,
                            payments.amount,
                            payments.status
                          FROM 
                            payments
                          WHERE payments.user_id = (SELECT user_id FROM accounts WHERE account_id = %s)''', (account_id,))
        payments = cursor.fetchall()

        return render_template('manager-balance_checking_detail.html', location=session['location'][0],role=role,manager_info=manager_info, account=account, payments=payments)
    else: 
        return redirect(url_for('logout'))

@app.route('/manager/subscription-list', methods=['GET', 'POST'])
def manager_subscription_list():
    # Get the user's role from the session
    role = session.get('role')
    
    # Get the user's ID from the session
    user_id = session.get('user_id')
    
    # Get a cursor object to interact with the database
    cursor = getCursor()
    
    # Fetch manager information for use in the manager.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                      FROM roles 
                      INNER JOIN users ON roles.role_id = users.role_id 
                      INNER JOIN staff ON staff.user_id = users.user_id 
                      WHERE users.user_id = %s''', (user_id,))
    manager_info = cursor.fetchone()

    if 'loggedin' in session and role == 2:
        # Fetch the user's depot_id for GET requests without form submission
        manager_depot = session.get('location')

        cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (manager_depot[0],))
        location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
        
        # Fetch subscription list for the manager's depot
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
                        WHERE (customers.city = %s OR accounts.city = %s)'''
        
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

        # Execute the query
        if type_filter in ['Weekly', 'Biweekly', 'Monthly']:
            cursor.execute(base_query + ' ORDER BY subscription_records.record_id DESC;', (location_id, location_id, type_filter))
        else:
            cursor.execute(base_query + ' ORDER BY subscription_records.record_id DESC;', (location_id, location_id))

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
                                    WHERE (customers.city = %s OR accounts.city = %s) AND (customers.given_name LIKE %s OR customers.family_name LIKE %s OR accounts.account_name LIKE %s OR boxes.box_name LIKE %s)'''
                cursor.execute(search_query + ' ORDER BY subscription_records.record_id DESC;', (location_id, location_id, f'%{search_input}%', f'%{search_input}%', f'%{search_input}%', f'%{search_input}%'))
                subscription_list = cursor.fetchall()

        return render_template('manager_subscription_list.html', manager_info=manager_info, subscription_list=subscription_list, role=role, location=session['location'][0], status_filter=status_filter, type_filter=type_filter)
    else: 
        return redirect(url_for('logout'))






