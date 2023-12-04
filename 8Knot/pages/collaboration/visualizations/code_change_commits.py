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
VIZ_ID = "code_change_commits"

gc_code_change_commits = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Code Change Commits",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                                    """
                                    Code change commits track, per 90-day periods, the number of commits per week, 
                                    the percentage of weeks with at least code commit, and the percentage of repositories 
                                    with at least one commit ​(Metrics and Metric Models, 2023)​. This is a useful metric 
                                    to analyze how active the coding community is on a project. Projects with waning 
                                    activity are potentially at risk. This metric provides information similar to the 
                                    contributors metric in that it seeks to quantify project activity, but it is more tailor 
                                    focused on commits to the repositories themselves than the individual user interaction 
                                    with the project (i.e. comments, reviews).  
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

def create_figure(df: pd.DataFrame, action_type):
    fig = px.scatter()
    fig.update_layout(legend_title_text="Code Change Commits")

    return fig