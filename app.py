from flask import Flask, session
# Server-side client to support larger data transfer
from flask_session import Session
from handlers import database
from flask import (request,
                   redirect,
                   render_template)
from werkzeug.utils import secure_filename
import os
from os.path import join, dirname, realpath
from handlers.data_handling import file_options, clean_data
from handlers.graph_templates import *
from handlers.models import *
import secrets

UPLOAD_FOLDER = join(dirname(realpath(__file__)), 'static/temp_files')
basedir = os.path.abspath(os.path.dirname(__file__))
ALLOWED_EXTENSIONS = ['csv', 'xlsx']

app = Flask(__name__)

app.secret_key = secrets.token_bytes(16)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

Session(app)
database.init_app(app)


class CurrentData:
    def __init__(self):
        self.table_name = None
        # self.perc_profit = None
        self.dates = None
        self.sales = None
        self.materials = None
        self.labor = None
        self.costs = None
        self.pandas_df = None

    def extract_data(self, data):
        self.pandas_df = data["dataframe"]
        self.costs = data["dashboard_config"]["fields"]["costs_field"]
        self.labor = data["dashboard_config"]["fields"]["labor_field"]
        self.materials = data["dashboard_config"]["fields"]["materials_field"]
        self.sales = data["dashboard_config"]["fields"]["sales_field"]
        self.dates = data["dashboard_config"]["fields"]["date_field"]
        # self.perc_profit = data["dashboard_config"]["fields"]["perc_profit_field"]
        self.table_name = data["dashboard_config"]["project_name"]

    def update_percent_profit(self):
        try:
            self.pandas_df[self.sales] = pd.to_numeric(self.pandas_df[self.sales], errors="ignore")
            self.pandas_df[self.costs] = pd.to_numeric(self.pandas_df[self.costs], errors="ignore")
            self.pandas_df["profit"] = self.pandas_df[self.sales] - self.pandas_df[self.costs]
            self.pandas_df["percent_profit"] = (self.pandas_df["profit"] / self.pandas_df[self.sales]) * 100
        except Exception as e:
            print(e)


def saveData(overwrite=True):
    data = session.get("preview_dataframe")
    user = session.get("account")

    data_obj = CurrentData()

    # Pass data to
    data_obj.extract_data(data)
    data_obj.pandas_df = clean_data(data_obj.pandas_df,
                                    date_field=data_obj.dates,
                                    labor_field=data_obj.labor,
                                    materials_field=data_obj.materials)
    data_obj.update_percent_profit()

    final_data = createDataTable(user_id=user["user_id"],
                                 table_name=data_obj.table_name,
                                 table_obj=data_obj.pandas_df,
                                 dates=data_obj.dates,
                                 costs=data_obj.costs,
                                 sales=data_obj.sales,
                                 labor=data_obj.labor,
                                 materials=data_obj.materials,
                                 get_name=True)

    if not overwrite:
        return final_data


@app.route('/create_db', methods=["GET"])
def create_db():
    createDB()
    return f"Database created"


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
        registerUser(email=email, pwd=pwd)
        print(f"New user added:\nEmail: {email}\nPassword: {pwd}")
        return redirect('/')
    return render_template('register.html')


