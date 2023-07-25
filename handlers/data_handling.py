import pandas as pd
from handlers.models import createDataTable, addRecord, UserTables
import json


class file_options:
    def __init__(self):
        """Class Docs"""

    @staticmethod
    def load_csv(file):
        df = pd.read_csv(file)
        fields = df.columns
        dataframe = df.copy()
        return dataframe, fields

    @staticmethod
    def load_excel(file):
        df = pd.read_excel(file)
        fields = df.columns
        dataframe = df.copy()
        return dataframe, fields


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


def clean_data(data, date_field, labor_field, materials_field, costs_field, sales_field):
    print("Cleaning Data...")
    # Change date to datetime
    data[date_field] = pd.to_datetime(data[date_field], format='%Y-%m-%d %H:%M:%S')

    data[[labor_field, materials_field, costs_field, sales_field]] = data[[labor_field, materials_field, costs_field, sales_field]].astype(float)

    # Fill in materials with average
    data[materials_field] = data[materials_field].fillna(data[materials_field].mean())

    # Fill in labor with average?
    data[labor_field] = data[labor_field].fillna(data[labor_field].mean())

    # Fill in everything else with 0
    data = data.fillna(0)

    # Sort data frame based on date
    data = data.sort_values(date_field)

    # Create numerical data for future analyses
    data["Date Numeric"] = pd.to_numeric(data[date_field])
    print("Cleaning complete.")
    return data


def saveData(session, overwrite=True):
    data = session.get("preview_dataframe")
    user = session.get("account")

    data_obj = CurrentData()

    # Pass data to
    data_obj.extract_data(data)
    data_obj.pandas_df = clean_data(data_obj.pandas_df,
                                    date_field=data_obj.dates,
                                    labor_field=data_obj.labor,
                                    materials_field=data_obj.materials,
                                    costs_field=data_obj.costs,
                                    sales_field=data_obj.sales)
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


def processNewRecord(request, user_id, table_name):
    date = request.form.get("add-record-date")
    sales = request.form.get("add-record-sales")
    materials = request.form.get("add-record-materials")
    labor = request.form.get("add-record-labor")
    costs = request.form.get("add-record-costs")

    addRecord(user_id=user_id,
              table_name=table_name,
              date=date,
              sales=sales,
              materials=materials,
              labor=labor,
              costs=costs)


def getRequestedData(user_id, table_name):
    db_row = UserTables.query.filter_by(user_id=user_id, table_name=table_name).first()

    data = db_row.data
    col_mapping = db_row.col_mapping
    col_mapping = json.loads(col_mapping)

    return data, col_mapping
