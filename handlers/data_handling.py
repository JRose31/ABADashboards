import pandas as pd


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


def clean_data(data, date_field, labor_field, materials_field, ):
    print("Cleaning Data...")
    # Change date to datetime
    data[date_field] = pd.to_datetime(data[date_field], format='%Y-%m-%d %H:%M:%S')

    data[[labor_field, materials_field]] = data[[labor_field, materials_field]].astype(float)

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
