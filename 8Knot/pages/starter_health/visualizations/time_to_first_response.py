from dash import html, dcc, callback
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from dateutil.relativedelta import *  # type: ignore
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from queries.response_time_query import response_time_query as rtq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time
import datetime as dt
import math
import numpy as np

"""
Just do PRs for time to first response
pull from this new view explore_process_time

for design document each graphs visualization is thought out, database exists so not necessarily a need for design,
do example queries and say what tables we are using, class-model and database-model not necessary, a lot of things in design
doc don't apply so describing what someone would need to know to build the graph
so like details of what we are computing, how we query, and settle on type of visualization
"""


PAGE = "starter_health"
VIZ_ID = "time_to_first_response"

gc_time_to_first_response = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Time to First Response (Pull Requests)",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Time to first response is a metric which tracks the average time a 
                            contributors pull request sits before receiving interaction from a real-person maintainer 
                            for the project. The longer on average it takes for these requests to receive responses, the more
                            at risk a project becomes as contributors can become discouraged if feedback time is slow. A general target 
                            for most projects is to stay within a ~2-day response window. This metric is in particular very helpful 
                            for project maintainers so that they can ensure adequate response speed.
                            """
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",
                    placement="top",
                    is_open=False,
                ),
                dcc.Loading(
                    dcc.Graph(id=f"{PAGE}-{VIZ_ID}"),
                ),
                dbc.Form(
                    [
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for=f"date-interval-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id=f"date-interval-{PAGE}-{VIZ_ID}",
                                        options=[
                                            {
                                                "label": "Day",
                                                "value": "D",
                                            },
                                            {
                                                "label": "Week",
                                                "value": "W",
                                            },
                                            {"label": "Month", "value": "M"},
                                            {"label": "Year", "value": "Y"},
                                        ],
                                        value="M",
                                        inline=True,
                                    ),
                                    className="me-2",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "About Graph",
                                        id=f"popover-target-{PAGE}-{VIZ_ID}",
                                        color="secondary",
                                        size="sm",
                                    ),
                                    width="auto",
                                    style={"paddingTop": ".5em"},
                                ),
                            ],
                            align="center",
                        ),
                    ]
                ),
            ]
        ),
    ],
)


# formatting for graph generation
@callback(
    Output(f"popover-{PAGE}-{VIZ_ID}", "is_open"),
    [Input(f"popover-target-{PAGE}-{VIZ_ID}", "n_clicks")],
    [State(f"popover-{PAGE}-{VIZ_ID}", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open


# callback for prs over time graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)
def time_to_first_response_graph(repolist, interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=rtq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=rtq, repos=repolist)

    # data ready.
    start = time.perf_counter()
    logging.warning("TIME TO FIRST RESPONSE - START")

    # test if there is data
    if df.empty:
        logging.warning("TIME TO FIRST RESPONSE - NO DATA AVAILABLE")
        return nodata_graph

    # function for all data pre processing
    df_created = process_data(df, interval)

    fig = create_figure(df_created, interval)

    logging.warning(f"TIME_TO_FIRST_RESPONSE_VIZ - END - {time.perf_counter() - start}")
    return fig


def process_data(df: pd.DataFrame, interval):
    # convert to datetime objects with consistent column name
    # incoming value should be a posix integer.
    df["created"] = pd.to_datetime(df["created"], utc=True) #created in this case is actually closed, naming was kept as "created" due to how the query is structured

    # variable to slice on to handle weekly period edge case
    period_slice = None
    if interval == "W":
        # this is to slice the extra period information that comes with the weekly case
        period_slice = 10

    # get the average for response time in hours in the desired interval in pandas period format, sort index to order entries
    df_created = (
        df.groupby(by=df.created.dt.to_period(interval))["response_time"]
        .mean()
        .reset_index()
        .rename(columns={"created": "Date"})
    )

    # converts date column to a datetime object, converts to string first to handle period information
    # the period slice is to handle weekly corner case
    df_created["Date"] = pd.to_datetime(df_created["Date"].astype(str).str[:period_slice])

    return df_created


def create_figure(df_created: pd.DataFrame, interval):
    # time values for graph
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph geration
    fig = px.bar(
        df_created,
        x="Date",
        y="response_time",
        range_x=x_r,
        labels={"x": x_name, "y": "Average Response Time in Hours (PRs)"},
        color_discrete_sequence=[color_seq[3]],
    )
    fig.update_traces(hovertemplate=hover + "<br>Avg. Response Time in Hours: %{y}<br>")
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )
    fig.update_layout(
        xaxis_title="Date Request was Closed",
        yaxis_title="Average Response Time in Hours (PRs)",
        margin_b=40,
        margin_r=20,
        font=dict(size=14),
    )

    return fig



