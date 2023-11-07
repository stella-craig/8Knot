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
                            "Test stub for release frequency metric"
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

"""
# callback for dynamically changing the graph title
@callback(
    Output(f"graph-title-{PAGE}-{VIZ_ID}", "children"),
    Input(f"top-k-contributors-{PAGE}-{VIZ_ID}", "value"),
    Input(f"action-type-{PAGE}-{VIZ_ID}", "value"),
)
def graph_title(k, action_type):
    title = f"Top {k} Contributors by {action_type}"
    return title


# callback for contrib-importance graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    Output(f"check-alert-{PAGE}-{VIZ_ID}", "is_open"),
    [
        Input("repo-choices", "data"),
        Input(f"action-type-{PAGE}-{VIZ_ID}", "value"),
        Input(f"top-k-contributors-{PAGE}-{VIZ_ID}", "value"),
        Input(f"patterns-{PAGE}-{VIZ_ID}", "value"),
        Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "start_date"),
        Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "end_date"),
    ],
    background=True,
)
def create_top_k_cntrbs_graph(repolist, action_type, top_k, patterns, start_date, end_date):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=ctq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=ctq, repos=repolist)

    start = time.perf_counter()
    logging.warning(f"{VIZ_ID}- START")

    # test if there is data
    if df.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return nodata_graph, False

    # checks if there is a contribution of a specfic action type in repo set
    if not df["Action"].str.contains(action_type).any():
        return dash.no_update, True

    # function for all data pre processing
    df = process_data(df, action_type, top_k, patterns, start_date, end_date)

    fig = create_figure(df, action_type)

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    return fig, False


def process_data(df: pd.DataFrame, action_type, top_k, patterns, start_date, end_date):
    # convert to datetime objects rather than strings
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)

    # order values chronologically by created_at date
    df = df.sort_values(by="created_at", ascending=True)

    # filter values based on date picker
    if start_date is not None:
        df = df[df.created_at >= start_date]
    if end_date is not None:
        df = df[df.created_at <= end_date]

    # subset the df such that it only contains rows where the Action column value is the action type
    df = df[df["Action"].str.contains(action_type)]

    # option to filter out potential bots
    if patterns:
        # remove rows where login column value contains any keyword in patterns
        patterns_mask = df["login"].str.contains("|".join(patterns), na=False)
        df = df[~patterns_mask]

    # count the number of contributions for each contributor
    df = (df.groupby("cntrb_id")["Action"].count()).to_frame()

    # sort rows according to amount of contributions from greatest to least
    df.sort_values(by="cntrb_id", ascending=False, inplace=True)
    df = df.reset_index()

    # rename Action column to action_type
    df = df.rename(columns={"Action": action_type})

    # get the number of total contributions
    t_sum = df[action_type].sum()

    # index df to get first k rows
    df = df.head(top_k)

    # convert cntrb_id from type UUID to String
    df["cntrb_id"] = df["cntrb_id"].apply(lambda x: str(x).split("-")[0])

    # get the number of total top k contributions
    df_sum = df[action_type].sum()

    # calculate the remaining contributions by taking the the difference of t_sum and df_sum
    df = df.append({"cntrb_id": "Other", action_type: t_sum - df_sum}, ignore_index=True)

    return df
"""

def create_figure(df: pd.DataFrame, action_type):
    fig = px.scatter()
    """
    # create plotly express pie chart
    fig = px.pie(
        df,
        names="cntrb_id",  # can be replaced with login to unanonymize
        values=action_type,
        color_discrete_sequence=color_seq,
    )

    # display percent contributions and cntrb_id in each wedge
    # format hover template to display cntrb_id and the number of their contributions according to the action_type
    fig.update_traces(
        textinfo="percent+label",
        textposition="inside",
        hovertemplate="Contributor ID: %{label} <br>Contributions: %{value}<br><extra></extra>",
    )
    """
    # add legend title
    fig.update_layout(legend_title_text="Contributor ID")

    return fig
