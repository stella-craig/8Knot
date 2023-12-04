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
    fig.update_layout(legend_title_text="Technical Forks")

    return fig