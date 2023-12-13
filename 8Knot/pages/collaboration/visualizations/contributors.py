from dash import html, dcc, callback
import dash
from dash import dcc
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from dateutil.relativedelta import *  # type: ignore
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from queries.contributors_query import contributors_query as ctq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time
import datetime as dt

PAGE = "collaboration"
VIZ_ID = "contributors"

gc_contributors = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Contributors",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                                        The contributors metric tracks the number of users (change requests, commit authors, reviewers) 
                                        that have been active on the project within the past 90 days. This can be useful to track to see 
                                        the ebbs and flows of a project and determine the overall trend. Projects which are trending 
                                        downward in contributor activity may be at higher risk.    
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
                                            {"label": "Week", "value": "W"},
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
        )
    ],
)

# callback for graph info popover
@callback(
    Output(f"popover-{PAGE}-{VIZ_ID}", "is_open"),
    [Input(f"popover-target-{PAGE}-{VIZ_ID}", "n_clicks")],
    [State(f"popover-{PAGE}-{VIZ_ID}", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open

@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)

def contributors_graph(repolist,interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=ctq, repos=repolist)

    while df is None:
            time.sleep(1.0)
            df = cache.grabm(func=ctq, repos=repolist)

    # data ready.
    start = time.perf_counter()
    logging.warning("CONTIBUTORS_VIZ - START")

    # test if there is data
    if df.empty:
        logging.warning("CONTRIBUTORS - NO DATA AVAILABLE")
        return nodata_graph
    
    # function for all data pre processing
    df_released = process_data(df, interval) 

    fig = create_figure(df_released, interval)
        
    logging.warning(f"CONTIBUTORS_VIZ - END - {time.perf_counter() - start}")

    return fig

def process_data(df: pd.DataFrame, interval):
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    #df.dropna(inplace=True)

    period_slice = None
    if interval == "W":
        period_slice = 10

    df_contributors = (
        df.groupby(by=df.created_at.dt.to_period(interval))["cntrb_id"]
        .nunique()
        .reset_index()
    )

    df_contributors["created_at"] = pd.to_datetime(df_contributors["created_at"].astype(str).str[:period_slice])

    return df_contributors

def create_figure(df_contributors: pd.DataFrame, interval):
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph geration
    fig = px.line(
        df_contributors,
        x="created_at",
        y="cntrb_id",
        range_x=x_r,
        labels={"x": x_name, "y": "Contibutors"},
        color_discrete_sequence=[color_seq[3]],
    )
    fig.update_traces(hovertemplate=hover + "<br>Contributors: %{y}<br>")
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )
    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Number of Contributos",
        margin_b=40,
        margin_r=20,
        font=dict(size=14),
    )

    return fig