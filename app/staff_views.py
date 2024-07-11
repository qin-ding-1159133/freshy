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
from datetime import date



hashing = Hashing(app)  #create an instance of hashing
from dateutil import relativedelta
from dateutil.relativedelta import relativedelta


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

@app.route("/staff/dashboard")
def staff_dashboard():
    # Check if user is logged in
    if 'loggedin' in session:
        role = session.get('role')  # Get the user's role from the session

        # Redirect based on user's role
        if role == 3:  
            # Get the user's ID from the session
            user_id = session.get('user_id')

            # Get a cursor object to interact with the database
            cursor = getCursor()

            # Execute a SQL query to fetch the staff's details including depot_id
            cursor.execute('SELECT * FROM staff WHERE user_id = %s', (user_id,))
            staff_details = cursor.fetchone()

            # Execute a SQL query to fetch the staff's role 
            cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
            staff_info = cursor.fetchone()

            if staff_details:
                # Extract depot_id from staff's details
                depot_id = staff_details[9]

                # Execute a SQL query to fetch the location based on depot_id
                cursor.execute('SELECT location FROM depots WHERE depot_id = %s', (depot_id,))
                location_result = cursor.fetchone()

                if location_result:
                    location = location_result[0]
                else:
                    location = "Location not found"
                
                # Execute a SQL query to fetch the most recent 3 incoming orders, ordering by date and then order ID
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

                cursor.execute('''SELECT * FROM customers WHERE city = %s ORDER BY user_id DESC LIMIT 4''', (depot_id,))
                recent_customers = cursor.fetchall()

                cursor.execute('''SELECT * FROM accounts WHERE city = %s ORDER BY user_id DESC LIMIT 4''', (depot_id,))
                recent_accounts = cursor.fetchall()

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


                # check if subscription has freshed today
                todaydate = date.today()
                cursor.execute('select max(fresh_date) from daily_fresh_subscriptions')
                max_fresh_date = cursor.fetchone()
                if max_fresh_date[0]< todaydate:
                    fresh = 'yes'
                else:
                    fresh = 'no'

                # Render the staff dashboard template with location data
                return render_template('staff-dashboard.html', orders=orders, total_customers=total_customers, total_orders=total_orders, total_revenue=total_revenue, total_subscriptions=total_subscriptions, staff_details=staff_details, staff_info=staff_info, 
                                       location=location, recent_orders=recent_orders, recent_products=recent_products, recent_boxes=recent_boxes, recent_news=recent_news, recent_customers=recent_customers, recent_accounts=recent_accounts, recent_subscription=recent_subscription, fresh=fresh)
            else:
                # Handle case where staff details are not found
                return render_template('error.html', error="Staff details not found")
        else:
            # Redirect to the error page since the user's role doesn't match any predefined roles
            return redirect(url_for('error'))
    # User is not logged in redirect to error page
    return redirect(url_for('logout'))
     
  
@app.route('/staff/profileupdate',methods= ['get','post'])
def staff_profileupdate():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor=getCursor()
    # Fetch staff information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                    FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                    INNER JOIN staff ON staff.user_id = users.user_id 
                    WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()

    if 'loggedin' in session and role == 3: 
        if request.method=='GET':
            if request.args.get('msg'):
                msg= request.args.get('msg')
            else:
                msg=''
            user_id = session['user_id']
            cursor=getCursor()
            cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.user_id=%s',(user_id,))
            profileinfo= cursor.fetchone()
            cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
            profile_image_url = cursor.fetchone()

            return render_template("staff_profile_update.html", role=role, staff_info=staff_info, location=session['location'][0], profileinfo=profileinfo,msg=msg,profile_image_url= profile_image_url)
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
                        cursor.execute("""SELECT pic FROM customers WHERE user_id = %s""", (user_id,))
    
                        profile_image_url = cursor.fetchone()
                        msg="Profile has been successfully updated!"

                        return render_template("staff_profile_update.html",profileinfo="",role=role, staff_info=staff_info, msg=msg,profile_image_url=profile_image_url, location=session['location'][0])

                    else: #if no pic uploaded, then no need to update image in database
                        cursor = getCursor()
                        cursor.execute("UPDATE staff set title=%s,given_name=%s,family_name=%s,email=%s,phone_number=%s where user_id=%s",(title,first_name,family_name,email,phone_number,user_id,))
                        msg="Profile has been successfully updated!"

                        cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
                        profile_image_url = cursor.fetchone()

                        return redirect( url_for('staff_profile', msg=msg))
    else:
        return redirect(url_for('logout'))
    

