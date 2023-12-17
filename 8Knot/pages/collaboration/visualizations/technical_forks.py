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
from queries.forks_query import forks_query as fkq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time
import datetime as dt

PAGE = "collaboration"
VIZ_ID = "technical_forks"

gc_technical_forks = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Technical Forks",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                                        Technical forks are instances of a code repository that an individual copies 
                                        over to their platform account to use and modify. Forking is an excellent tool 
                                        which allows contributors to experiment with project code without effecting the 
                                        main source. Forks can be contributing forks, or forks which regularly open change 
                                        requests, or non-contributing. The technical forks metric quantifies how many copies 
                                        of a project are in distribution at any certain time. This metric is useful to track 
                                        as it can indicate how users are interacting with the code using platform tools. 
                                        A high number of forks for example, while not necessarily a project risk, may result 
                                        in unnecessary difficulties in merging later if major conflicting contributions 
                                        are made on different contributing forks without communication. 
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

# def forks_graph(repolist,interval):
#     # wait for data to asynchronously download and become available.
#     cache = cm()
#     df = cache.grabm(func=fkq, repos=repolist)
#     while df is None:
#             time.sleep(1.0)
#             df = cache.grabm(func=fkq, repos=repolist)

#     # data ready.
#     start = time.perf_counter()
#     logging.warning("FORKS_VIZ - START")

#     # test if there is data
#     if df.empty:
#         logging.warning("FORKS - NO DATA AVAILABLE")
#         return nodata_graph
    
#     # function for all data pre processing
#     df_created = process_data(df, interval) 

#     fig = create_figure(df_created, interval)
        
#     logging.warning(f"CONTIBUTORS_VIZ - END - {time.perf_counter() - start}")
#     return fig

def forks_graph(repolist,interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    dataframes = []

    for repo in repolist:
        df = cache.grabm(func=fkq, repos=[repo])
        while df is None:
                time.sleep(1.0)
                df = cache.grabm(func=fkq, repos=[repo])
                break
        dataframes.append(df)

    # data ready.
    start = time.perf_counter()
    logging.warning("FORKS_VIZ - START")

    new_df = pd.concat(dataframes, ignore_index=True)

    # test if there is data
    if new_df.empty:
        logging.warning("FORKS - NO DATA AVAILABLE")
        return nodata_graph
    
    # function for all data pre processing
    df_created = process_data(new_df, interval) 

    fig = create_figure(df_created, interval)
        
    logging.warning(f"CONTIBUTORS_VIZ - END - {time.perf_counter() - start}")
    return fig


# def process_data(df: pd.DataFrame, interval):
#     df["created"] = pd.to_datetime(df["created"], utc=True)

#     period_slice = None
#     if interval == "W":
#         # this is to slice the extra period information that comes with the weekly case
#         period_slice = 10

#     df_created = (
#         df.groupby(by=df.created.dt.to_period(interval))["id"]
#         .nunique()
#         .cumsum()
#         .reset_index()
#         .rename(columns={"created": "Date"})
#     )

#     df_created["Date"] = pd.to_datetime(df_created["Date"].astype(str).str[:period_slice])

#     return df_created

def process_data(df: pd.DataFrame, interval):
    df["created"] = pd.to_datetime(df["created"], utc=True)
    df.sort_values(by='created', inplace=True)

    period_slice = None
    if interval == "W":
        period_slice = 10

    df_created = (
        df.groupby(df.created.dt.to_period(interval))["id"]
        .count()
        .cumsum()
        .reset_index()
        .rename(columns={"created": "Date", "id": "Total Forks"})
    )

    df_created["Date"] = pd.to_datetime(df_created["Date"].astype(str).str[:period_slice])

    return df_created



def create_figure(df_created: pd.DataFrame, interval):
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph geration
    fig = px.line(
        df_created,
        x="Date",
        y="Total Forks",
        range_x=x_r,
        labels={"x": x_name, "y": "Forks"},
        color_discrete_sequence=[color_seq[3]],
    )
    fig.update_traces(hovertemplate=hover + "<br>Forks: %{y}<br>")
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )
    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Forks",
        margin_b=40,
        margin_r=20,
        font=dict(size=14),
    )

    return fig