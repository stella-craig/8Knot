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
                    "Code Change Lines",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                                    """
                                    Like contribution information, quantifying the amount of actual physical code edits 
                                    is a great way to provide a general volume of project activity. Code change lines 
                                    is a metric which tracks the number of lines (added and removed) that are changed over 
                                    a specific period. This metric provides granularity that contributions does not as the 
                                    number of lines changed can be large or small within a single commit. Further filtration 
                                    of this metric can provide information about authors of bulk changes, type of changes, 
                                    and what the goal is of these changes (aggregating code lines for efficiency versus large 
                                    blocks of code to add additional features). 
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
    fig.update_layout(legend_title_text="Code Change Lines")

    return fig