@app.route("/staff/deleteimg")
def staff_deleteimg():
    user_id = session['user_id']
    cursor=getCursor()
    # change staff pic to default one if deleting
    cursor.execute("update staff set pic=%s where user_id=%s",("app/static/assets/img/avatar.jpg",user_id,))
    msg="Image has been successfully deleted!"
    # Fetch staff information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                    FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                    INNER JOIN staff ON staff.user_id = users.user_id 
                    WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()
    return render_template("staff_profile_update.html",staff_info=staff_info, profileinfo="",msg=msg,profile_image_url='', location=session['location'][0])



@app.route("/staff/profile")
def staff_profile():
    cursor =  getCursor()
    role = session.get('role')
    cart = session.get('cart', {})

    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg = ''

    #if 'loggedin' in session and role == 4:

  
    user_id = session['user_id']
    # Fetch staff information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                    FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                    INNER JOIN staff ON staff.user_id = users.user_id 
                    WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()

    if request.args.get('msg'):
        msg = request.args.get('msg')
    else: 
        msg = ''
     
    cursor.execute('select s.*, d.location,u.status,r.responsibility_name from staff as s join depots as d on s.depot_id=d.depot_id join users as u on s.user_id=u.user_id join responsibilities as r on s.responsibility_id=r.responsibility_id where s.user_id=%s',(user_id,))
    profileinfo= cursor.fetchone()

    cursor.execute("""SELECT pic FROM staff WHERE user_id = %s""", (user_id,))
    profile_image_url = cursor.fetchone()
    

    return render_template ('staff_profile.html', msg=msg, role=role,cart=cart,location=session['location'][0], profile=profileinfo, profile_image_url=profile_image_url, staff_info=staff_info)

    

    # else:
    #     return redirect(url_for('login'))

@app.route('/staff/password_update', methods=['GET', 'POST'])
def staff_password_update():
    role = session.get('role')
    cart = session.get('cart', {})

    if 'loggedin' not in session or session.get('role') != 3:
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
    staff_info = cursor.fetchone()

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
            return redirect(url_for('staff_profile',cart=cart,location=session['location'][0],role=role,msg=msg,staff_info=staff_info))  # Redirect to the staff profile page after successful update


    #if not staff_info:
    #    return render_template('error.html', error="Staff details not found")

    return render_template('staff_password_update.html', cart=cart,location=session['location'][0],role=role,msg=msg,staff_info=staff_info) 

