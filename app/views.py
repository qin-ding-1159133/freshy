from app import app
import re
from flask import request, session
from flask import render_template, redirect, url_for, jsonify
import mysql.connector
from mysql.connector import FieldType
from collections import defaultdict
from datetime import date
from flask_hashing import Hashing
#import connect
import os
from dateutil import relativedelta
from datetime import datetime
import datetime as dt
import schedule
import time
from decimal import *
from werkzeug.utils import secure_filename
from decimal import Decimal

from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler

from config import mail_username, mail_password, mail_sender


app.config['MAIL_SERVER'] = 'smtp.mailgun.org'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAUL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = mail_username
app.config['MAIL_PASSWORD'] = mail_password
app.config['MAIL_DEFAULT_SENDER'] = mail_sender



mail = Mail(app)


UPLOAD_FOLDER = 'app/static/assets/img'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


hashing = Hashing(app)  #create an instance of hashing
app.secret_key = 'hello'

# Initialise global variables for database connection
dbconn = None
connection = None

# Function to establish database connection and return cursor
def getCursor():
    global dbconn
    global connection
    connection = mysql.connector.connect(user="sqladmin", password="Superwine1@", host="servermysql325.mysql.database.azure.com", port=3306, database="fresh_harvest_delivery_db", ssl_ca="{ca-cert filename}", ssl_disabled=False)
    dbconn = connection.cursor()
    return dbconn

@app.route('/subscription/order')
def subscription_order():
    today = date.today()
    cursor=getCursor()
    role = session.get('role')

    cursor.execute('select * from daily_fresh_subscriptions order by fresh_date desc ')
    latest_fresh = cursor.fetchone()
    if today != latest_fresh[1]:
        cursor=getCursor()
        cursor.execute('select user_id from subscription_records')
        user_all = cursor.fetchall()
        new_id = latest_fresh[0] +1
        cursor.execute('insert into daily_fresh_subscriptions values (%s,%s)',(new_id,today,))
        for user in user_all:

            cursor.execute("""
                           select s.*,p.product_price,p.depot_id,shippment_price,shippment_id from subscription_records as s 
                            join products as p on s.product_id=p.product_id 
                            join shippments as sh on p.depot_id=sh.depot_id 
                            where s.subscription_status != 'Cancelled'
                            and s.user_id=%s""",(user[0],))
            all_sub = cursor.fetchall()
            sub_order=[]
            for sub in all_sub:
                    # Parse the dates from strings into datetime objects
                date1 = today
                date2 = sub[2]
                    
                    # Calculate the difference between the two dates
                difference = relativedelta.relativedelta(date2, date1)     
                df= difference.days
        # collect all subscription order that needs to happen today from that customer
                if sub[5]=='Weekly' :
                    if df % 7 ==0:
                        sub_order.append((sub[3],sub[4],sub[5],sub[8]))

                    #if customer has bi-weekly subscription
                elif sub[5]=='Biweekly':
                    if df % 14 == 0:
                        sub_order.append((sub[3],sub[4],sub[5],sub[8]))

                        # append an order line to pack

                elif sub[5] =='Monthly' :
                    if df % 30 == 0:
                        sub_order.append((sub[3],sub[4],sub[5],sub[8]))

            
                                #create an order for that customer
            if sub_order:

                cursor.execute('select max(order_id) from orders')
                max_order_id = cursor.fetchone()                    
                new_order_id = max_order_id[0] +1

                cursor.execute('select max(payment_id) from payments')
                max_payment_id = cursor.fetchone()            
                new_payment_id = max_payment_id[0] +1
                cursor.execute('insert into payments value (%s,%s,%s,%s,%s,%s)',(new_payment_id,sub[1],0,sub[6],today,'Pending',))
                cursor.execute('insert into orders value (%s,%s,%s,%s,%s)',(new_order_id,sub[1],today,new_payment_id,sub[11],))

                amount = 0

                for order in sub_order:
                    #insert order lin in line table
                    cursor.execute('select max(line_number) from order_lines')
                    max_line_number = cursor.fetchone()
                    new_line_number = max_line_number[0]+1
                    cursor.execute('insert into order_lines value (%s,%s,%s,%s)',(new_line_number,new_order_id,order[0],order[1],))
                    amount = amount + order[3] * order[2]
                
                amount = amount + sub[10] #adding shippment fee later, gst later(float to decimal)

                cursor.execute('update payments set amount=%s,status=%s where payment_id=%s',(amount,'Completed',new_payment_id,))
                

    if role ==1:
        return redirect(url_for('admin_dashboard'))
    elif role ==2:
        return redirect(url_for('manager_dashboard'))
    elif role ==3:
        return redirect(url_for('staff_dashboard'))

#             return render_template('test.html',difference=amount)

# schedule.every().day.at('10:35').do(subscription_order)
# while True:
#     schedule.run_pending()
#     time.sleep(1)

