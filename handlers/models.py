from .database import db
import json
import pandas as pd


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
                    get_name=False):
    # Check if table name already exists
    existing_tables = UserTables.query.filter_by(user_id=user_id, table_name=table_name).all()
    print(len(existing_tables))
    if len(existing_tables) > 0:
        # Get all duplicate named tables
        all_tables = UserTables.query.filter_by(user_id=user_id).all()
        duplicate_tables = [table.table_name for table in all_tables if table.table_name.startswith(table_name)]
        latest_version = 0
        for table in duplicate_tables:
            try:
                version = int(table[-3:].replace("(", "").replace(")",""))
                if version > latest_version:
                    latest_version = version
            except:
                pass
        table_name = table_name+f" ({latest_version+1})"
        print(f"Copy created {table_name}")

    # Add table to UserTables (associate to user)
    table_obj = table_obj.to_json()
    col_mapping = {'date_field': f'{dates}',
                   'costs_field': f'{costs}',
                   'sales_field': f'{sales}',
                   'labor_field': f'{labor}',
                   'materials_field': f'{materials}', }
    # 'perc_profit_field': f'{perc_profit_col}'}

    col_mapping = json.dumps(col_mapping)

    userTable = UserTables(user_id=user_id, table_name=table_name, data=table_obj, col_mapping=col_mapping)
    db.session.add(userTable)
    db.session.commit()

    if get_name:
        return table_name


def addRecord(user_id, table_name, date, sales, materials, labor, costs):
    row = UserTables.query.filter_by(user_id=user_id, table_name=table_name).first()
    current_df = pd.read_json(row.data)
    print(f"Old shape of dataframe: {current_df.shape}...")
    col_mapping_dict = json.loads(row.col_mapping)
    new_record = {
        col_mapping_dict["date_field"]: pd.to_datetime(date),
        col_mapping_dict["sales_field"]: float(sales),
        col_mapping_dict["materials_field"]: float(materials),
        col_mapping_dict["labor_field"]: float(labor),
        col_mapping_dict["costs_field"]: float(costs),
    }

    # current_df = current_df.append(new_record)
    current_df = pd.concat([current_df, pd.DataFrame([new_record])], ignore_index=True)
    print(f"New shape of dataframe: {current_df.shape}...")

    table_obj = current_df.to_json()
    row.data = table_obj
    db.session.commit()

    # print(f"Current Table Object: {current_df.head()}")
    # print("=====================\n=====================")
    # print(f"Col Mapping Dictionary: {col_mapping_dict}")
    # print("=====================\n=====================")
    print(f"Added data:{date, sales, materials, labor, costs}")


def deleteTable(user_id=None, table_name=None):
    UserTables.query.filter_by(user_id=user_id, table_name=table_name).delete()
    db.session.commit()