@app.route('/staff/product-list', methods = ['GET', 'POST'])
def staff_product_list():
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
    # Fetch staff information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()
    # Fetch all distinct categories from the database
    cursor.execute('''SELECT DISTINCT product_category_name FROM product_categories where product_category_id !="7" and product_category_id !="8"''')
    categories = [row[0] for row in cursor.fetchall()]
    if 'loggedin' in session and role == 3:
        location_id = None  # Assign a default value
        if request.method == 'POST':
            # Fetch the user's depot_id
            staff_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
            location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

            searchinput = request.form.get('searchinput', '').strip()
            selected_category = request.form.get('category')
        else:
            # If it's a GET request, get search input, and selected category from query parameters
            searchinput = request.args.get('searchinput', '').strip()
            selected_category = request.args.get('category')

        if searchinput:
            staff_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
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
                staff_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
                location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
                cursor.execute('''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, pro.product_id
                                    FROM product p 
                                    LEFT JOIN products pro ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                               Left join units on p.unit = units.unit_id
                                    WHERE product_status="1" AND pro.product_category_id != "7" AND pro.product_category_id != "8" AND pro.depot_id = %s AND pc.product_category_name = %s
                                    ORDER BY pro.product_id DESC''',
                                (location_id, selected_category,))
            
            else:
                # Fetch the user's depot_id for GET requests without form submission
                staff_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
                location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

                # Fetch all products
                cursor.execute('''SELECT p.SKU, pc.product_category_name, p.product_name, pro.product_price, units.unit_name, stock.quantity, pro.product_id
                                    FROM product p 
                                    LEFT JOIN products pro ON p.SKU = pro.SKU
                                    LEFT JOIN product_categories pc ON pro.product_category_id = pc.product_category_id
                                    LEFT JOIN stock on stock.product_id = pro.product_id 
                               Left join units on p.unit = units.unit_id
                                    WHERE product_status="1" AND pro.product_category_id != "7" AND pro.product_category_id != "8" and pro.depot_id = %s
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
        return render_template('staff-product_list.html', location=session['location'][0], products=products, staff_info=staff_info, role=role, categories=categories, searchinput=searchinput, selected_category=selected_category, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


@app.route('/staff/product-list/product', methods=["GET","POST"])
def staff_product_details():
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor=getCursor()
    # Fetch staff information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()
    if 'loggedin' in session and role == 3: 
        cursor=getCursor()

        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''

        product_id = request.args.get('product_id')

        cursor.execute("""SELECT p.SKU, p.product_name, pro.product_price, units.unit_name, p.pic, p.product_des, p.product_origins
                       FROM product p LEFT JOIN products pro ON p.SKU = pro.SKU
                       left join units on p.unit=units.unit_id 
                       WHERE pro.product_id = %s""", (product_id,)) 
        product = cursor.fetchall()

        return render_template('staff-product_details.html', location=session['location'][0], staff_info=staff_info, product=product, role=role, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))
    
@app.route('/staff/product-list/add-product', methods = ['GET', 'POST'])
def staff_add_new_product():
    role = session.get('role')
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories where product_category_id !="7" and product_category_id !="8"')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    if 'loggedin' in session and role == 3:
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

            return render_template('staff-add_new_product.html', msg=msg, list_unit=list_unit, new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, staff_info=staff_info, depot_id=depot_id[0], role=role, location=session['location'][0] )
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
                return redirect(url_for('staff_add_new_product', new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, staff_info=staff_info, depot_id=depot_id[0], msg=msg, role=role, location=session['location'][0]))
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
                            return redirect(url_for('staff-add_new_product', new_product_id=new_product_id, product_categories=product_categories, promotion_type=promotion_type, staff_info=staff_info, depot_id=depot_id[0], msg=msg, role=role, location=session['location'][0]))
                    else:
                        fixed_filepath = "app/static/assets/img/product_avatar.png"

            cursor.execute('INSERT INTO product VALUES (%s, %s, %s, %s, %s, %s);', (product_name, sku, unit, fixed_filepath, product_des, product_origins))
            cursor.execute('INSERT INTO union_skus VALUES (%s, "product");', (sku, ))
            cursor.execute('INSERT INTO products VALUES (%s, %s, %s, %s, %s, %s, "1");', (new_product_id, sku, product_price, product_category_id, promotion_type_id, depot_id))
            cursor.execute('Insert into stock values (%s, %s, %s);', (new_product_id, depot_id, stock_quantity,))
            msg = 'Product has been added successfully!'
            return redirect(url_for('staff_product_list', msg=msg))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/staff/product-list/product/update', methods = ['GET', 'POST'])
def staff_edit_product():
    role = session.get('role')
    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg=''
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories where product_category_id !="7" and product_category_id !="8"')
    product_categories = cursor.fetchall()
    
    cursor.execute('SELECT * FROM promotion_types')
    promotion_type = cursor.fetchall()

    if 'loggedin' in session and role == 3:
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
            return render_template('staff-update_product.html', msg=msg, list_unit=list_unit, stock_info=stock_info, product_id=products_info[0], product_categories=product_categories, promotion_type=promotion_type, staff_info=staff_info, depot_id=depot_id[0], role=role, location=session['location'][0], product_info=product_info, products_info=products_info)

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
                            return redirect(url_for('staff_edit_product', sku=sku, product_id=product_id, product_categories=product_categories, promotion_type=promotion_type, staff_info=staff_info, depot_id=depot_id[0], msg=msg, role=role, location=session['location'][0], product_info=product_info, products_info=products_info, stock_info=stock_info))
                    else:
                        fixed_filepath = request.form.get('old_image')
            cursor.execute('UPDATE product SET product_name = %s, unit = %s, pic = %s, product_des = %s, product_origins = %s WHERE SKU = %s;', (product_name, unit, fixed_filepath, product_des, product_origins, sku))
            cursor.execute('UPDATE products SET SKU = %s, product_price = %s, product_category_id = %s, promotion_type_id = %s where product_id = %s;', (sku, product_price, product_category_id, promotion_type_id, product_id))
            cursor.execute('UPDATE stock SET quantity = %s WHERE product_id = %s;', (stock_quantity, product_id))
            msg = 'You have successfully updated the product.'
            return redirect(url_for('staff_product_details', msg=msg, product_id=product_id))
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/staff/product-list/delete')
def staff_product_delete():
    product_id = request.args.get('product_id')
    cursor = getCursor()
    cursor.execute('UPDATE products SET product_status="0" WHERE product_id = %s;', (product_id,))
    msg = 'Product has been removed successfully.'
    return redirect( url_for('staff_product_list', msg=msg))

@app.route('/staff/premade-box-list', methods = ['GET', 'POST'])
def staff_premade_box_list():
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
    # Fetch staff information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()
    # Fetch all distinct categories from the database
    cursor.execute('''SELECT DISTINCT product_category_name FROM product_categories where product_category_id !="7" and product_category_id !="8"''')
    categories = [row[0] for row in cursor.fetchall()]
    if 'loggedin' in session and role == 3:
        location_id = None  # Assign a default value
        if request.method == 'POST':
            # Fetch the user's depot_id
            staff_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
            location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

            searchinput = request.form.get('searchinput', '').strip()
            selected_category = request.form.get('category')
        else:
            # If it's a GET request, get search input, and selected category from query parameters
            searchinput = request.args.get('searchinput', '').strip()
            selected_category = request.args.get('category')

        if searchinput:
            staff_depot = session.get('location')

            cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
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
                staff_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
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
                staff_depot = session.get('location')

                cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
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
        return render_template('staff-premade_box_list.html', location=session['location'][0], products=products, staff_info=staff_info, role=role, categories=categories, searchinput=searchinput, selected_category=selected_category, msg=msg)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))

@app.route('/staff/premade-box-list/premade-box', methods=["GET","POST"])
def staff_premade_box_details():
    # Get the user's role from the session
    role = session.get('role')
    # Get the user's ID from the session
    user_id = session.get('user_id')
    # Get a cursor object to interact with the database
    cursor=getCursor()
    # Fetch staff information for use of staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()
    if 'loggedin' in session and role == 3: 
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

        return render_template('staff-premade_box_details.html', location=session['location'][0], staff_info=staff_info, product=product, role=role, msg=msg, box_items=box_items)
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page

        return redirect(url_for('logout'))

@app.route('/staff/premade-box-list/delete')
def staff_premade_box_delete():
    product_id = request.args.get('product_id')
    cursor = getCursor()
    cursor.execute('UPDATE products SET product_status="0" WHERE product_id = %s;', (product_id,))
    msg = 'Premadebox has been removed successfully.'
    return redirect( url_for('staff_premade_box_list', msg=msg))

@app.route('/staff/orderlist',methods=['get','post'])
def staff_orderlist():
    role = session.get('role')
    msg=''
    cursor = getCursor()
    user_id = session['user_id']
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()
    cursor.execute('SELECT * FROM product_categories')
    product_categories = cursor.fetchall()
    


    if 'loggedin' in session and role == 3:
        # get all order status types
        if request.args.get('msg'):
            msg = request.args.get('msg')
        else: 
            msg = ''

        if request.method=='GET':                

            cursor.execute('select * from order_status_types')
            order_status_types = cursor.fetchall()

            cursor.execute('select depot_id from staff where user_id=%s',(user_id,))
            depot= cursor.fetchone()
            #changed 2605 7pm
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
            # get all order number 
            # simplified
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

            #get responsible id to differ the role
            cursor.execute('select responsibility_id from staff where user_id=%s',(user_id,))
            resp_id = cursor.fetchone()        
            #get all staff name:
            cursor.execute(' select given_name from staff')
            staff_name_all = cursor.fetchall()

            # get max_order status list
            cursor.execute("""
                                select o.order_id,max(oa.order_status_type_id) as order_status
                                from orders as o 
                                left join order_assignments as oa on o.order_id=oa.order_id
                                where o.payment_id != ''
                                group by order_id
                            """)
            max_status= cursor.fetchall()        

            #fill in the array 
            i = 0
            for order_number in order_number_all:                
                order_status_all[i].insert(0,order_number[0])
                
                ## fill in 'begin' and 'to be started' when the resp_id is different
                for status in max_status:

                    if status[0] == order_number[0]:
                        len_status = len(str(status[1]))

                        # check if there's no assignment 
                        len_status = len(str(status[1]))
                        if len_status==4 :            
                            if resp_id[0] == 2:
                                order_status_all[i].insert(1,'Begin')
                            elif resp_id[0] ==3:                        
                                order_status_all[i].insert(1,'To Start')

                        else:

                            if  resp_id[0] == 2:
                                if status[1] ==1:
                                    order_status_all[i].insert(1,'Begin')
                                elif status[1] >= 2:
                                    order_status_all[i].insert(1,'To Start')

                            elif resp_id[0] ==3:
                                if status[1] ==2 or status[1]==3:
                                    order_status_all[i].insert(1,'Begin')
                                elif status[1] ==1:
                                    order_status_all[i].insert(1,'To Start')



                #insert name into the list
                for order_process in order_process_all:
                    if order_process[0] == order_number[0]:
                        for staff_name in staff_name_all:
                            if order_process[2] == staff_name[0]:
                                order_status_all[i].insert(1,order_process[2])


                #increase i         
                i = i +1

            
            return render_template('staff-order_list.html',msg=msg,order_status_types=order_status_types,order_number_all=order_number_all,staff_info=staff_info, location=session['location'][0],order_status_all=order_status_all)

        elif request.method=='POST':                

          # get order_status_all 
            cursor.execute('select * from order_status_types')
            order_status_types = cursor.fetchall()

            cursor.execute('select depot_id from staff where user_id=%s',(user_id,))
            depot= cursor.fetchone()
            #changed 2605 7pm
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
            # get all order number 
            # simplified
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

            #get responsible id to differ the role
            cursor.execute('select responsibility_id from staff where user_id=%s',(user_id,))
            resp_id = cursor.fetchone()        
            #get all staff name:
            cursor.execute(' select given_name from staff')
            staff_name_all = cursor.fetchall()

            # get max_order status list
            cursor.execute("""
                                select o.order_id,max(oa.order_status_type_id) as order_status
                                from orders as o 
                                left join order_assignments as oa on o.order_id=oa.order_id
                                where o.payment_id != ''
                                group by order_id
                            """)
            max_status= cursor.fetchall()        

            #fill in the array 
            i = 0
            for order_number in order_number_all:                
                order_status_all[i].insert(0,order_number[0])
                
                ## fill in 'begin' and 'to be started' when the resp_id is different
                for status in max_status:

                    if status[0] == order_number[0]:
                        len_status = len(str(status[1]))

                        # check if there's no assignment 
                        len_status = len(str(status[1]))
                        if len_status==4 :            
                            if resp_id[0] == 2:
                                order_status_all[i].insert(1,'Begin')
                            elif resp_id[0] ==3:                        
                                order_status_all[i].insert(1,'To Start')

                        else:

                            if  resp_id[0] == 2:
                                if status[1] ==1:
                                    order_status_all[i].insert(1,'Begin')
                                elif status[1] >= 2:
                                    order_status_all[i].insert(1,'To Start')

                            elif resp_id[0] ==3:
                                if status[1] ==2 or status[1]==3:
                                    order_status_all[i].insert(1,'Begin')
                                elif status[1] ==1:
                                    order_status_all[i].insert(1,'To Start')



                #insert name into the list
                for order_process in order_process_all:
                    if order_process[0] == order_number[0]:
                        for staff_name in staff_name_all:
                            if order_process[2] == staff_name[0]:
                                order_status_all[i].insert(1,order_process[2])


                #increase i         
                i = i +1
            # #filter function script
            selected_status_id = request.form.get('status_id')

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
                    #return redirect(url_for('staff_orderlist',order_status_all=status_filter_result))
                    #nok
                    return render_template('staff-order_list.html',msg=msg,order_status_types=order_status_types,order_number_all=order_number_all,staff_info=staff_info, location=session['location'][0], order_status_all=status_filter_result)


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

                    return render_template('staff-order_list.html',msg=msg,order_status_types=order_status_types,order_number_all=order_number_all,staff_info=staff_info, location=session['location'][0], order_status_all=status_filter_result)
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

                    return render_template('staff-order_list.html',msg=msg,order_status_types=order_status_types,order_number_all=order_number_all,staff_info=staff_info, location=session['location'][0], order_status_all=status_filter_result)
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

                    return render_template('staff-order_list.html',msg=msg,order_status_types=order_status_types,order_number_all=order_number_all,staff_info=staff_info, location=session['location'][0], order_status_all=status_filter_result)
            
            else:
                return render_template('staff-order_list.html',msg=msg,order_status_types=order_status_types,order_number_all=order_number_all,staff_info=staff_info, location=session['location'][0], order_status_all=order_status_all)



@app.route('/staff/updateorder/<order_id1>/<row_id>',methods=['get','post'])
def staff_updateorder(order_id1,row_id):
    cursor = getCursor()
    todaydate = datetime.now()


    # get staff info
    user_id = session['user_id']
    cursor.execute('''SELECT * from staff where user_id=%s''', (user_id,))
    staff_info = cursor.fetchone()


    cursor.execute('insert into order_assignments values (%s,%s,%s,%s)', (order_id1,row_id,staff_info[0],todaydate,))
    msg='You have successfully got the task!'

    return redirect(url_for('staff_orderlist',msg=msg))

@app.route('/staff/order_incoming', methods=['GET', 'POST'])
def staff_order_incoming():
    msg = request.args.get('msg', '')
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 3:
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        staff_info = cursor.fetchone()
        
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
                    orders.order_date
                FROM 
                    orders 
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
                UNION ALL
                SELECT 
                    orders.order_id,
                    accounts.account_name AS full_name,
                    accounts.account_address AS customer_address,
                    accounts.phone_number,
                    accounts.email,
                    COALESCE(ost.order_status_type_name, 'Pending') AS delivery_status,
                    orders.order_date
                FROM 
                    orders 
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

        return render_template('staff-order_incoming.html', staff_info=staff_info, location=session['location'][0], orders=orders, order_status=order_status, searchinput=searchinput, selected_order_status=selected_order_status, sort_by=sort_by, reverse=reverse, msg=msg, order_date=order_date_str)
    else:
        return redirect(url_for('logout'))

@app.route('/staff/order_incoming_detail/<order_id>')
def staff_order_incoming_detail(order_id):
    msg = request.args.get('msg', '')
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    if 'loggedin' in session and role == 3:
        cursor.execute('''SELECT roles.role_name, CONCAT(staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                          FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                          INNER JOIN staff ON staff.user_id = users.user_id 
                          WHERE users.user_id = %s''', (user_id,))
        staff_info = cursor.fetchone()
        
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

        return render_template('staff-order_incoming_detail.html', order_lines=order_lines, role=role, staff_info=staff_info, location=session['location'][0], theorder=theorder, msg=msg, order_statuses=order_statuses)       
    else: 
        return redirect(url_for('logout'))
    

@app.route('/staff/news', methods=['GET', 'POST'])
def staff_news():
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()

    depot_name = session['location']

    cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (depot_name[0],))
    depot_id = cursor.fetchone()

    if 'loggedin' in session and role == 3:
        if request.method == 'POST':
            searchinput = request.form.get('searchinput', '').strip()
            order = request.form.get('order')
        else:
            searchinput = request.args.get('searchinput', '').strip()
            order = request.args.get('order')

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
        return render_template('staff-news.html', staff_info=staff_info, role=role, news_list=news_list, searchinput=searchinput, order=order, location=session['location'][0])
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


@app.route('/staff/news/<int:news_id>', methods=['GET'])
def staff_news_details(news_id):
    role = session.get('role')
    user_id = session.get('user_id')
    cursor = getCursor()

    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()

    if 'loggedin' in session and role == 3:
        cursor.execute('''SELECT news.*, CONCAT(staff.given_name, ' ', staff.family_name) AS full_name
                   FROM news 
                   INNER JOIN staff ON news.created_by = staff.user_id
                   WHERE news_id = %s''', (news_id,))
        news_item = cursor.fetchone()

        if news_item:
            return render_template('staff-news_details.html', news_item=news_item, staff_info=staff_info, role=role, location=session['location'][0])
        else:
            return redirect(url_for('error', msg='News not found'))   
    else:
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))   

@app.route('/staff/subscription-list', methods=['GET', 'POST'])
def staff_subscription_list():
    # Get the user's role from the session
    role = session.get('role')
    
    # Get the user's ID from the session
    user_id = session.get('user_id')
    
    # Get a cursor object to interact with the database
    cursor = getCursor()
    
    # Fetch staff information for use in the staff.html extension in the template
    cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
    staff_info = cursor.fetchone()

    if 'loggedin' in session and role == 3:
        # Fetch the user's depot_id for GET requests without form submission
        staff_depot = session.get('location')

        cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
        location_id = cursor.fetchone()[0]  # Get the first item of the result tuple
        
        # Fetch subscription list for the staff's depot
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

        return render_template('staff_subscription_list.html', staff_info=staff_info, subscription_list=subscription_list, role=role, location=session['location'][0], status_filter=status_filter, type_filter=type_filter)
    else: 
        return redirect(url_for('logout'))
    
@app.route('/staff/customerlist',methods=['get','post'])
def staff_customerlist():
    role = session.get('role')
    user_id = session['user_id']
    cursor=getCursor()
    # Fetch the user's depot_id
    staff_depot = session.get('location')

    cursor.execute('SELECT depot_id FROM depots WHERE location = %s;', (staff_depot[0],))
    location_id = cursor.fetchone()[0]  # Get the first item of the result tuple

    if 'loggedin' in session and role == 3:
        cursor=getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        staff_info = cursor.fetchone()
        
        if request.method=='GET':

            cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where u.role_id = 4 and d.depot_id=%s
                      """,(location_id,))
            customerinfo= cursor.fetchall()
           
            return render_template('staff_customer_list.html', location=session['location'][0], staff_info=staff_info,allprofile=customerinfo)
        else:
            searchinput = request.form['searchinput']
            all= searchinput.split()
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
                return render_template('staff_customer_list.html', location=session['location'][0], staff_info=staff_info,allprofile=allprofile)

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
                return render_template('staff_customer_list.html', location=session['location'][0], staff_info=staff_info,allprofile=allprofile)

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
                return render_template('staff_customer_list.html', location=session['location'][0], staff_info=staff_info,allprofile=allprofile)
    else: 
        return redirect(url_for('logout'))


@app.route("/staff/customerprofile/<user_id1>")
def staff_customer_profile(user_id1):
    role = session.get('role')
    if 'loggedin' in session and role == 3:
        cursor =  getCursor()

        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        staff_info = cursor.fetchone()
        

        cursor.execute("""
                        select c.*,d.location,u.status,roles.role_name from customers as c
                        join depots as d on c.city = d.depot_id
                        join users as u on c.user_id=u.user_id
                        join roles on u.role_id = roles.role_id
                        where c.user_id=%s 
                       """
                       ,(user_id1,))
        profile = cursor.fetchone()
        return render_template ('staff-customer-profile.html', location=session['location'][0], staff_info=staff_info,profile=profile)       
    else: 
        return redirect(url_for('logout'))
    
@app.route('/staff/accountlist',methods=['GET','POST'])
def staff_account_list():
    role = session.get('role')
    user_id = session['user_id']

    if 'loggedin' in session and role == 3:
        cursor=getCursor()
        cursor=getCursor()
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        staff_info = cursor.fetchone()
      
        cursor.execute('select depot_id from staff where user_id=%s',(user_id,))
        my_depot = cursor.fetchone()
        if request.method=='GET':

            cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5 and a.city=%s""",(my_depot[0],))
            accountlist= cursor.fetchall()
           

            return render_template('staff-account_list.html', location=session['location'][0], staff_info=staff_info,cardHolderList=accountlist)
        else:
            searchinput = request.form['searchinput']
            all= searchinput.split()
            if len(all)==0:
                cursor=getCursor()
                cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5 and a.city=%s""",(my_depot[0],))              
                cardHolderList=cursor.fetchall()
                return render_template('staff-account_list.html', location=session['location'][0], staff_info=staff_info,cardHolderList=cardHolderList)

            elif len(all)==1:
                cursor=getCursor()
                parameter = ("%"+all[0]+"%")
                cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE u.role_id = 5 AND a.account_name LIKE %s""",(parameter,))
                cardHolderList=cursor.fetchall()
                return render_template('staff-account_list.html', location=session['location'][0], staff_info=staff_info,cardHolderList=cardHolderList)

            
    else: 
        return redirect(url_for('logout'))


@app.route('/staff/accountlist/profile',methods=['get','post'])
def staff_account_profile():
    
    role = session.get('role')
    account_holder_id = request.args.get('account_holder_id')

    if request.args.get('msg'):
        msg = request.args.get('msg')
    else:
        msg = ''
    
    if 'loggedin' in session and role == 3:
        cursor =  getCursor()
        user_id = session['user_id']
        cursor.execute('''SELECT roles.role_name, CONCAT (staff.given_name, " ", staff.family_name) AS full_name, staff.pic
                           FROM roles INNER JOIN users ON roles.role_id = users.role_id 
                           INNER JOIN staff ON staff.user_id = users.user_id 
                           WHERE users.user_id = %s''', (user_id,))
        staff_info = cursor.fetchone()

        cursor.execute("""SELECT a.*, d.location, u.status, roles.role_name, u.username FROM accounts AS a JOIN depots AS d ON a.city = d.depot_id JOIN users AS u ON a.user_id=u.user_id JOIN roles ON u.role_id = roles.role_id WHERE a.account_id = %s""", (account_holder_id,))

        profile= cursor.fetchone()


        return render_template ('staff-account_profile.html', location=session['location'][0], staff_info=staff_info, profile=profile, msg=msg)
    
    else:
        return redirect(url_for('logout'))