@app.route("/")
@app.route('/home', methods=["GET","POST"])
def homepage():

  

    msg = ''
    # Initialise an empty alert variable to hold error messages
    alert = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    role = session.get('role')  
    user_in_session = session.get('user_id')
    location = session.get('location')
    print(location)

    depot_all=get_depot()
    user_info = get_user_info(user_in_session, role)
    
    promotionProList = ()
    today = date.today()
    cart = session.get('cart', {})
    cursor=getCursor()
    if request.args.get('regi'):
        regi=request.args.get('regi')
    else:
        regi=''

    # Check weather the user is in session
    if 'loggedin' in session: 

        cursor=getCursor()

        # Fetch prodcuts if user's location is in Auckland
        if 'Auckland' in location:
            
            cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = '1' AND pro.product_status =1 AND pro. promotion_type_id = 7""")

            promotionProList = cursor.fetchall()

        # Fetch prodcuts if user's location is in Christchurch
        elif 'Christchurch' in location:
            cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = '2' AND pro.product_status =1 AND pro. promotion_type_id = 7""")
            promotionProList = cursor.fetchall()

        # Fretch prodcuts if user's location is in Wellington    
        elif 'Wellington' in location:
            cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = '3' AND pro.product_status =1 AND pro. promotion_type_id = 7""")
            promotionProList = cursor.fetchall()

        # Fetch prodcuts if user's location is in Hamilton   
        elif 'Hamilton' in location:
            cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = '4' AND pro.product_status =1 AND pro. promotion_type_id = 7""")
            promotionProList = cursor.fetchall()

        # Fetch prodcuts if user's location is in Invercargill 
        elif 'Invercargill' in location:
            cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = '5' AND pro.product_status =1 AND pro. promotion_type_id = 7""") 
            promotionProList = cursor.fetchall()

    if 'loggedin' not in session: 

    
        cursor=getCursor()
        cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.product_status =1 AND pro. promotion_type_id = 7""")

        

        promotionProList = cursor.fetchall()
 

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access. Extract username and password from the form data
        username = request.form['username']
        user_password = request.form['password']
        # Get a cursor object to interact with the database
        cursor = getCursor()
        # Execute a SQL query to select the user account based on the provided username
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        # Fetch the first matching record from the result
        account = cursor.fetchone()
        # Check if the account exists
        if account is not None:
            # Extract the hashed password from the account record
            password = account[2]
            # Verify the submitted password against the hashed password
            if hashing.check_value(password, user_password, salt='c639'):
                # If account exists, check account status is active
                if account[4] != 'Active':
                    # Set an error message for inactive account
                    alert = 'Your account is currently inactive. Please contact the administrator for assistance. You can reach us via phone at (0064)221356836 or by email at sam@freshharvest.co.nz.'
                    return render_template('index.html', alert=alert, depot_all=depot_all) 
                if account[3] in [1, 2, 3]:
                    cursor.execute('select depots.location from depots inner join staff on staff.depot_id = depots.depot_id where staff.user_id = %s', (account[0],))
                elif account[3] == 4:
                    cursor.execute('select depots.location from depots inner join customers on customers.city = depots.depot_id where customers.user_id = %s', (account[0],))
                else:
                    cursor.execute('select depots.location from depots inner join accounts on accounts.city = depots.depot_id where accounts.user_id = %s', (account[0],))
                user_location = cursor.fetchone()
                # Create session data for the logged-in user, we can access this data in other routes
                
                session['loggedin'] = True
                session['user_id'] = account[0]
                session['username'] = account[1]
                session['role'] = account[3]
                session['location'] = user_location

               
                # Redirect the user to the dashboard page
                return redirect(url_for('dashboard'))
            else:
                # Set an error message for incorrect password credential
                alert = 'Incorrect username and/or password. Please check your credentials and try again.'
                return render_template('index.html', alert= alert, msg=msg, depot_all=depot_all, cart=cart, user_in_session=user_in_session, regi=regi)
        else:
            # Account doesnt exist or username credential incorrect
            alert = 'Incorrect username and/or password. Please check your credentials and try again.'
            return render_template('index.html', alert= alert, msg=msg, depot_all=depot_all, cart=cart, user_in_session=user_in_session, regi=regi)
    
    

    if request.method=='GET':
    
        msg = "Please complete the form!"
    else:
        role_type=request.form['role_type']
        if role_type=='Member':
            cursor=getCursor()
            cursor.execute('select * from depots')
            depot_all=cursor.fetchall()
            username = request.form['username']
            password1 = request.form['password1']
            password2 = request.form['password2']
            title=request.form['title']
            email = request.form['email']
            given_name = request.form['given_name']
            family_name = request.form['family_name']
            phone_number = request.form['phone']
            address= request.form['address1']
            city=request.form['city']

            #Check if account exists using MySQL
            cursor = getCursor()
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            account = cursor.fetchone()
            cursor.execute('select * from customers where email=%s',(email,))
            email_all_customer = cursor.fetchone()
            cursor.execute('select * from accounts where email=%s',(email,))
            email_all_account = cursor.fetchone()
            if account:
                msg = 'Account/email already exists!'
                

            elif email_all_customer or email_all_account:
                msg='Account/email already exists!'
              

            elif password1 !=password2:
                msg="Password doesn't match"
                

            else:
                hashed = hashing.hash_value(password1, salt='c639')
                cursor=getCursor()
                cursor.execute('select max(user_id) from users')
                max_user_id=cursor.fetchone()
                if max_user_id[0] is None:
                    new_userid=1
                else:
                    new_userid=max_user_id[0]+1
                cursor.execute('insert into users values (%s,%s,%s,%s,%s)',(new_userid,username,hashed,4,'Active',))
                #get new customerid
                cursor=getCursor()
                cursor.execute('insert into customers values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);',(new_userid, title, given_name, family_name, email, address, city, phone_number, 0.00, ''))
                msg= 'You have successfully registered as a member!'

    # register as an account
        elif role_type=='Account':
            cursor=getCursor()
            cursor.execute('select * from depots')
            depot_all=cursor.fetchall()
            # get all info for account
            username = request.form['username']
            password1 = request.form['password1']
            password2 = request.form['password2']
            email = request.form['email']
            account_name = request.form['accountname']
            phone_number = request.form['phone']
            address= request.form['address']
            city=request.form['city']
            credit = request.form['credit']
            files = request.files.getlist('image1')
            reason = request.form['reason']


            #Check if account exists using MySQL
            cursor = getCursor()
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            account = cursor.fetchone()
            cursor.execute('select * from customers where email=%s',(email,))
            email_all_customer = cursor.fetchone()
            cursor.execute('select * from accounts where email=%s',(email,))
            email_all_account = cursor.fetchone()
            
            if account:
                msg = 'Account/email already exists!'
                

            elif email_all_customer or email_all_account:
                msg='Account/email already exists!'
              

            elif password1 !=password2:
                msg="Password doesn't match"
                

            else:
                if files:

                    for file in files:
                        if file and allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            fixed_filepath = filepath.replace("\\","/")
                            file.save(fixed_filepath)

                            # insert users and accounts
                            hashed = hashing.hash_value(password1, salt='c639')
                            cursor=getCursor()
                            cursor.execute('select max(user_id) from users')
                            max_user_id=cursor.fetchone()
                            if max_user_id[0] is None:
                                new_userid=1
                            else:
                                new_userid=max_user_id[0]+1

                            cursor.execute('insert into users values (%s,%s,%s,%s,%s)',(new_userid,username,hashed,5,'Inactive',))

                            #get new accountid
                            cursor.execute('select max(account_id) from accounts')
                            max_account_id=cursor.fetchone()
                            if max_account_id[0] is None:
                                new_accountid=1
                            else:
                                new_accountid=max_account_id[0]+1

                            cursor=getCursor()
                            cursor.execute('insert into accounts values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(new_accountid,new_userid,account_name,address,city,email,phone_number,"app/static/assets/img/avatar.jpg",0.00,0.00,))

                            #create an application for account and credit 

                                # get max application id 

                            cursor.execute('select max(application_id) from applications')
                            max_application_id = cursor.fetchone()
                            if max_application_id[0] is None:
                                new_applicationid=1
                            else:
                                new_applicationid=max_application_id[0]+1
                                #create an application for account and credit 

                                #return render_template('test.html',new_applicationid=new_applicationid)
                            cursor.execute('insert into applications values (%s,%s,%s,%s,%s,%s,%s,%s,%s)',(new_applicationid,credit,fixed_filepath,'Pending',new_userid,0,reason,today,'',))

                            msg="Your application is awaiting approval!"


                        else: #if no pic uploaded, then no need to update image in database
                                
                            msg="Please upload the incorporate certificate!"
                
    return render_template('index.html', regi=regi, alert= alert, msg=msg, depot_all=depot_all, promotionProList=promotionProList,user_in_session=user_in_session, role=role, user_info=user_info, cart=cart)



@app.route('/member-register', methods=['get','post'])
def member_register():
    cursor=getCursor()
    cursor.execute('select * from depots')
    depot_all=cursor.fetchall()

    if request.method=='GET':

        cursor=getCursor()
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()

        return render_template('member-register.html',depot_all=depot_all)
    else:
        username = request.form['username']
        password1 = request.form['password1']
        password2 = request.form['password2']
        title=request.form['title']
        email = request.form['email']
        given_name = request.form['given_name']
        family_name = request.form['family_name']
        phone_number = request.form['phone']
        address= request.form['address1']
        city=request.form['city']

            #Check if account exists using MySQL
        cursor = getCursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        cursor.execute('select * from customers where email=%s',(email,))
        email_all_customer = cursor.fetchone()
        cursor.execute('select * from accounts where email=%s',(email,))
        email_all_account = cursor.fetchone()
        if account:
            msg = 'Account/email already exists!'
            return render_template('member-register.html',msg=msg,depot_all=depot_all)     

        elif email_all_customer or email_all_account:
            msg='Account/email already exists!'
            return render_template('member-register.html',msg=msg,depot_all=depot_all)     


        elif password1 !=password2:
            msg="Password doesn't match"
            return render_template('member-register.html',msg=msg,depot_all=depot_all)     


        else:
            hashed = hashing.hash_value(password1, salt='c639')
            cursor=getCursor()
            cursor.execute('select max(user_id) from users')
            max_user_id=cursor.fetchone()
            if max_user_id[0] is None:
                new_userid=1
            else:
                new_userid=max_user_id[0]+1
            cursor.execute('insert into users values (%s,%s,%s,%s,%s)',(new_userid,username,hashed,4,'Active',))
                #get new customerid
            cursor=getCursor()
            cursor.execute('insert into customers values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(new_userid,title,given_name,family_name,email,address,city,phone_number,0.00,'app/static/assets/img/avatar.jpg',))
            regi= 'You have successfully registered as a member!'
            return redirect(url_for('homepage',regi=regi))

@app.route('/account-register', methods=['get','post'])
def account_register():
    today = date.today()

    cursor=getCursor()
    cursor.execute('select * from depots')
    depot_all=cursor.fetchall()

    if request.method=='GET':

        cursor=getCursor()
        cursor.execute('select * from depots')
        depot_all=cursor.fetchall()

        return render_template('account-register.html',depot_all=depot_all)
    else:
        username = request.form['username']
        password1 = request.form['password1']
        password2 = request.form['password2']
        email = request.form['email']
        account_name = request.form['accountname']
        phone_number = request.form['phone']
        address= request.form['address']
        city=request.form['city']
        credit = request.form['credit']
        files = request.files.getlist('image1')
        reason = request.form['reason']


            #Check if account exists using MySQL
        cursor = getCursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        cursor.execute('select * from customers where email=%s',(email,))
        email_all_customer = cursor.fetchone()
        cursor.execute('select * from accounts where email=%s',(email,))
        email_all_account = cursor.fetchone()
            
        if account:
            msg = 'Account/email already exists!'
            return render_template('account-register.html',msg=msg,depot_all=depot_all)

        elif email_all_customer or email_all_account:
            msg='Account/email already exists!'
            return render_template('account-register.html',msg=msg,depot_all=depot_all)


        elif password1 !=password2:
            msg="Password doesn't match"
            return render_template('account-register.html',msg=msg,depot_all=depot_all)


        else:
            if files:

                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        fixed_filepath = filepath.replace("\\","/")
                        file.save(fixed_filepath)

                            # insert users and accounts
                        hashed = hashing.hash_value(password1, salt='c639')
                        cursor=getCursor()
                        cursor.execute('select max(user_id) from users')
                        max_user_id=cursor.fetchone()
                        if max_user_id[0] is None:
                            new_userid=1
                        else:
                            new_userid=max_user_id[0]+1

                        cursor.execute('insert into users values (%s,%s,%s,%s,%s)',(new_userid,username,hashed,5,'Inactive',))

                            #get new accountid
                        cursor.execute('select max(account_id) from accounts')
                        max_account_id=cursor.fetchone()
                        if max_account_id[0] is None:
                            new_accountid=1
                        else:
                            new_accountid=max_account_id[0]+1

                        cursor=getCursor()
                        cursor.execute('insert into accounts values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(new_accountid,new_userid,account_name,address,city,email,phone_number,"app/static/assets/img/avatar.jpg",0.00,0.00,))

                            #create an application for account and credit 

                                # get max application id 

                        cursor.execute('select max(application_id) from applications')
                        max_application_id = cursor.fetchone()
                        if max_application_id[0] is None:
                            new_applicationid=1
                        else:
                            new_applicationid=max_application_id[0]+1
                                #create an application for account and credit 

                                #return render_template('test.html',new_applicationid=new_applicationid)
                        cursor.execute('insert into applications values (%s,%s,%s,%s,%s,%s,%s,%s,%s)',(new_applicationid,credit,fixed_filepath,'Pending',new_userid,0,reason,today,'',))

                        regi="Your application is awaiting approval!"
                        return redirect(url_for('homepage',regi=regi))


                    else: #if no pic uploaded, then no need to update image in database
                                
                        msg="Please upload the incorporate certificate!"
                        return render_template('account-register.html',msg=msg,depot_all=depot_all)


@app.route('/products', methods=["GET","POST"])
def shop():

    role = session.get('role')  
    user_in_session = session.get('user_id')
    location = session.get('location')
    depot_all=get_depot()
    user_info = get_user_info(user_in_session, role)
    ProductList = ()
    cursor = getCursor()
    cart = session.get('cart', {})
    # Fetch products categories from database
    cursor.execute("""SELECT * FROM product_categories WHERE product_category_id !=8""")
    proCategories = cursor.fetchall()
  
   
    category = request.form.get('category')

    if 'loggedin' in session: 


        # Fetch prodcuts if user's location is in Auckland
        if 'Auckland' in location:

            if category:
             
          

             ProductList = filter_category(category, 1)
            
            else: 
                cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = '1' AND pro.product_status =1""")
                ProductList  = cursor.fetchall()
                print(ProductList)


        # Fetch prodcuts if user's location is in Christchurch
        elif 'Christchurch' in location:
            
            if category:

             ProductList = filter_category(category, 2)
            
            else: 
                cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = 2 AND pro.product_status =1""")
                ProductList  = cursor.fetchall()

        # Fretch prodcuts if user's location is in Wellington    
        elif 'Wellington' in location:
            if category:

             ProductList = filter_category(category, 3)
            
            else: 
                cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = 3 AND pro.product_status =1""")
                ProductList  = cursor.fetchall()

        # Fetch prodcuts if user's location is in Hamilton   
        elif 'Hamilton' in location:
            if category:

               ProductList = filter_category(category, 4)
            
            else: 
                cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id  WHERE pro.depot_id = 4 AND pro.product_status =1""")
                ProductList  = cursor.fetchall()

        # Fetch prodcuts if user's location is in Invercargill 
        elif 'Invercargill' in location:
            if category:

             ProductList = filter_category(category, 5)
            
            else: 
                cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = 5 AND pro.product_status =1""")
                ProductList  = cursor.fetchall()

        return render_template('shop.html',ProductList=ProductList, proCategories=proCategories, depot_all=depot_all,user_in_session=user_in_session, role=role, user_info=user_info, cart=cart)    
    
    else:   

        if category:

            if category == 'all' or category == '':

       

                #Fetch products  from database
                cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.product_status =1""")
                ProductList = cursor.fetchall()
            
            else: 

        
                cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.product_category_id = %s AND pro.product_status =1""", (category,))
                ProductList = cursor.fetchall()

            
       
        
        else:

            
            #Fetch products  from database
            cursor.execute("""SELECT DISTINCT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.product_status =1""")
            ProductList = cursor.fetchall()

           


    return render_template('shop.html',ProductList=ProductList, proCategories=proCategories, depot_all=depot_all,user_in_session=user_in_session, role=role, user_info=user_info, cart=cart)

@app.route('/products/product', methods=["GET","POST"])
def product_details():

    role = session.get('role')  
    user_in_session = session.get('user_id')
    location = session.get('location')

    depot_all=get_depot()
    user_info = get_user_info(user_in_session, role)
      
    sku = request.args.get('sku')

    product = ()
    
    cart = session.get('cart', {})
    cursor=getCursor()

    cursor.execute("""SELECT * FROM subscriptions""")
    subscriptions = cursor.fetchall()


    cursor.execute("""SELECT pro.SKU, p.product_name, b.quantity, u.unit_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN box_items AS b ON b.product_id = pro.product_id LEFT JOIN units AS u ON u.unit_id = p.unit WHERE b.SKU = %s""", (sku,))

    box_items = cursor.fetchall()
    

    if 'loggedin' in session: 


        # Fetch prodcuts if user's location is in Auckland
        if 'Auckland' in location:
            cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.depot_id = 1 AND pro.product_status =1""", (sku,))


            product = cursor.fetchone()


        # Fetch prodcuts if user's location is in Christchurch
        elif 'Christchurch' in location:
            cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.depot_id = 2 AND pro.product_status =1""", (sku,)) 

            product = cursor.fetchone()

        # Fretch prodcuts if user's location is in Wellington    
        elif 'Wellington' in location:
            cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.depot_id = 3 AND pro.product_status =1""", (sku,)) 

            product = cursor.fetchone()

        # Fetch prodcuts if user's location is in Hamilton   
        elif 'Hamilton' in location:
            cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.depot_id = 4 AND pro.product_status =1""", (sku,)) 

            product = cursor.fetchone()


        # Fetch prodcuts if user's location is in Invercargill 
        elif 'Invercargill' in location:
            cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.depot_id = 5 AND pro.product_status =1""", (sku,)) 

            product = cursor.fetchone()

        return render_template('product-details.html', product=product, depot_all=depot_all,role=role, user_info=user_info,user_in_session=user_in_session, cart=cart, subscriptions=subscriptions, box_items=box_items)    

    else: 
        cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, prom.promotion_type_name FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.product_status =1""", (sku,)) 
        product = cursor.fetchone()

        

        return render_template('product-details.html', product=product, depot_all=depot_all,role=role, user_info=user_info, user_in_session=user_in_session, cart=cart, subscriptions=subscriptions, box_items=box_items) 



    

@app.route('/about')
def about_us():
    role = session.get('role')  
    user_in_session = session.get('user_id')
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    cart = session.get('cart', {})
    
    return render_template('about.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart,role=role)

@app.route('/subscriptions', methods=["GET","POST"])
def subscriptions():
    role = session.get('role')  
    user_in_session = session.get('user_id')
    location = session.get('location')
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    cursor=getCursor()
    cart = session.get('cart', {})

    if 'loggedin' in session: 

        # Fetch prodcuts if user's location is in Auckland
        if 'Auckland' in location:

            cursor.execute("""SELECT b.SKU, b.box_name, pro.product_price, u.unit_name, b.pic, prom.discount, prom.promotion_type_name  FROM boxes AS b INNER JOIN products AS pro ON b.SKU = pro.SKU INNER JOIN units as u ON b.unit = u.unit_id INNER JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id  WHERE pro.depot_id = 1 AND pro.product_category_id =7 AND pro.product_status =1""")
            SubscriptionList  = cursor.fetchall()

        # Fetch prodcuts if user's location is in Christchurch
        elif 'Christchurch' in location:
            
            cursor.execute("""SELECT b.SKU, b.box_name, pro.product_price, u.unit_name, b.pic, prom.discount, prom.promotion_type_name  FROM boxes AS b INNER JOIN products AS pro ON b.SKU = pro.SKU INNER JOIN units as u ON b.unit = u.unit_id INNER JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.depot_id = 2 AND pro.product_category_id =7 AND pro.product_status =1""")
            SubscriptionList  = cursor.fetchall()

        # Fretch prodcuts if user's location is in Wellington    
        elif 'Wellington' in location:

            cursor.execute("""SELECT b.SKU, b.box_name, pro.product_price, u.unit_name, b.pic, prom.discount, prom.promotion_type_name  FROM boxes AS b INNER JOIN products AS pro ON b.SKU = pro.SKU INNER JOIN units as u ON b.unit = u.unit_id INNER JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id  WHERE pro.depot_id = 3 AND pro.product_category_id =7 AND pro.product_status =1""")
            SubscriptionList  = cursor.fetchall()

        # Fetch prodcuts if user's location is in Hamilton   
        elif 'Hamilton' in location:

            cursor.execute("""SELECT b.SKU, b.box_name, pro.product_price, u.unit_name, b.pic, prom.discount, prom.promotion_type_name  FROM boxes AS b INNER JOIN products AS pro ON b.SKU = pro.SKU INNER JOIN units as u ON b.unit = u.unit_id INNER JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id  WHERE pro.depot_id = 4 AND pro.product_category_id =7 AND pro.product_status =1""")
            SubscriptionList  = cursor.fetchall()

        # Fetch prodcuts if user's location is in Invercargill 
        elif 'Invercargill' in location:
            cursor.execute("""SELECT b.SKU, b.box_name, pro.product_price, u.unit_name, b.pic, prom.discount, prom.promotion_type_name  FROM boxes AS b INNER JOIN products AS pro ON b.SKU = pro.SKU INNER JOIN units as u ON b.unit = u.unit_id INNER JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id  WHERE pro.depot_id = 5 AND pro.product_category_id =7 AND pro.product_status =1""")
            SubscriptionList  = cursor.fetchall()

        return render_template('subscriptions.html',depot_all=depot_all,user_info=user_info,role=role,SubscriptionList=SubscriptionList, user_in_session=user_in_session, cart=cart)
    
    else: 
        cursor.execute("""SELECT b.SKU, b.box_name, pro.product_price, u.unit_name, b.pic, prom.discount, prom.promotion_type_name  FROM boxes AS b INNER JOIN products AS pro ON b.SKU = pro.SKU INNER JOIN units as u ON b.unit = u.unit_id INNER JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id  WHERE pro.product_category_id =7 AND pro.product_status =1""") 
        SubscriptionList = cursor.fetchall()

        return render_template('subscriptions.html',depot_all=depot_all,user_info=user_info,SubscriptionList=SubscriptionList, user_in_session=user_in_session, cart=cart) 



@app.route('/checkout-subscription/<sku1>',methods=['get','post'])
def checkout_subscription(sku1):


    role = session.get('role')  
    user_in_session = session.get('user_id') 
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    cart = session.get('cart', {})
    cart = session.get('subscription', {})

    cursor=getCursor()
    cursor.execute('select city from customers where user_id=%s ', (user_in_session,))
    depot_id = cursor.fetchone()
    if request.args.get('msg1'):
        msg1 = request.args.get('msg1')
    else: 
        msg1 = ''
    # sub_type=request.form['sub_type']
    # quantity=request.form['quantity1']
    if 'loggedin' in session:
        if request.method == "GET" :
            cursor.execute('select balance from customers where user_id=%s ',(user_in_session,))
            balance = cursor.fetchone()
            return render_template('checkout-subscription.html',msg1=msg1,balance=balance,sub = session['subscription'],sku1=sku1,depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart)

            # # get subscription type

            # cursor=getCursor()
            # cursor.execute('select city from customers where user_id=%s ', (user_in_session,))
            # depot_id = cursor.fetchone()

            # cursor.execute('select shippment_price from shippments where depot_id=%s',(depot_id[0],))
            # ship_cost = cursor.fetchone()

            # # get promotion info



            # cursor.execute('''select p.*, b.box_name,pt.discount 
            #                 from products as p
            #                 join boxes as b on p.SKU= b.SKU 
            #                 join promotion_types as pt on p.promotion_type_id = pt.promotion_type_id 
            #                 where p.SKU=%s''',(sku1,))
            # product_info = cursor.fetchone()
            # current_price = float(product_info[2])*float(product_info[8])*float(quantity)

            # # return render_template('test.html')
            # return render_template('checkout-subscription.html',msg1=msg1,sub_type=sub_type,current_price=current_price,product_info=product_info,sku1=sku1,quantity=quantity,depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart)
        else:
            # get balance 
            cursor=getCursor()
            cursor.execute('select balance from customers where user_id=%s ',(user_in_session,))
            balance = cursor.fetchone()
            if 'subscription' not in session:
                session['subscription'] = {}
            subscription = session['subscription']
            # if sku in session
            if sku1 in subscription:
                return render_template('checkout-subscription.html',msg1=msg1,balance=balance,sub = session['subscription'],sku1=sku1,depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart)

            else:
                sub_type=request.form['sub_type']
                quantity=request.form['quantity1']
                sku_chosen = sku1
                cursor=getCursor()
                cursor.execute('select city from customers where user_id=%s ', (user_in_session,))
                depot_id = cursor.fetchone()

                cursor.execute('select shippment_price from shippments where depot_id=%s',(depot_id[0],))
                ship_cost = cursor.fetchone()

                # get promotion info
                cursor.execute("""select p.*, b.box_name,pt.discount 
                                from products as p
                                join boxes as b on p.SKU= b.SKU 
                                join promotion_types as pt on p.promotion_type_id = pt.promotion_type_id 
                                where p.SKU=%s """,(sku_chosen,))
                product_info = cursor.fetchone()
                current_price = float(product_info[2])*float(product_info[8])

                current_total = current_price + ship_cost[0]
                subscription[sku_chosen] = {
                    'name':product_info[7],
                    'sub_type':sub_type,
                    'price':current_price,
                    'quantity':quantity,
                    'prod_id':product_info[0],
                    'ship':ship_cost[0]
                }
                session['subscription'] = subscription
                session.modified = True



            # # get coupon code info
            # couponcode1=request.form['couponcode']            
    
            # if couponcode1:
            #     cursor.execute('select * from coupons where coupon_code = %s and depot_id = %s',(couponcode1,depot_id[0],))
            #     coupon_info = cursor.fetchone()
            #     if coupon_info and current_total>coupon_info[3]:
            #         new_total = current_total - coupon_info[2]

            #     else:
            #         msg1 = 'Coupon code is not valid for your order'
                        
            return render_template('checkout-subscription.html',msg1=msg1,balance=balance,sub = session['subscription'],sku1=sku1,depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart)
    else:

        session.pop('subscription', None)
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))
    
@app.route('/checkout/usecoupon',methods=['get','post'])
def checkout_usecoupon():
    couponcode1=request.form['couponcode']
    sku1 = request.form['sku1']
    current_total = request.form['current']

    user_in_session = session.get('user_id') 
    cursor = getCursor()
    cursor.execute('select city from customers where user_id=%s ', (user_in_session,))
    depot_id = cursor.fetchone()

    cursor.execute('select * from coupons where coupon_code = %s and depot_id = %s',(couponcode1,depot_id[0],))
    coupon_info = cursor.fetchone()

    if coupon_info and float(current_total)>coupon_info[3]:
        new_total = current_total - coupon_info[2]

    else:
        msg1 = 'Coupon code is not valid for your order' 
        return redirect(url_for('checkout_subscription',msg1=msg1,sku1=sku1))


#subscription pay
@app.route('/pay-subscription', methods=["GET","POST"])
def pay_subscription():
    role = session.get('role')  
    user_in_session = session.get('user_id')
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    # Get cart content from session
    cart = session.get('cart', {})
    subscription = session.get('subscription', {})

    location = session.get('location')
 #need to check
    shipping_cost = get_shipping(location)
    user_id = request.args.get('user_id')
    balance = get_balance(user_id)
#need to check
    current_balance = 0.0

    shipment_id = get_shipment(location)


    error = ''
    cursor=getCursor()


    cursor.execute("""SELECT * FROM 
    payment_methods WHERE user_id = %s""", (user_id,))
    paymentMethod = cursor.fetchone()
    if 'loggedin' in session: 

        # Insert the all the date if the shipping address and billing address are different
        if request.method == "POST" and 'ccName' in request.form and 'ccNumber' in request.form and 'ccExp' in request.form and 'ccCvc' in request.form and 'total' in request.form and 'deducted' in request.form and 'updated_balance' in request.form:
            
            ccName = request.form['ccName']
            ccNumber = request.form['ccNumber']
            ccExp = request.form['ccExp']
            ccCvc = request.form['ccCvc']
            total = request.form['total']
            deducted = request.form['deducted']
            updated_balance = request.form['updated_balance']
            order_date = datetime.now().date()


            print(cart)

            print(ccName, ccNumber, ccExp, ccCvc,total, deducted, updated_balance) 

            cursor.execute("""UPDATE customers SET balance = %s WHERE user_id = %s""", (updated_balance,user_in_session))

            cursor.execute("""INSERT INTO payment_methods (user_id, card_number, card_holder_name, expiry_date, cvc) VALUES (%s, %s, %s, %s, %s);""", (user_in_session, ccNumber, ccName, ccExp, ccCvc))
            #Get payment method id after inserting the payment method
            payment_med_id = cursor.lastrowid
            cursor.execute("""INSERT INTO payments (user_id, amount, payment_method_id, payment_date, status) VALUES (%s, %s, %s ,%s,'Completed');""", (user_in_session,total,payment_med_id,order_date))
            #Get payment id after inserting the payment
            payment_id = cursor.lastrowid
                
            cursor.execute("""INSERT INTO orders (user_id, order_date, payment_id, shippment_id) VALUES (%s, %s, %s, %s);""", (user_in_session,order_date,payment_id,shipment_id[0]))

            order_id = cursor.lastrowid
            cursor.execute("""INSERT INTO receipts (order_id, gst) VALUES (%s, '0.15');""", (order_id,))

            for sku, item_details in subscription.items():
                pro_id = item_details['prod_id']
                quantity = item_details['quantity']
                sub_type = item_details['sub_type']

                cursor.execute("""INSERT INTO order_lines (order_id, product_id, product_quantity) VALUES (%s, %s, %s);""", (order_id, pro_id, quantity))

                # Retrieve the current stock for the product
                cursor.execute("""SELECT quantity FROM stock WHERE product_id = %s""", (pro_id, ))
                current_stock = cursor.fetchone()[0]

                # Subtract the quantity from the current stock
                new_stock = float(current_stock) - float(quantity)

                cursor.execute("UPDATE stock SET quantity = %s WHERE product_id = %s", (new_stock, pro_id))

            # get max sub record id
            cursor.execute('select max(record_id) from subscription_records')
            max_id = cursor.fetchone()
            if max_id[0] is None:
                new_id = 1
            else:
                new_id = 1 + max_id[0]


            if sub_type != 'One-off':
                cursor.execute('''insert into subscription_records values (%s,%s,%s,%s,%s,%s,%s,%s)''',(new_id,user_in_session,order_date,pro_id,quantity,sub_type,payment_med_id,'Active'))    
                
            session.pop('subscription', None)

            return redirect(url_for('order_confirmation'))    
        


        elif request.method == 'POST':
            #form is empty

            error = 'Please complete all the details!' 


        return render_template('checkout-product.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart, shipping_cost=shipping_cost, balance=balance, error=error)
    
        
    else:

        session.pop('subscription', None)
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

#sub pay ends

#account subscription
@app.route('/acc-checkout-subscription/<sku1>',methods=['get','post'])
def acc_checkout_subscription(sku1):


    role = session.get('role')  
    user_in_session = session.get('user_id') 
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    cart = session.get('cart', {})
    cart = session.get('subscription', {})

    cursor=getCursor()
    cursor.execute('select city from accounts where user_id=%s ', (user_in_session,))
    depot_id = cursor.fetchone()
    if request.args.get('msg1'):
        msg1 = request.args.get('msg1')
    else: 
        msg1 = ''

    if 'loggedin' in session:
        if request.method == "GET" :
            cursor.execute('select balance from accounts where user_id=%s ',(user_in_session,))
            balance = cursor.fetchone()
            return render_template('account_holder-checkout_subscription.html',msg1=msg1,balance=balance,sub = session['subscription'],sku1=sku1,depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart)

            # # get subscription type

            # cursor=getCursor()
            # cursor.execute('select city from customers where user_id=%s ', (user_in_session,))
            # depot_id = cursor.fetchone()

            # cursor.execute('select shippment_price from shippments where depot_id=%s',(depot_id[0],))
            # ship_cost = cursor.fetchone()

            # # get promotion info



            # cursor.execute('''select p.*, b.box_name,pt.discount 
            #                 from products as p
            #                 join boxes as b on p.SKU= b.SKU 
            #                 join promotion_types as pt on p.promotion_type_id = pt.promotion_type_id 
            #                 where p.SKU=%s''',(sku1,))
            # product_info = cursor.fetchone()
            # current_price = float(product_info[2])*float(product_info[8])*float(quantity)

            # # return render_template('test.html')
            # return render_template('checkout-subscription.html',msg1=msg1,sub_type=sub_type,current_price=current_price,product_info=product_info,sku1=sku1,quantity=quantity,depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart)
        else:
            # get balance 
            cursor=getCursor()
            cursor.execute('select balance from accounts where user_id=%s ',(user_in_session,))
            balance = cursor.fetchone()

            cursor.execute('select credit_limit_monthly from accounts where user_id=%s',(user_in_session,))
            credit = cursor.fetchone()
            if 'subscription' not in session:
                session['subscription'] = {}
            subscription = session['subscription']
            # if sku in session
            if sku1 in subscription:
                return render_template('account_holder-checkout_subscription.html',credit=credit,msg1=msg1,balance=balance,sub = session['subscription'],sku1=sku1,depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart)

            else:
                sub_type=request.form['sub_type']
                quantity=request.form['quantity1']
                sku_chosen = sku1
                cursor=getCursor()
                cursor.execute('select city from accounts where user_id=%s ', (user_in_session,))
                depot_id = cursor.fetchone()

                cursor.execute('select shippment_price from shippments where depot_id=%s',(depot_id[0],))
                ship_cost = cursor.fetchone()

                # get promotion info
                cursor.execute('''select p.*, b.box_name,pt.discount 
                                from products as p
                                join boxes as b on p.SKU= b.SKU 
                                join promotion_types as pt on p.promotion_type_id = pt.promotion_type_id 
                                where p.SKU=%s''',(sku_chosen,))
                product_info = cursor.fetchone()
                current_price = float(product_info[2])*float(product_info[8])

                current_total = current_price + ship_cost[0]
                subscription[sku_chosen] = {
                    'name':product_info[7],
                    'sub_type':sub_type,
                    'price':current_price,
                    'quantity':quantity,
                    'prod_id':product_info[0],
                    'ship':ship_cost[0]
                }
                session['subscription'] = subscription
                session.modified = True



            # # get coupon code info
            # couponcode1=request.form['couponcode']            
    
            # if couponcode1:
            #     cursor.execute('select * from coupons where coupon_code = %s and depot_id = %s',(couponcode1,depot_id[0],))
            #     coupon_info = cursor.fetchone()
            #     if coupon_info and current_total>coupon_info[3]:
            #         new_total = current_total - coupon_info[2]

            #     else:
            #         msg1 = 'Coupon code is not valid for your order'
                        
            return render_template('account_holder-checkout_subscription.html',credit=credit,msg1=msg1,balance=balance,sub = session['subscription'],sku1=sku1,depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart)
    else:

        session.pop('subscription', None)
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))
    
#acc process subsccription
@app.route('/acc/paysubscription', methods=["GET","POST"])
def acc_paysubscription():
    role = session.get('role')  
    user_in_session = session.get('user_id')
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    # Get subscription content from session
    cart = session.get('cart', {})
    subscription = session.get('subscription', {})

    location = session.get('location')
    shipping_cost = get_shipping(location)
    user_id = request.args.get('user_id')
    credit = get_credit(user_in_session)
   
    balance = get_balance_acc(user_in_session)
    shipment_id = get_shipment(location)

    error = ''
    cursor=getCursor()

    cursor.execute("""SELECT * FROM 
    payment_methods WHERE user_id = %s""", (user_in_session,))
    paymentMethod = cursor.fetchall()
    print(paymentMethod)


    if 'loggedin' in session: 

        if request.method == "POST": 

            
            order_date = datetime.now().date()
            total = Decimal(request.form.get('total', '0.00'))
              
            balance = balance if balance else [Decimal('0.00')]
            credit = credit if credit else [Decimal('0.00')]

            # Convert balance and credit to Decimal
            balance_amount = Decimal(balance[0])
            credit_amount = Decimal(credit[0])

            positive_balance = abs(balance_amount)
            #Calculate the current balance
            updated_balance = -(positive_balance + total)

            if paymentMethod:

                
                if total + positive_balance > credit_amount:

                    error = "Insufficient balance. Please top up your account or request an increase in your limit."
    
                    
                elif total + positive_balance <= credit_amount:
                   
                    cursor.execute("""UPDATE accounts SET balance = %s WHERE user_id = %s""", (updated_balance,user_in_session))

                    cursor.execute("""SELECT payment_method_id FROM 
                    payment_methods WHERE user_id = %s""", (user_in_session,))

                    payment_med_id = cursor.fetchone()
                    cursor.execute("""INSERT INTO payments (user_id, amount, payment_method_id, payment_date, status) VALUES (%s, %s, %s ,%s,'Completed');""", (user_in_session,total,payment_med_id[0],order_date))

                   #Get payment id after inserting the payment
                    payment_id = cursor.lastrowid
                    cursor.execute("""INSERT INTO orders (user_id, order_date, payment_id, shippment_id) VALUES (%s, %s, %s, %s);""", (user_in_session,order_date,payment_id,shipment_id[0]))

                    order_id = cursor.lastrowid

                    cursor.execute("""INSERT INTO receipts (order_id, gst) VALUES (%s, '0.15');""", (order_id,))

                    for sku, item_details in subscription.items():
                        pro_id = item_details['prod_id']
                        quantity = item_details['quantity']

                        cursor.execute("""INSERT INTO order_lines (order_id, product_id, product_quantity) VALUES (%s, %s, %s);""", (order_id, pro_id, quantity))

                        # Retrieve the current stock for the product
                        cursor.execute("""SELECT quantity FROM stock WHERE product_id = %s""", (pro_id, ))
                        current_stock = cursor.fetchone()[0]

                        # Subtract the quantity from the current stock
                        new_stock = float(current_stock) - float(quantity)

                        cursor.execute("UPDATE stock SET quantity = %s WHERE product_id = %s", (new_stock, pro_id))
                        sub_type = item_details['sub_type']

                    # get max sub record id
                    cursor.execute('select max(record_id) from subscription_records')
                    max_id = cursor.fetchone()
                    if max_id[0] is None:
                        new_id = 1
                    else:
                        new_id = 1 + max_id[0]


                    if sub_type != 'One-off':
                        cursor.execute('''insert into subscription_records values (%s,%s,%s,%s,%s,%s,%s,%s)''',(new_id,user_in_session,order_date,pro_id,float(quantity),sub_type,payment_med_id[0],'Active'))    
                        
                    
                    session.pop('cart', None)

                    print("Payment")
                    return redirect(url_for('order_confirmation'))
              
            else:
             
                cursor.execute("""UPDATE accounts SET balance = %s WHERE user_id = %s""", (updated_balance,user_in_session))

                cursor.execute("""INSERT INTO payment_methods (user_id, card_number, card_holder_name, expiry_date, cvc) VALUES (%s,'', '', '', '');""", (user_in_session,))
                #Get payment method id after inserting the payment method
                payment_med_id = cursor.lastrowid

                cursor.execute("""INSERT INTO payments (user_id, amount, payment_method_id, payment_date, status) VALUES (%s, %s, %s ,%s,'Completed');""", (user_in_session,total,payment_med_id,order_date))

                #Get payment id after inserting the payment
                payment_id = cursor.lastrowid
                cursor.execute("""INSERT INTO orders (user_id, order_date, payment_id, shippment_id) VALUES (%s, %s, %s, %s);""", (user_in_session,order_date,payment_id,shipment_id[0]))

                order_id = cursor.lastrowid
                cursor.execute("""INSERT INTO receipts (order_id, gst) VALUES (%s, '0.15');""", (order_id,))

                for sku, item_details in subscription.items():
                    pro_id = item_details['prod_id']
                    quantity = item_details['quantity']

                    cursor.execute("""INSERT INTO order_lines (order_id, product_id, product_quantity) VALUES (%s, %s, %s);""", (order_id, pro_id, quantity))

                    # Retrieve the current stock for the product
                    cursor.execute("""SELECT quantity FROM stock WHERE product_id = %s""", (pro_id, ))
                    current_stock = cursor.fetchone()[0]

                    # Subtract the quantity from the current stock
                    new_stock = float(current_stock) - float(quantity)

                    cursor.execute("UPDATE stock SET quantity = %s WHERE product_id = %s", (new_stock, pro_id))
                # get max sub record id
                cursor.execute('select max(record_id) from subscription_records')
                max_id = cursor.fetchone()
                if max_id[0] is None:
                    new_id = 1
                else:
                    new_id = 1 + max_id[0]


                if sub_type != 'One-off':
                    cursor.execute('''insert into subscription_records values (%s,%s,%s,%s,%s,%s,%s,%s)''',(new_id,user_in_session,order_date,pro_id,float(quantity),sub_type,payment_med_id[0],'Active'))    
                        
                    
                session.pop('cart', None)

                return redirect(url_for('order_confirmation'))

    
        else:

            return render_template('account_holder-checkout_subscription.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart, shipping_cost=shipping_cost, balance=balance, error=error, credit=credit)

        
    else:

        session.pop('cart', None)
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))

@app.route('/cus/checkout-product', methods=["GET","POST"])
def cus_product_checkout():

    role = session.get('role')  
    user_in_session = session.get('user_id')
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    # Get cart content from session
    cart = session.get('cart', {})
    location = session.get('location')
    shipping_cost = get_shipping(location)
    user_id = request.args.get('user_id')
    balance = get_balance(user_in_session)
  

    shipment_id = get_shipment(location)


    error = ''
    cursor=getCursor()


    cursor.execute("""SELECT * FROM 
    payment_methods WHERE user_id = %s""", (user_id,))
    paymentMethod = cursor.fetchone()
    if 'loggedin' in session: 

        
        if request.method == "POST" and 'ccName' in request.form and 'ccNumber' in request.form and 'ccExp' in request.form and 'ccCvc' in request.form and 'total' in request.form and 'deducted' in request.form and 'updated_balance' in request.form:
            
            ccName = request.form['ccName']
            ccNumber = request.form['ccNumber']
            ccExp = request.form['ccExp']
            ccCvc = request.form['ccCvc']
            total = request.form['total']
            deducted = request.form['deducted']
            updated_balance = request.form['updated_balance']
            order_date = datetime.now().date()

            cursor.execute("""SELECT * FROM payment_methods WHERE card_number = %s""", (ccNumber,))

            checkccNumber = cursor.fetchone()

            if checkccNumber: 

                if ccExp != checkccNumber[4]:
                    error = "Your expired date does not match your credit card!"
                    return render_template('customer-checkout_product.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart, shipping_cost=shipping_cost, balance=balance, error=error)
                elif ccCvc != checkccNumber[5]:
                    error = "Your cvc does not match your credit card!"
                    return render_template('customer-checkout_product.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart, shipping_cost=shipping_cost, balance=balance, error=error)
                
                else:

                    print(ccName, ccNumber, ccExp, ccCvc,total, deducted, updated_balance) 

                    cursor.execute("""UPDATE customers SET balance = %s WHERE user_id = %s""", (updated_balance,user_in_session))
                    
                    cursor.execute("""INSERT INTO payments (user_id, amount, checkccNumber[0], payment_date, status) VALUES (%s, %s, %s ,%s,'Completed');""", (user_in_session,total,payment_med_id,order_date))
                    #Get payment id after inserting the payment
                    payment_id = cursor.lastrowid
                    
                    cursor.execute("""INSERT INTO orders (user_id, order_date, payment_id, shippment_id) VALUES (%s, %s, %s, %s);""", (user_in_session,order_date,payment_id,shipment_id[0]))

                    order_id = cursor.lastrowid

                    cursor.execute("""INSERT INTO receipts (order_id, gst) VALUES (%s, '0.15');""", (order_id,))

                    for sku, item_details in cart.items():
                        pro_id = item_details['pro_id']
                        quantity = item_details['quantity']

                        cursor.execute("""INSERT INTO order_lines (order_id, product_id, product_quantity) VALUES (%s, %s, %s);""", (order_id, pro_id, quantity))

                        # Retrieve the current stock for the product
                        cursor.execute("""SELECT quantity FROM stock WHERE product_id = %s""", (pro_id, ))
                        current_stock = cursor.fetchone()[0]

                        # Subtract the quantity from the current stock
                        new_stock = current_stock - quantity

                        cursor.execute("UPDATE stock SET quantity = %s WHERE product_id = %s", (new_stock, pro_id))

                    
                    session.pop('cart', None)

                    return redirect(url_for('order_confirmation'))
            else: 

                print(cart)

                print(ccName, ccNumber, ccExp, ccCvc,total, deducted, updated_balance) 

                cursor.execute("""UPDATE customers SET balance = %s WHERE user_id = %s""", (updated_balance,user_in_session))

                cursor.execute("""INSERT INTO payment_methods (user_id, card_number, card_holder_name, expiry_date, cvc) VALUES (%s, %s, %s, %s, %s);""", (user_in_session, ccNumber, ccName, ccExp, ccCvc))
                #Get payment method id after inserting the payment method
                payment_med_id = cursor.lastrowid
                cursor.execute("""INSERT INTO payments (user_id, amount, payment_method_id, payment_date, status) VALUES (%s, %s, %s ,%s,'Completed');""", (user_in_session,total,payment_med_id,order_date))
                #Get payment id after inserting the payment
                payment_id = cursor.lastrowid
                
                cursor.execute("""INSERT INTO orders (user_id, order_date, payment_id, shippment_id) VALUES (%s, %s, %s, %s);""", (user_in_session,order_date,payment_id,shipment_id[0]))

                order_id = cursor.lastrowid
                cursor.execute("""INSERT INTO receipts (order_id, gst) VALUES (%s, '0.15');""", (order_id,))

                for sku, item_details in cart.items():
                    pro_id = item_details['pro_id']
                    quantity = item_details['quantity']

                    cursor.execute("""INSERT INTO order_lines (order_id, product_id, product_quantity) VALUES (%s, %s, %s);""", (order_id, pro_id, quantity))

                    # Retrieve the current stock for the product
                    cursor.execute("""SELECT quantity FROM stock WHERE product_id = %s""", (pro_id, ))
                    current_stock = cursor.fetchone()[0]

                    # Subtract the quantity from the current stock
                    new_stock = current_stock - quantity

                    cursor.execute("UPDATE stock SET quantity = %s WHERE product_id = %s", (new_stock, pro_id))

                
                session.pop('cart', None)

                return redirect(url_for('order_confirmation'))    
        


        elif request.method == 'POST':
            #form is empty

            error = 'Please complete all the details!' 


        return render_template('customer-checkout_product.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart, shipping_cost=shipping_cost, balance=balance, error=error)
    
        
    else:

        session.pop('cart', None)
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))
    
    
@app.route('/acc/checkout-product', methods=["GET","POST"])
def acc_product_checkout():
    role = session.get('role')  
    user_in_session = session.get('user_id')
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    # Get cart content from session
    cart = session.get('cart', {})
    location = session.get('location')
    shipping_cost = get_shipping(location)
    user_id = request.args.get('user_id')
    credit = get_credit(user_in_session)
   
    balance = get_balance_acc(user_in_session)
    shipment_id = get_shipment(location)

    error = ''
    cursor=getCursor()

    cursor.execute("""SELECT * FROM 
    payment_methods WHERE user_id = %s""", (user_in_session,))
    paymentMethod = cursor.fetchall()
    print(paymentMethod)


    if 'loggedin' in session: 

        if request.method == "POST": 

            
            order_date = datetime.now().date()
            total = Decimal(request.form.get('total', '0.00'))
              
            balance = balance if balance else [Decimal('0.00')]
            credit = credit if credit else [Decimal('0.00')]

            # Convert balance and credit to Decimal
            balance_amount = Decimal(balance[0])
            credit_amount = Decimal(credit[0])

            positive_balance = abs(balance_amount)
            #Calculate the current balance
            updated_balance = balance_amount - total

            if paymentMethod:

                
                if total +  credit_amount < credit_amount:

                    error = "Insufficient balance. Please top up your account or request an increase in your limit."
    
                    
                else:
                   
                   cursor.execute("""UPDATE accounts SET balance = %s WHERE user_id = %s""", (updated_balance,user_in_session))

                   cursor.execute("""SELECT payment_method_id FROM 
                   payment_methods WHERE user_id = %s""", (user_in_session,))

                   payment_med_id = cursor.fetchone()
                   cursor.execute("""INSERT INTO payments (user_id, amount, payment_method_id, payment_date, status) VALUES (%s, %s, %s ,%s,'Completed');""", (user_in_session,total,payment_med_id[0],order_date))

                   #Get payment id after inserting the payment
                   payment_id = cursor.lastrowid
                   cursor.execute("""INSERT INTO orders (user_id, order_date, payment_id, shippment_id) VALUES (%s, %s, %s, %s);""", (user_in_session,order_date,payment_id,shipment_id[0]))

                   order_id = cursor.lastrowid

                   cursor.execute("""INSERT INTO receipts (order_id, gst) VALUES (%s, '0.15');""", (order_id,))

                   for sku, item_details in cart.items():
                        pro_id = item_details['pro_id']
                        quantity = item_details['quantity']

                        cursor.execute("""INSERT INTO order_lines (order_id, product_id, product_quantity) VALUES (%s, %s, %s);""", (order_id, pro_id, quantity))

                        # Retrieve the current stock for the product
                        cursor.execute("""SELECT quantity FROM stock WHERE product_id = %s""", (pro_id, ))
                        current_stock = cursor.fetchone()[0]

                        # Subtract the quantity from the current stock
                        new_stock = float(current_stock) - float(quantity)

                        cursor.execute("UPDATE stock SET quantity = %s WHERE product_id = %s", (new_stock, pro_id))

                    
                   session.pop('cart', None)

                   print("Payment")
                   return redirect(url_for('order_confirmation'))
              
            else:
             
                cursor.execute("""UPDATE accounts SET balance = %s WHERE user_id = %s""", (updated_balance,user_in_session))

                cursor.execute("""INSERT INTO payment_methods (user_id, card_number, card_holder_name, expiry_date, cvc) VALUES (%s,'', '', '', '');""", (user_in_session,))
                #Get payment method id after inserting the payment method
                payment_med_id = cursor.lastrowid

                cursor.execute("""INSERT INTO payments (user_id, amount, payment_method_id, payment_date, status) VALUES (%s, %s, %s ,%s,'Completed');""", (user_in_session,total,payment_med_id,order_date))

                #Get payment id after inserting the payment
                payment_id = cursor.lastrowid
                cursor.execute("""INSERT INTO orders (user_id, order_date, payment_id, shippment_id) VALUES (%s, %s, %s, %s);""", (user_in_session,order_date,payment_id,shipment_id[0]))

                order_id = cursor.lastrowid
                cursor.execute("""INSERT INTO receipts (order_id, gst) VALUES (%s, '0.15');""", (order_id,))

                for sku, item_details in cart.items():
                    pro_id = item_details['pro_id']
                    quantity = item_details['quantity']

                    cursor.execute("""INSERT INTO order_lines (order_id, product_id, product_quantity) VALUES (%s, %s, %s);""", (order_id, pro_id, quantity))

                    # Retrieve the current stock for the product
                    cursor.execute("""SELECT quantity FROM stock WHERE product_id = %s""", (pro_id, ))
                    current_stock = cursor.fetchone()[0]

                    # Subtract the quantity from the current stock
                    new_stock = current_stock - quantity

                    cursor.execute("UPDATE stock SET quantity = %s WHERE product_id = %s", (new_stock, pro_id))

                    
                session.pop('cart', None)

                return redirect(url_for('order_confirmation'))
            
            return render_template('account_holder-checkout_product.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart, shipping_cost=shipping_cost, balance=balance, error=error, credit=credit)
    
        else:

            return render_template('account_holder-checkout_product.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart, shipping_cost=shipping_cost, balance=balance, error=error, credit=credit)

        
    else:

        session.pop('cart', None)
        # If user is not logged in or doesn't have the required role, redirect to home page
        return redirect(url_for('logout'))


    


@app.route('/order-confirmation')
def order_confirmation():



    role = session.get('role')  
    user_in_session = session.get('user_id') 
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)
    cart = session.get('cart', {})

    order_date = datetime.now().date()
   

    if 'loggedin' in session: 

      
      cursor=getCursor()
      cursor.execute("""SELECT order_id FROM orders WHERE user_id = %s ORDER BY order_id DESC LIMIT 1;""", (user_in_session,))
      order_id = cursor.fetchone()
      
      return render_template('order_confirmation.html',depot_all=depot_all,user_info=user_info, role=role, user_in_session=user_in_session, cart=cart, order_id=order_id, order_date=order_date)
    
    else: 
      
      return redirect(url_for('logout'))

@app.route('/cart')
def cart():
 

    return render_template('cart.html')




@app.route('/contact-us', methods=["GET","POST"])
def contact():

    role = session.get('role')  
    user_in_session = session.get('user_id')

   
    depot_all= get_depot()
    user_info = get_user_info(user_in_session, role)

    cart = session.get('cart', {})

    location = session.get('location')

    recipients = ['hifreshharvestdelivery@outlook.com']


    if location is None:
        recipients = ['fresh_harvest@outlook.com']
    elif 'Auckland' in location:
        recipients = ['fresh_harvest@outlook.com']
    elif 'Christchurch' in location:
        recipients = ['fresh_harvest@outlook.com']
    elif 'Wellington' in location:
        recipients = ['fresh_harvest@outlook.com']
    elif 'Hamilton' in location:
        recipients = ['fresh_harvest@outlook.com']
    elif 'Invercargill' in location:
        recipients = ['fresh_harvest@outlook.com']
        


    if request.method == "POST":

        try:

            name = request.form['name']
            email = request.form['email']
            message = request.form['message']

            msg= Message(subject=f"Mail from {name}", body=f"Name: {name}\nE-mail: {email}\n{message}", sender=mail_username, recipients=recipients)
            mail.send(msg)
        
            return render_template('contact.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart,role=role, success = True)
        
        except Exception as e:
            
            redirect(url_for('error'))   
    

    return render_template('contact.html',depot_all=depot_all,user_info=user_info,user_in_session=user_in_session, cart=cart,role=role)

# http://localhost:5000/dashboard/ - this will be the dashboard page
@app.route('/dashboard')
def dashboard():
    # Check if user is loggedin
    if 'loggedin' in session:
        role = session.get('role')  # Get the user's role from the session
        # Redirect based on user's role
        if role == 1:
            return redirect(url_for('admin_dashboard'))  # Redirect to national manager dashboard
        elif role == 2:
            return redirect(url_for('manager_dashboard'))  # Redirect to local manager dashboard
        elif role == 3:
            return redirect(url_for('staff_dashboard'))   # Redirect to staff dashboard    
        elif role == 4:
            return redirect(url_for('homepage'))   # Redirect to the homepage for shopping purposes
        elif role == 5:
            return redirect(url_for('homepage'))   # Redirect to the homepage for shopping purposes
        else:
            # Redirect to the error page since the user's role doesn't match any predefined roles
            return redirect(url_for('error'))   
    # User is not loggedin redirect to error page
    return redirect(url_for('homepage'))

@app.route('/register', methods=['GET', 'POST'])
def register():
# Output message if something goes wrong...
    msg = ''
    cursor=getCursor()

    depot_all=get_depot()
    # Check if "username", "password1" and "email" POST requests exist (user submitted form)
    if request.method=='GET':
        cursor=getCursor()
        cursor.execute('select * from depots')
        depot_all=get_depot()
        return render_template('accounts/register.html', msg=msg,depot_all=depot_all) 
    else:
        role_type=request.form['role_type']
        if role_type=='Member':
            cursor=getCursor()
            cursor.execute('select * from depots')
            depot_all=cursor.fetchall()
            username = request.form['username']
            password1 = request.form['password1']
            password2 = request.form['password2']
            title=request.form['title']
            email = request.form['email']
            given_name = request.form['given_name']
            family_name = request.form['family_name']
            phone_number = request.form['phone']
            address= request.form['address']
            city=request.form['city']

            #Check if account exists using MySQL
            cursor = getCursor()
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            account = cursor.fetchone()
            cursor.execute('select * from customers where email=%s',(email,))
            email_all_customer = cursor.fetchone()
            cursor.execute('select * from accounts where email=%s',(email,))
            email_all_account = cursor.fetchone()
            if account:
                msg = 'Account/email already exists!'
                return render_template('accounts/register.html',msg=msg,depot_all=depot_all)

            elif email_all_customer or email_all_account:
                msg='Account/email already exists!'
                return render_template('accounts/register.html',msg=msg,depot_all=depot_all)

            elif password1 !=password2:
                msg="Password doesn't match"
                return render_template('accounts/register.html',msg=msg,depot_all=depot_all)

            else:
                hashed = hashing.hash_value(password1, salt='c639')
                cursor=getCursor()
                cursor.execute('select max(user_id) from users')
                max_user_id=cursor.fetchone()
                if max_user_id[0] is None:
                    new_userid=1
                else:
                    new_userid=max_user_id[0]+1
                cursor.execute('insert into users values (%s,%s,%s,%s,%s)',(new_userid,username,hashed,4,'Active',))
                #get new customerid
                cursor=getCursor()
                cursor.execute('insert into customers values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(new_userid,title,given_name,family_name,email,address,city,phone_number,0.00,'',))
                msg= 'You have successfully registered as a member!'
                return render_template('accounts/register.html',msg=msg,depot_all=depot_all)

@app.route('/404')
def error():
    cursor = getCursor()
    cursor.execute('SELECT * FROM depots')
    depot_all = cursor.fetchall()
    msg = request.args.get('msg', 'Page Not Found')  # Get the error message from query parameters
    return render_template('error.html', depot_all=depot_all, msg=msg)


# http://localhost:5000/logout/ - this will be the logout page
@app.route('/logout')
def logout():
    #remove session data
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('location', None)
    session.pop('cart', None)
    session.pop('subscription', None)

    #redict to login page
    return redirect(url_for('homepage'))


if __name__ == '__main__':
    app.run(debug=True)




# filter product category 
def filter_category(category, location):
    cursor = getCursor()
    ProductList = ()
    
    if category == 'all' or category == '':

       cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON pro.product_id = s.product_id WHERE pro.depot_id = %s AND pro.product_status =1 """, (location,))

       ProductList  = cursor.fetchall()

       return ProductList

    else:
        cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON pro.product_id = s.product_id WHERE pro.depot_id = %s AND pro.product_category_id = %s AND pro.product_status =1""", (location, category))

        ProductList  = cursor.fetchall()

        return  ProductList
    

def get_depot():

    cursor=getCursor()
    cursor.execute('select * from depots')
    depot_all=cursor.fetchall()

    return depot_all

def get_shipment(location):

    cursor=getCursor()
    location = session.get('location') 

    if 'Auckland' in location:
        cursor.execute("""SELECT shippment_id FROM shippments WHERE depot_id = 1""")
        shipment_id = cursor.fetchone()

    elif 'Christchurch' in location:
        cursor.execute("""SELECT shippment_id FROM shippments WHERE depot_id = 2""")
        shipment_id = cursor.fetchone()
    elif 'Wellington' in location:
        cursor.execute("""SELECT shippment_id FROM shippments WHERE depot_id = 3""")
        shipment_id = cursor.fetchone()
    elif 'Hamilton' in location:
        cursor.execute("""SELECT shippment_id FROM shippments WHERE depot_id = 4""")
        shipment_id = cursor.fetchone()
    elif 'Invercargill' in location:
        cursor.execute("""SELECT shippment_id FROM shippments WHERE depot_id = 5""")
        shipment_id = cursor.fetchone()
    return shipment_id


        

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

@app.route('/add-to-cart', methods=["POST"])
def add_to_cart():
    if 'loggedin' in session:
        sku = request.form.get('sku')
        if 'cart' not in session:
            session['cart'] = {}
        cart = session['cart']
        if sku in cart:
            cart[sku]['quantity'] += 1
        else:
            product_details = get_product_details(sku)
            cart[sku] = {
                'name': product_details[1],
                'price': product_details[2] * product_details[17],
                'image_url': product_details[4],
                'quantity': 1,
                'stock': product_details[16],
                'unit': product_details[3],
                'pro_id': product_details[18]
            }
        session['cart'] = cart
        session.modified = True
        return jsonify({'success': True})
    else:
        return redirect(url_for('homepage'))
    
@app.route('/update-cart-quantity', methods=['POST'])
def update_cart_quantity():
    sku = request.form.get('sku')
    quantity = int(request.form.get('quantity'))
   
    cart = session.get('cart', {})

    if sku in cart:
        cart[sku]['quantity'] = quantity
        session['cart'] = cart
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))


@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    sku = request.form.get('sku')
    if 'cart' in session:
        cart = session['cart']
        if sku in cart:
            del cart[sku]
            session['cart'] = cart
            session.modified = True
            return jsonify({'success': True})
    return redirect(url_for('homepage'))


 

def get_product_details(sku):

    location = session.get('location') 
  
    cursor=getCursor()

    if 'Auckland' in location:

    
        cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, pro.product_id FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.product_status =1 AND pro.depot_id = '1'""", (sku,)) 

        product = cursor.fetchone()
    elif 'Christchurch' in location:

    
        cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, pro.product_id FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.product_status =1 AND pro.depot_id = '2'""", (sku,)) 

        product = cursor.fetchone()
    elif 'Wellington' in location:

        cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, pro.product_id FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.product_status =1 AND pro.depot_id = '3'""", (sku,)) 

        product = cursor.fetchone()
    elif 'Hamilton' in location:

    
        cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, pro.product_id FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.product_status =1 AND pro.depot_id = '4'""", (sku,)) 

        product = cursor.fetchone()
    elif 'Invercargill' in location:

        cursor.execute("""SELECT pro.SKU, p.product_name, pro.product_price, u.unit_name, p.pic, pro.product_category_id, b.pic, b.box_name, us.unit_name, p.product_des, b.box_des, p.product_origins, b.product_origins, g.giftcard_name, g.pic, g.giftcard_des, s.quantity, prom.discount, pro.product_id FROM products AS pro LEFT JOIN product AS p ON p.SKU = pro.SKU LEFT JOIN units AS u ON u.unit_id = p.unit LEFT JOIN boxes AS b ON b.SKU = pro.SKU LEFT JOIN units AS us ON us.unit_id = b.unit LEFT JOIN giftcards AS g ON pro.SKU = g.SKU LEFT JOIN stock AS s ON s.product_id = pro.product_id LEFT JOIN promotion_types AS prom ON pro.promotion_type_id = prom.promotion_type_id WHERE pro.SKU = %s AND pro.product_status =1 AND pro.depot_id = '5'""", (sku,)) 

        product = cursor.fetchone()

    return product


 


def get_shipping(location):
  
    cursor=getCursor()
    if 'Auckland' in location:
        cursor.execute("""SELECT s.shippment_price FROM shippments AS s WHERE s.depot_id = 1""")
        shipping = cursor.fetchone()

    elif 'Christchurch' in location:
        cursor.execute("""SELECT s.shippment_price FROM shippments AS s WHERE s.depot_id = 2""")
        shipping = cursor.fetchone()
    elif 'Wellington' in location:
        cursor.execute("""SELECT s.shippment_price FROM shippments AS s WHERE s.depot_id = 3""")
        shipping = cursor.fetchone()
    elif 'Hamilton' in location:
        cursor.execute("""SELECT s.shippment_price FROM shippments AS s WHERE s.depot_id = 4""")
        shipping = cursor.fetchone()
    elif 'Invercargill' in location:
        cursor.execute("""SELECT s.shippment_price FROM shippments AS s WHERE s.depot_id = 5""")
        shipping = cursor.fetchone()
    
    return shipping


def get_balance(user_id):
    cursor=getCursor()
    cursor.execute("""SELECT balance FROM customers WHERE user_id = %s""", (user_id,))

    balance = cursor.fetchone()
    return balance

def get_credit(user_id):
    cursor=getCursor()
    cursor.execute("""SELECT credit_limit_monthly FROM accounts WHERE user_id = %s""", (user_id,))

    credit = cursor.fetchone()
    return credit

def get_balance_acc(user_id):
    cursor=getCursor()
    cursor.execute("""SELECT balance FROM accounts WHERE user_id = %s""", (user_id,))

    balance = cursor.fetchone()
    return balance