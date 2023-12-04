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

PAGE = "collaboration"
VIZ_ID = "change_request_reviews"

gc_change_request_reviews = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Change Request Reviews",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                                    """
                                    This metric tracks the procedures for which change requests are reviewed 
                                    and processed on a project. This can relate to the quality of review being 
                                    completed on the change request (i.e. does the project have a formal contribution 
                                    procedures document, if not do they need one). The metric provides analysis of 
                                    how many change requests were reviewed, accepted, commented on and the number of 
                                    contributors providing reviews versus authoring change requests over a 90-day period. 
                                    The percentage of change requests who had at least one non-author reviewer are also 
                                    tracked. This metric can be useful, for example if a project becomes bogged down with 
                                    many rejected change requests. This puts a project at risk for stagnation as the deficit 
                                    grows between when contributors submit a request and when maintainers will get to it, 
                                    and it can also lead to maintainer burnout. Projects heavy in rejected requests may 
                                    benefit from providing more instructional information to their users to communicate 
                                    expectations for change request type.  
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
    fig.update_layout(legend_title_text="Change Request Reviews")

    return fig