@app.route('/home', methods=["GET", "POST"])
def home():
    user_info = session.get("account")
    if request.method == "POST":
        action = request.form.get("project_button")

        if action.startswith("delete_"):
            table_name = action[7:]
            deleteTable(user_id=user_info["user_id"], table_name=table_name)
            print(f'Deleted project: {table_name}')
            return redirect('/home')

        if action.startswith("edit_"):
            table_name = action[5:]
            print(f'Editing: {table_name}')
            return redirect('/home')

        if action == "Add record":
            print("Adding record")
            table_name = request.form.get("table-selection")
            date = request.form.get("add-record-date")
            sales = request.form.get("add-record-sales")
            materials = request.form.get("add-record-materials")
            labor = request.form.get("add-record-labor")
            costs = request.form.get("add-record-costs")

            addRecord(user_id=user_info["user_id"],
                      table_name=table_name,
                      date=date,
                      sales=sales,
                      materials=materials,
                      labor=labor,
                      costs=costs)

            return redirect('/home')

        table_name = action
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
        user_tables = [[table.table_name, table.last_updated] for table in user_datasets]
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
    username = session.get("account")
    messages = None
    if request.method == "POST":
        title = request.form.get("data-title")
        date_col = request.form.get("date-column")
        sales_col = request.form.get("sales-column")
        costs_col = request.form.get("costs-column")
        labor_col = request.form.get("labor-column")
        materials_col = request.form.get("materials-column")
        # perc_profit_col = request.form.get("perc-profit-column")
        data = session.get("preview_dataframe")
        data["dashboard_config"] = {"project_name": title,
                                    "fields": {"date_field": date_col,
                                               "sales_field": sales_col,
                                               "costs_field": costs_col,
                                               "labor_field": labor_col,
                                               "materials_field": materials_col,
                                               },
                                    }

        action = request.form["submit-btn"]
        if action == "Save & Analyze":
            try:
                table_name = saveData(overwrite=False)
                print(table_name)
                db_row = UserTables.query.filter_by(user_id=username["user_id"], table_name=table_name).first()
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
                return redirect("/active-dashboard")
            except Exception as e:
                message = "Please follow upload instructions. " \
                          "If the issue persists, report the following error to dev support:"
                messages = [message, e]
        else:
            try:
                saveData()
                return redirect('/home')
            except Exception as e:
                message = "Please follow upload instructions. " \
                          "If the issue persists, report the following error to dev support:"
                messages = [message, e]
    data = session.get("preview_dataframe")
    preview_dataframe = data["dataframe"]
    table = create_table(preview_dataframe.loc[:100])
    return render_template('preview_data.html', data=data, table=table, user=username, messages=messages)


@app.route('/active-dashboard', methods=["GET", "POST"])
def active_dashboard():
    user = session.get("account")

    if request.method == "POST":
        action = request.form.get("dashboard-action")
        if action.startswith("add_record_"):
            table_name = action.split("add_record_")[1]
            date = request.form.get("add-record-date")
            sales = request.form.get("add-record-sales")
            materials = request.form.get("add-record-materials")
            labor = request.form.get("add-record-labor")
            costs = request.form.get("add-record-costs")

            addRecord(user_id=user["user_id"],
                      table_name=table_name,
                      date=date,
                      sales=sales,
                      materials=materials,
                      labor=labor,
                      costs=costs)

            db_row = UserTables.query.filter_by(user_id=user["user_id"], table_name=table_name).first()
            # print(db_row)
            json_obj = db_row.data
            col_mapping = db_row.col_mapping
            # print(col_mapping)
            json_col_mapping = json.loads(col_mapping)
            data = session["preview_dataframe"]
            data["dataframe"] = pd.read_json(json_obj)
            data["dashboard_config"] = {"project_name": table_name,
                                        "fields": json_col_mapping,
                                        }
            return redirect('/active-dashboard')

    data = session.get("preview_dataframe")

    data_obj = CurrentData()
    data_obj.extract_data(data)
    data_obj.update_percent_profit()

    pandas_df = data_obj.pandas_df
    dates = data_obj.dates
    sales = data_obj.sales
    costs = data_obj.costs
    labor = data_obj.labor
    materials = data_obj.materials

    total_sales_kpi = sum(pandas_df[sales])
    total_sales_kpi = '${:,.2f}'.format(round(total_sales_kpi, 2))
    bar = create_bar_plot(pandas_df, costs, labor, materials)
    ml_graph, summary_stats = anomaly_detection(pandas_df, columns={"date": dates,
                                                                    "sales": sales,
                                                                    "labor": labor,
                                                                    "materials": materials,
                                                                    }
                                                )
    line = create_line_plot(pandas_df, dates, sales)
    table = create_table(pandas_df.loc[:100])
    session["dashboard_objects"] = {"kpis": [total_sales_kpi],
                                    "visuals": {"bar": bar,
                                                "line": line,
                                                "table": table,
                                                "ml_graph": ml_graph},
                                    "anomalies": {"stats": summary_stats}}
    visual_objects = session.get("dashboard_objects")

    return render_template('active_dashboard.html', data=data, user=user, objects=visual_objects)


if __name__ == '__main__':
    app.run()
