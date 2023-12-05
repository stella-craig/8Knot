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

PAGE = "collaboration"
VIZ_ID = "code_change_lines"

gc_code_change_lines = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Code Lines Changed per Pull Request (PR)",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                                    """
                                    Code change lines is a metric which tracks the number of lines (added and removed) that are changed over 
                                    a specific period by pull request (PR) close date. This metric provides granularity that contributions
                                    does not as the number of lines changed can be large or small within a single commit. 
                                   """
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",  # needs to be the same as dbc.Button id
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

def code_change_lines_graph(repolist, interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=rtq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=rtq, repos=repolist)

    # data ready.
    start = time.perf_counter()
    logging.warning("CODE CHANGE LINES - START")

    # test if there is data
    if df.empty:
        logging.warning("CODE CHANGE LINES - NO DATA AVAILABLE")
        return nodata_graph

    # function for all data pre processing
    df_created, df_added, df_removed = process_data(df, interval)

    fig = create_figure(df_created, df_added, df_removed, interval)

    logging.warning(f"CODE_CHANGE_LINES_VIZ - END - {time.perf_counter() - start}")
    return fig

def process_data(df: pd.DataFrame, interval):
    # convert to datetime objects with consistent column name
    df["created"] = pd.to_datetime(df["created"], utc=True)

    # variable to slice on to handle weekly period edge case
    period_slice = None
    if interval == "W":
        # this is to slice the extra period information that comes with the weekly case
        period_slice = 10

    # group by the "created" date and sum the corresponding columns
    # borrowed from the pr_over_time.py
    df_created = (
        df.groupby(by=df.created.dt.to_period(interval))["total_lines_changed"]
        .sum()
        .reset_index()
        .rename(columns={"created": "Date"})
    )

    df_added = (
        df.groupby(by=df.created.dt.to_period(interval))["added"]
        .sum()
        .reset_index()
        .rename(columns={"created": "Date"})
    )

    df_removed = (
        df.groupby(by=df.created.dt.to_period(interval))["removed"]
        .sum()
        .reset_index()
        .rename(columns={"created": "Date"})
    )

    # converts date column to a datetime object, converts to string first to handle period information
    df_created["Date"] = pd.to_datetime(df_created["Date"].astype(str).str[:period_slice])
    df_added["Date"] = pd.to_datetime(df_added["Date"].astype(str).str[:period_slice])
    df_removed["Date"] = pd.to_datetime(df_removed["Date"].astype(str).str[:period_slice])

    return df_created, df_added, df_removed

def create_figure(df_created: pd.DataFrame, df_added: pd.DataFrame, df_removed: pd.DataFrame, interval):
    # time values for graph
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # borrowed this style of graphing from pr_over_time.py
    # graph generation
    fig = go.Figure()
    fig.add_bar( 
        x=df_created["Date"],
        y=df_created["total_lines_changed"],
        opacity=0.9,
        hovertemplate=hover + "<br>Total Lines Changed: %{y}<br>" + "<extra></extra>",
        offsetgroup=0,
        marker=dict(color=color_seq[3]),
        name="Total Lines Changed",
    )
    fig.add_bar( 
        x=df_added["Date"],
        y=df_added["added"],
        opacity=0.9,
        hovertemplate=hover + "<br>Lines Added: %{y}<br>" + "<extra></extra>",
        offsetgroup=1,
        marker=dict(color=color_seq[2]),
        name="Lines Added",
    )
    fig.add_bar(
        x=df_removed["Date"],
        y=df_removed["removed"],
        opacity=0.9,
        hovertemplate=[f"{hover}<br>Lines Removed: {val}<br><extra></extra>" for val in df_removed["removed"]],
        offsetgroup=1,
        base=df_added["added"],
        marker=dict(color=color_seq[1]),
        name="Lines Removed",
    )
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )
    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Code Changed Lines per PR",
        bargroupgap=0.1,
        margin_b=40,
        font=dict(size=14),
    )

    return fig

