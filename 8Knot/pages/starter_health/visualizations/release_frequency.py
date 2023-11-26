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
from queries.realease_frequency_query import release_frequency_query as rfq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time

PAGE = "starter_health"
VIZ_ID = "release_frequency"

gc_release_frequency = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Release Frequency",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Visualizes the number of releases for the project. \n
                            Releases are counted relative to a user-selected time window.
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

def rfq_graph(repolist,interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=rfq, repos=repolist)

    while df is None:
            time.sleep(1.0)
            df = cache.grabm(func=rfq, repos=repolist)

    # data ready.
    start = time.perf_counter()
    logging.warning("RELEASE_FREQUENCY_VIZ - START")

    # test if there is data
    if df.empty:
        logging.warning("RELEASE FREQUENCY - NO DATA AVAILABLE")
        return nodata_graph
    
    # function for all data pre processing
    df_released = process_data(df, interval) 

    fig = create_figure(df_released, interval)
        
    logging.warning(f"RELEASE_FREQUENCY_VIZ - END - {time.perf_counter() - start}")

    return fig

def process_data(df: pd.DataFrame, interval):

    df["r_date"] = pd.to_datetime(df["r_date"], utc=True)

    period_slice = None
    if interval == "W":
        period_slice = 10

    df_released = (
        df.groupby(by=df.r_date.dt.to_period(interval))["r_id"]
        .nunique()
        .reset_index()
    )

    df_released["r_date"] = pd.to_datetime(df_released["r_date"].astype(str).str[:period_slice])

    return df_released

def create_figure(df_released: pd.DataFrame, interval):
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph geration
    fig = px.bar(
        df_released,
        x="r_date",
        y="r_id",
        range_x=x_r,
        labels={"x": x_name, "y": "Releases"},
        color_discrete_sequence=[color_seq[3]],
    )
    fig.update_traces(hovertemplate=hover + "<br>Releases: %{y}<br>")
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )
    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Number of Releases",
        margin_b=40,
        margin_r=20,
        font=dict(size=14),
    )

    return fig