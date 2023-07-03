import pandas as pd
from flask import Flask, session
# Server-side client to support larger data transfer
from flask_session import Session
from flask import (request,
                   redirect,
                   render_template)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import json
from os.path import join, dirname, realpath
from handlers.read_file import file_options
from handlers.graph_templates import *
import secrets

UPLOAD_FOLDER = join(dirname(realpath(__file__)), 'static/temp_files')
basedir = os.path.abspath(os.path.dirname(__file__))
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

app = Flask(__name__)

app.secret_key = secrets.token_bytes(16)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

Session(app)
db = SQLAlchemy(app)


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


# class ProjectTable(db.Model):
#     project_id = db.Column("project_id", db.Integer, primary_key=True)
#     date = db.Column("date", db.DateTime)
#     costs = db.Column("costs", db.Float)
#     sales = db.Column("sales", db.Float)
#     labor = db.Column("labor", db.Float)
#     materials = db.Column("materials", db.Float)
#
#     def __init__(self, date, costs, sales, labor, materials):
#         self.date = date
#         self.costs = costs
#         self.sales = sales
#         self.labor = labor
#         self.materials = materials


def createDataTable(user_id, table_name, table_obj, dates, costs, sales, labor, materials, perc_profit_col):
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

    # Create new project table
    # temp_table = db.Table(
    #     table_name,
    #     db.Column("project_id", db.Integer, primary_key=True),
    #     db.Column("date", db.DateTime),
    #     db.Column("costs", db.Float),
    #     db.Column("sales", db.Float),
    #     db.Column("labor", db.Float),
    #     db.Column("materials", db.Float),
    # )
    # temp_table = ProjectTable
    # temp_table.__tablename__ = table_name
    #
    # db.create_all()
    # # Add project data to table object
    # for i in range(table_obj.shape[0]):
    #     row = temp_table(date=table_obj.at[i, dates],
    #                      costs=table_obj.at[i, costs],
    #                      sales=table_obj.at[i, sales],
    #                      labor=table_obj.at[i, labor],
    #                      materials=table_obj.at[i, materials])
    #     db.session.add(row)
    #
    #     print(f"Added row: {len(temp_table.query.all())}")

    db.session.commit()


def save_only():
    data = session.get("preview_dataframe")
    user = session.get("account")

    pandas_df = data["dataframe"]
    costs = data["dashboard_config"]["fields"]["costs_field"]
    labor = data["dashboard_config"]["fields"]["labor_field"]
    materials = data["dashboard_config"]["fields"]["materials_field"]
    sales = data["dashboard_config"]["fields"]["sales_field"]
    dates = data["dashboard_config"]["fields"]["date_field"]
    perc_profit = data["dashboard_config"]["fields"]["perc_profit_field"]

    table_name = data["dashboard_config"]["project_name"]
    cleaned_name = str(user["user_id"]) + '_' + table_name.replace(" ", "_")

    createDataTable(user_id=user["user_id"],
                    table_name=cleaned_name,
                    table_obj=pandas_df,
                    dates=dates,
                    costs=costs,
                    sales=sales,
                    labor=labor,
                    materials=materials,
                    perc_profit_col=perc_profit)


@app.route('/create_db', methods=["GET"])
def create_db():
    db.create_all()
    admin = (UserLogin(user_email="demo@learningn.com", user_pwd="ai4all"))
    db.session.add(admin)
    db.session.commit()

    return f"Database created and added admin: {admin}"


@app.route('/view_db', methods=["GET"])
def view_db():
    schema = db.metadata.tables.keys()
    return f"{schema}"


@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        print(f"Email: {email}\nPassword: {password}")
        try:
            current_user = UserLogin.query.filter_by(user_email=email).all()[0]
            logged_pwd = current_user.user_pwd
            user_id = current_user.user_id
            print(logged_pwd, user_id)
            if password != logged_pwd:
                message = "Incorrect password."
                return render_template('login.html', message=message)
            session["account"] = {"email": email, "user_id": user_id}
            return redirect('home')
        except Exception as e:
            print(e)
            message = "Account not found."
            return render_template('login.html', message=message)

    return render_template('login.html')


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("user-email")
        pwd = request.form.get("user-pwd")
        if "@" not in email:
            message = "Not a valid email."
            return render_template('register.html', message=message)
        if len(pwd) < 8:
            message = "Password must be at least 8 characters."
            return render_template('register.html', message=message)
        new_user = (UserLogin(user_email=email, user_pwd=pwd))
        db.session.add(new_user)
        db.session.commit()
        print(f"New user added:\nEmail: {email}\nPassword: {pwd}")
        return redirect('/')
    return render_template('register.html')


