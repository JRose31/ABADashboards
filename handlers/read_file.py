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
