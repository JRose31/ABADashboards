import plotly
import plotly.express as px
import plotly.graph_objs as go
from sklearn.ensemble import IsolationForest

import pandas as pd
import json
import numpy as np


def create_bar_plot(df, costs, labor, materials):
    labor_costs = df[labor].sum()
    materials_costs = df[materials].sum()
    total_costs = df[costs].sum()
    addt_costs = total_costs - (labor_costs + materials_costs)

    labels = ['Labor', 'Materials', 'Additional']
    values = [labor_costs, materials_costs, addt_costs]

    data = [go.Pie(labels=labels, values=values, hole=.3, sort=False)]
    # Use `hole` to create a donut-like pie chart
    fig = go.Figure(data)

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            yanchor="top",
            y=.85,
            xanchor="left",
            x=-0.5
        )
    )

    fig.update_traces(marker=dict(colors=['royalblue', 'darkblue', 'lightgrey']))

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

    summary_stats = {"Low Percent Profit":{},
                     "High Percent Profit": {}}

    lpp_prompt = "Low Percent Profit:"
    lpp_stat_one_prompt = f"Avg Sales Price: "
    lpp_stat_one_metric = f"${np.round(low_anom[columns['sales']].mean(), 2)}"
    lpp_stat_two_prompt = f"Avg Labor Cost (% Sales): "
    lpp_stat_two_metric = f"{np.round(low_anom[columns['labor']].mean() / low_anom[columns['sales']].mean() * 100, 2)}%"
    lpp_stat_three_prompt = f"Avg Paint Cost (% Sales): "
    lpp_stat_three_metric = f"{np.round(low_anom[columns['materials']].mean() / low_anom[columns['sales']].mean() * 100, 2)}%"

    summary_stats["Low Percent Profit"]["Top Prompt"] = lpp_prompt

    summary_stats["Low Percent Profit"]["Stat (1) Prompt"] = lpp_stat_one_prompt
    summary_stats["Low Percent Profit"]["Stat (1) Metric"] = lpp_stat_one_metric

    summary_stats["Low Percent Profit"]["Stat (2) Prompt"] = lpp_stat_two_prompt
    summary_stats["Low Percent Profit"]["Stat (2) Metric"] = lpp_stat_two_metric

    summary_stats["Low Percent Profit"]["Stat (3) Prompt"] = lpp_stat_three_prompt
    summary_stats["Low Percent Profit"]["Stat (3) Metric"] = lpp_stat_three_metric

    # NOTE: Could add things like "Most of these jobs are interior cabinet jobs"

    hpp_prompt = f"High Percent Profit:"
    hpp_stat_one_prompt = f"Avg Sales Price: "
    hpp_stat_one_metric = f"${np.round(high_anom[columns['sales']].mean(), 2)}"
    hpp_stat_two_prompt = f"Avg Labor Cost (% Sales): "
    hpp_stat_two_metric = f"{np.round(high_anom[columns['labor']].mean() / high_anom[columns['sales']].mean() * 100, 2)}%"
    hpp_stat_three_prompt = f"Avg Paint Cost (% Sales): "
    hpp_stat_three_metric = f"{np.round(high_anom[columns['materials']].mean() / high_anom[columns['sales']].mean() * 100, 2)}%"

    summary_stats["High Percent Profit"]["Top Prompt"] = hpp_prompt

    summary_stats["High Percent Profit"]["Stat (1) Prompt"] = hpp_stat_one_prompt
    summary_stats["High Percent Profit"]["Stat (1) Metric"] = hpp_stat_one_metric

    summary_stats["High Percent Profit"]["Stat (2) Prompt"] = hpp_stat_two_prompt
    summary_stats["High Percent Profit"]["Stat (2) Metric"] = hpp_stat_two_metric

    summary_stats["High Percent Profit"]["Stat (3) Prompt"] = hpp_stat_three_prompt
    summary_stats["High Percent Profit"]["Stat (3) Metric"] = hpp_stat_three_metric

    return graphJSON, summary_stats
    # We can also have an option for them to look at the anomalies
    # if verbose:
    #     display(dat[dat['anomaly'] == True])
