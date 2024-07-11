from flask import Flask

app = Flask(__name__)

from app import views
from app import manager_views
from app import staff_views
from app import admin_views
from app import customer_views
from app import account_holder_views
