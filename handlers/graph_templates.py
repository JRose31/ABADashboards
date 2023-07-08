import plotly
import plotly.express as px
import plotly.graph_objs as go
from sklearn.ensemble import IsolationForest

import pandas as pd
import json
import numpy as np


def create_bar_plot(df, costs, labor, materials):
    df_agg = df[[costs, labor, materials]].sum()
    data = [
        go.Bar(
            x=df_agg.index,  # assign x as the dataframe column 'x'
            y=df_agg.values,
        )
    ]

    fig = go.Figure(data)

    fig.update_layout(
        yaxis_tickprefix='$',
        margin=dict(l=0, r=0, t=0, b=0),
    )

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON


def create_line_plot(df, x, y):
    df[x] = pd.to_datetime(df[x], errors="coerce")
    df = df.sort_values(by=x)
    data = [
        go.Scatter(
            x=df[x],  # assign x as the dataframe column 'x'
            y=df[y],
            mode="lines",
        )
    ]

    fig = go.Figure(data)

    fig.update_layout(
        yaxis_tickprefix='$',
        margin=dict(l=0, r=0, t=0, b=0))

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON


def create_table(df):
    data = [go.Table(header=dict(values=list(df.columns)),
                     cells=dict(values=df.transpose().values.tolist()),
                     hoverinfo='none')
            ]

    fig = go.Figure(data)

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        # style_cell={
        #     'overflow': 'hidden',
        #     'textOverflow': 'ellipsis',
        #     'maxWidth': 0,
        # }
    )

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON


def anomaly_detection(dat, columns, verbose=False):
    print("Data Type: ", type(dat))
    dat_col = dat[["percent_profit"]].copy()

    # Use Isolation Forest to identify anomalies
    clf = IsolationForest()
    clf.fit(dat_col)
    dat['scores'] = clf.score_samples(dat_col)
    dat['anomaly'] = False
    dat.loc[dat['scores'] < -.6, 'anomaly'] = True

    # Plot histograms
    fig1 = px.line(dat, x=columns["date"], y="percent_profit")
    fig2 = px.scatter(dat, x=columns["date"], y="percent_profit", color='anomaly',
                      hover_data=[columns["date"],
                                  columns["sales"],
                                  columns["labor"],
                                  columns["materials"],
                                  "percent_profit"])
    fig3 = go.Figure(data=fig1.data + fig2.data)
    fig3.update_layout(
        margin=dict(l=0, r=0, t=0, b=0))
    graphJSON = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)

    # Summary Stats for Anomalies
    low_anom = dat[(dat['anomaly'] == True) & (dat["percent_profit"] < dat["percent_profit"].median())]
    high_anom = dat[(dat['anomaly'] == True) & (dat["percent_profit"] >= dat["percent_profit"].median())]

    summary_stats = []
    section_prompt = f"Below are some details on your jobs that have unusually low percent profit:\n"
    stat_one = f"Average Sales Price: ${np.round(low_anom[columns['sales']].mean(), 2)}"
    stat_two = f"Average Labor Cost (Percent of Sales): {np.round(low_anom[columns['labor']].mean() / low_anom[columns['sales']].mean() * 100, 2)}%"
    stat_three = f"Average Paint Cost (Percent of Sales): {np.round(low_anom[columns['materials']].mean() / low_anom[columns['sales']].mean() * 100, 2)}%"

    section_one = [section_prompt, stat_one, stat_two, stat_three]
    summary_stats.append(section_one)

    # NOTE: Could add things like "Most of these jobs are interior cabinet jobs"

    section_prompt = f"\n Below are some details on your jobs that have unusually high percent profit:"
    stat_one = f"Average Sales Price: ${np.round(high_anom[columns['sales']].mean(), 2)}"
    stat_two = f"Average Labor Cost (Percent of Sales): {np.round(high_anom[columns['labor']].mean() / high_anom[columns['sales']].mean() * 100, 2)}%"
    stat_three = f"Average Paint Cost (Percent of Sales): {np.round(high_anom[columns['materials']].mean() / high_anom[columns['sales']].mean() * 100, 2)}%"

    section_two = [section_prompt, stat_one, stat_two, stat_three]
    summary_stats.append(section_two)

    return graphJSON, summary_stats
    # We can also have an option for them to look at the anomalies
    # if verbose:
    #     display(dat[dat['anomaly'] == True])
