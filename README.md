# requirements.txt
APScheduler==3.10.4
blinker==1.8.2
click==8.1.7
colorama==0.4.6
Flask==3.0.3
Flask-Hashing==1.1
Flask-Mail==0.10.0
itsdangerous==2.2.0
Jinja2==3.1.4
MarkupSafe==2.1.5
mysql-connector-python==8.4.0
python-dateutil==2.9.0.post0
pytz==2024.1
schedule==1.2.1
six==1.16.0
tzdata==2024.1
tzlocal==5.2
Werkzeug==3.0.3


# Refund Functionality
## User Story:
As Fresh Harvest Delivery, we aim to introduce innovative features to our system to enhance the user experience and differentiate our platform from competitors.

## Description:
We have implemented a comprehensive refund system that enables customers and account holders to request refunds for unsatisfactory purchases or issues with their orders. This functionality streamlines the refund process and provides clear guidance for users and managers.

## How It Works:

### Accessing the Refund Request Form:
Customers and account holders can easily access the refund request form from the "Request Refund" submenu under the "Refund" menu within the sidebar of their account dashboard.

### Completing the Refund Request Form:
The refund request form, also known as the return authorization form, includes fields for relevant information such as the customer/account holder's name and an order ID input field. Users can select the order for which they want to request a refund.
Upon selecting the order, the details of the order, including the order number and ordered items, along with details of each item, are displayed. Users can specify the quantity of each item they want to return and provide a reason for the refund request.
Clear guidance is provided within the form on how to fill out each field, ensuring ease of use for users.
Submission and Validation:

After submitting the form, the system validates the entered information. For example, it ensures that the total quantity to be returned is not zero or exceeds the total quantity ordered. Additionally, it checks that the reason input does not exceed 255 characters.

Users receive confirmation upon successful submission of their refund request.

### Checking Request Status:
Users can monitor the status of their refund requests from the sidebar under the "Refund" menu. They can view a list of all their requests and filter them by status (e.g., pending, rejected, approved).

A "Check Details" option allows users to review the specifics of each request, including the requester's details, submission date, reason for the request, status, and product details.

### Manager Approval Process:
Local managers/national managers have access to a dedicated interface for managing refund requests from the sidebar of their dashboard.

The interface displays a list of all refund requests, including details such as the order number, request date, and request status.
Managers can review the details provided by customers/account holders and determine whether the request meets the criteria for approval.

If a request is valid and meets the approval criteria, managers can approve it with a simple click. Upon approval, the system automatically initiates the refund process and updates the status to "Approved."

Requests that do not meet the approval criteria can be rejected by managers. Upon rejection, the status is updated to "Rejected."

### Outcome and Reflection in Customer/Account Holder Dashboard:
Once a refund request is processed by a manager (approved or rejected), customers/account holders can view the outcome from the "Request Status" submenu under "Refund" in the sidebar of their dashboard.

Approved refunds are reflected as a balance in the customer/account holder's dashboard, ensuring transparency and visibility of the refunded amount.

## Benefits:
Streamlines the refund process for users, improving customer satisfaction.
Provides managers with an efficient interface for reviewing and processing refund requests.
Enhances transparency and accountability by enabling users to track the status of their refund requests.
Elevates the overall user experience and sets our platform apart from competitors.

# Reload Pythonanywhere Web
Please reload the PythonAnywhere webpage after the max_user_connections issue occurs.
Login URL: https://www.pythonanywhere.com/login
Login name: flashnzproject2
Login password: 7mar2024istherightbirthday

# Daily fresh of subscriptions
Admin/manager/staff needs to click the fresh button in 'recent orders' section in dashboard to fresh the repeated subscription orders

# Order Assignment
managers can assign tasks to staff in order assignment page by choosing the staff name in dropdown list. they can only assign packing tasks to staff with packing responsibility, and same to delivery responsibility. 
National manager can only assign packing/delivery tasks to the staff with that responsibility in the order depot.
Staff can change order assignment when the 'begin' button is available, when it shows as 'to start', it means the task is processing at other staff side who is with different responsiblity.

# Subscription
Customers can change subscription by changing product name and/or how often they want the box to be delivered. Customers can order new subscription, and in box page, they can choose 'one-off' and other options like 'weekly'. If customers choose 'one-off', it won't be shown in their subscriptions. Only other types of subscriptions can be seen in customer subscription page.
