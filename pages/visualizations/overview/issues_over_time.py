from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash import callback
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from pages.utils.graph_utils import get_graph_time_values
from pages.utils.job_utils import nodata_graph
from queries.issues_query import issues_query as iq
from cache_manager.cache_manager import CacheManager as cm
import io
import time

gc_issues_over_time = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4(
                    "Issues Over Time",
                    className="card-title",
                    style={"text-align": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody("Information on overview graph 3"),
                    ],
                    id="overview-popover-3",
                    target="overview-popover-target-3",  # needs to be the same as dbc.Button id
                    placement="top",
                    is_open=False,
                ),
                dcc.Loading(
                    dcc.Graph(id="issues-over-time"),
                ),
                dbc.Form(
                    [
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for="issue-time-interval",
                                    width="auto",
                                    style={"font-weight": "bold"},
                                ),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id="issue-time-interval",
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
                                        id="overview-popover-target-3",
                                        color="secondary",
                                        size="sm",
                                    ),
                                    width="auto",
                                    style={"padding-top": ".5em"},
                                ),
                            ],
                            align="center",
                        ),
                    ]
                ),
            ]
        ),
    ],
    color="light",
)

# call backs for card graph 3 - Issue Over Time
@callback(
    Output("overview-popover-3", "is_open"),
    [Input("overview-popover-target-3", "n_clicks")],
    [State("overview-popover-3", "is_open")],
)
def toggle_popover_3(n, is_open):
    if n:
        return not is_open
    return is_open


# callback for issues over time graph
@callback(
    Output("issues-over-time", "figure"),
    [
        Input("repo-choices", "data"),
        Input("issue-time-interval", "value"),
    ],
    background=True,
)
def issues_over_time_graph(repolist, interval):

    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=iq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=iq, repos=repolist)

    # data ready.
    start = time.perf_counter()
    logging.debug("ISSUES OVER TIME - START")

    # test if there is data
    if df.empty:
        logging.debug("ISSUES OVER TIME - NO DATA AVAILABLE")
        return nodata_graph

    # convert to datetime objects rather than strings
    df["created"] = pd.to_datetime(df["created"], utc=True)
    df["closed"] = pd.to_datetime(df["closed"], utc=True)

    # order values chronologically by creation date
    df = df.sort_values(by="created", axis=0, ascending=True)

    # variable to slice on to handle weekly period edge case
    period_slice = None
    if interval == "W":
        # this is to slice the extra period information that comes with the weekly case
        period_slice = 10

    # data frames for issues created, merged, or closed. Detailed description applies for all 3.

    # get the count of created issues in the desired interval in pandas period format, sort index to order entries
    created_range = (
        pd.to_datetime(df["created"]).dt.to_period(interval).value_counts().sort_index()
    )

    # converts to data frame object and creates date column from period values
    df_created = (
        created_range.to_frame().reset_index().rename(columns={"index": "Date"})
    )

    # converts date column to a datetime object, converts to string first to handle period information
    # the period slice is to handle weekly corner case
    df_created["Date"] = pd.to_datetime(
        df_created["Date"].astype(str).str[:period_slice]
    )

    # df for merged issues in time interval
    closed_range = (
        pd.to_datetime(df["closed"]).dt.to_period(interval).value_counts().sort_index()
    )
    df_closed = closed_range.to_frame().reset_index().rename(columns={"index": "Date"})
    df_closed["Date"] = pd.to_datetime(df_closed["Date"].astype(str).str[:period_slice])

    if interval == "M":
        df_created["Date"] = df_created["Date"].dt.strftime("%Y-%m-01")
        df_closed["Date"] = df_closed["Date"].dt.strftime("%Y-%m-01")
    elif interval == "Y":
        df_created["Date"] = df_created["Date"].dt.strftime("%Y-01-01")
        df_closed["Date"] = df_closed["Date"].dt.strftime("%Y-01-01")

    # first and last elements of the dataframe are the
    # earliest and latest events respectively
    earliest = df["created"].min()
    latest = max(df["created"].max(), df["closed"].max())

    # beginning to the end of time by the specified interval
    dates = pd.date_range(start=earliest, end=latest, freq="D", inclusive="both")

    # df for open issues for time interval
    df_open = dates.to_frame(index=False, name="Date")

    # aplies function to get the amount of open issues for each day
    df_open["Open"] = df_open.apply(lambda row: get_open(df, row.Date), axis=1)

    df_open["Date"] = df_open["Date"].dt.strftime("%Y-%m-%d")

    # time values for graph
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph generation
    fig = go.Figure()
    fig.add_bar(
        x=df_created["Date"],
        y=df_created["created"],
        opacity=0.75,
        hovertemplate=hover + "<br>Created: %{y}<br>" + "<extra></extra>",
        offsetgroup=0,
        name="Issues Created",
    )
    fig.add_bar(
        x=df_closed["Date"],
        y=df_closed["closed"],
        opacity=0.6,
        hovertemplate=hover + "<br>Closed: %{y}<br>" + "<extra></extra>",
        offsetgroup=1,
        name="Issues Closed",
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
        yaxis_title="Number of Issues",
        bargroupgap=0.1,
        margin_b=40,
    )
    fig.add_trace(
        go.Scatter(
            x=df_open["Date"],
            y=df_open["Open"],
            mode="lines",
            name="Issues Actively Open",
            hovertemplate="Issues Open: %{y}<br>%{x|%b %d, %Y} <extra></extra>",
        )
    )
    logging.debug(f"ISSUES_OVER_TIME_VIZ - END - {time.perf_counter() - start}")

    # df = px.data.iris()  # iris is a pandas DataFrame
    # fig = px.scatter(df, x="sepal_width", y="sepal_length")

    return fig


# for each day, this function calculates the amount of open issues
def get_open(df, date):

    # drop rows that are more recent than the date limit
    df_lim = df[df["created"] <= date]

    # drops rows that have been closed after date
    df_open = df_lim[df_lim["closed"] > date]

    # include issues that have not been close yet
    df_open = pd.concat([df_open, df_lim[df_lim.closed.isnull()]])

    # generates number of columns ie open issues
    num_open = df_open.shape[0]
    return num_open