@app.route('/home', methods=["GET", "POST"])
def home():
    user_info = session.get("account")
    if request.method == "POST":
        print("Here")
        for k, v in request.form.items():
            print(k, ": ", v)
        table_name = request.form.get("project_button")
        print(table_name)
        db_row = UserTables.query.filter_by(user_id=user_info["user_id"], table_name=table_name).first()
        print(db_row)
        json_obj = db_row.data
        col_mapping = db_row.col_mapping
        print(col_mapping)
        json_col_mapping = json.loads(col_mapping)
        data = session["preview_dataframe"]
        data["dataframe"] = pd.read_json(json_obj)
        data["dashboard_config"] = {"project_name": table_name,
                                    "fields": json_col_mapping,
                                    }
        return redirect('/active-dashboard')

    user_datasets = UserTables.query.filter_by(user_id=user_info["user_id"]).all()
    if len(user_datasets) > 0:
        user_tables = [table.table_name for table in user_datasets]
        return render_template('home.html', user=user_info, projects=user_tables)
    return render_template('home.html', user=user_info, projects=None)


@app.route('/data-import', methods=["GET", "POST"])
def data_import():
    user_info = session.get("account")
    if request.method == "POST":
        file = request.files["file"]

        ext = file.filename.split('.')[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return render_template('import_data.html', message="File type not supported.")

        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        if ext == 'csv':
            dataframe, fields = file_options.load_csv(save_path)
            session["preview_dataframe"] = {"dataframe": dataframe,
                                            "fields": fields}
        if ext == 'xlsx':
            dataframe, fields = file_options.load_excel(save_path)
            session["preview_dataframe"] = {"dataframe": dataframe,
                                            "fields": fields}
        return redirect('/preview-data')
    return render_template('import_data.html', user=user_info)


@app.route('/preview-data', methods=["GET", "POST"])
def preview_data():
    if request.method == "POST":
        title = request.form.get("data-title")
        date_col = request.form.get("date-column")
        sales_col = request.form.get("sales-column")
        costs_col = request.form.get("costs-column")
        labor_col = request.form.get("labor-column")
        materials_col = request.form.get("materials-column")
        perc_profit_col = request.form.get("perc-profit-column")
        data = session.get("preview_dataframe")
        data["dashboard_config"] = {"project_name": title,
                                    "fields": {"date_field": date_col,
                                               "sales_field": sales_col,
                                               "costs_field": costs_col,
                                               "labor_field": labor_col,
                                               "materials_field": materials_col,
                                               "perc_profit_field": perc_profit_col},
                                    }

        action = request.form["submit-btn"]
        if action == "Save & Analyze":
            return redirect("/active-dashboard", code=307)
        else:
            save_only()
            return redirect('/home')
    data = session.get("preview_dataframe")
    username = session.get("account")
    preview_dataframe = data["dataframe"]
    table = create_table(preview_dataframe.loc[:100])
    return render_template('preview_data.html', data=data, table=table, user=username)


@app.route('/active-dashboard', methods=["GET", "POST"])
def active_dashboard():
    data = session.get("preview_dataframe")
    user = session.get("account")

    pandas_df = data["dataframe"]
    costs = data["dashboard_config"]["fields"]["costs_field"]
    labor = data["dashboard_config"]["fields"]["labor_field"]
    materials = data["dashboard_config"]["fields"]["materials_field"]
    sales = data["dashboard_config"]["fields"]["sales_field"]
    dates = data["dashboard_config"]["fields"]["date_field"]
    perc_profit = data["dashboard_config"]["fields"]["perc_profit_field"]

    try:
        pandas_df = clean_data(pandas_df, date_field=dates, labor_field=labor, materials_field=materials)
        table_name = data["dashboard_config"]["project_name"]
        cleaned_name = str(user["user_id"]) + '_' + table_name.replace(" ", "_")

        total_sales_kpi = sum(pandas_df[sales])
        total_sales_kpi = '${:,.2f}'.format(round(total_sales_kpi, 2))
        bar = create_bar_plot(pandas_df, costs, labor, materials)
        ml_graph, summary_stats = anomaly_detection(pandas_df, columns={"perc_profit": perc_profit,
                                                                        "date": dates,
                                                                        "sales": sales,
                                                                        "labor": labor,
                                                                        "materials": materials})
        line = create_line_plot(pandas_df, dates, sales)
        table = create_table(pandas_df.loc[:100])
        session["dashboard_objects"] = {"kpis": [total_sales_kpi, summary_stats],
                                        "visuals": {"bar": bar,
                                                    "line": line,
                                                    "table": table,
                                                    "ml_graph": ml_graph}}
        visual_objects = session.get("dashboard_objects")
    except Exception as e:
        print(e)
        return redirect('/preview-data')

    if request.method == "POST":
        createDataTable(user_id=user["user_id"],
                        table_name=cleaned_name,
                        table_obj=pandas_df,
                        dates=dates,
                        costs=costs,
                        sales=sales,
                        labor=labor,
                        materials=materials,
                        perc_profit_col=perc_profit)

    return render_template('active_dashboard.html', data=data, user=user, objects=visual_objects)


if __name__ == '__main__':
    app.run()
