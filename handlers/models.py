from .database import db
import json


class UserLogin(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100))
    user_pwd = db.Column(db.String(100))

    def __init__(self, user_email, user_pwd):
        self.user_email = user_email
        self.user_pwd = user_pwd


class UserTables(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey(UserLogin.user_id))
    table_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    table_name = db.Column(db.String(100))
    data = db.Column(db.JSON)
    col_mapping = db.Column(db.JSON)

    def __init__(self, user_id, table_name, data, col_mapping):
        self.user_id = user_id
        self.table_name = table_name
        self.data = data
        self.col_mapping = col_mapping


def createDB():
    db.create_all()
    admin = (UserLogin(user_email="demo@learningn.com", user_pwd="ai4all"))
    db.session.add(admin)
    db.session.commit()


# =======================================================
# =======================================================

def registerUser(email=None, pwd=None):
    new_user = (UserLogin(user_email=email, user_pwd=pwd))
    db.session.add(new_user)
    db.session.commit()

def createDataTable(user_id,
                    table_name,
                    table_obj,
                    dates,
                    costs,
                    sales,
                    labor,
                    materials,
                    perc_profit_col):
    # Add table to UserTables (associate to user)
    table_obj = table_obj.to_json()
    col_mapping = {'date_field': f'{dates}',
                   'costs_field': f'{costs}',
                   'sales_field': f'{sales}',
                   'labor_field': f'{labor}',
                   'materials_field': f'{materials}',
                   'perc_profit_field': f'{perc_profit_col}'}

    col_mapping = json.dumps(col_mapping)

    userTable = UserTables(user_id=user_id, table_name=table_name, data=table_obj, col_mapping=col_mapping)
    db.session.add(userTable)
    db.session.commit()


def deleteTable(user_id=None, table_name=None):
    UserTables.query.filter_by(user_id=user_id, table_name=table_name).delete()
    db.session.commit()
