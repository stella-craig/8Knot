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
from queries.bus_factor_query import bus_factor_query as ctq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time
import datetime as dt

PAGE = "starter_health"
VIZ_ID = "bus_factor"



gc_bus_factor = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    #Name of the graph
                    "Bus Factor",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                           "The Bus Factor is the smallest number of people that make 50% of contributions."
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
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            "About Graph",
                                            id=f"popover-target-{PAGE}-{VIZ_ID}",
                                            color="secondary",
                                            size="sm",
                                        ),
                                    ],
                                    width="auto",
                                    style={"paddingTop": ".5em"},
                                ),
                            ],
                            align="right",
                            justify="between",
                        ),
                    ]
                ),
           ]
        )
    ],
)

# # callback for graph info popover
# @callback(
#     Output(f"popover-{PAGE}-{VIZ_ID}", "is_open"),
#     [Input(f"popover-target-{PAGE}-{VIZ_ID}", "n_clicks")],
#     [State(f"popover-{PAGE}-{VIZ_ID}", "is_open")],
# )
# def toggle_popover(n, is_open):
#     if n:
#         return not is_open
#     return is_open


# # callback for dynamically changing the graph title
# @callback(
#     Output(f"graph-title-{PAGE}-{VIZ_ID}", "children"),
#     Input(f"top-k-contributors-{PAGE}-{VIZ_ID}", "value"),
#     Input(f"action-type-{PAGE}-{VIZ_ID}", "value"),
# )
# def graph_title(k, action_type):
#     title = f"Top {k} Contributors by {action_type}"
#     return title


# # callback for contrib-importance graph
# @callback(
#     Output(f"{PAGE}-{VIZ_ID}", "figure"),
#     Output(f"check-alert-{PAGE}-{VIZ_ID}", "is_open"),
#     [
#         Input("repo-choices", "data"),
#         Input(f"action-type-{PAGE}-{VIZ_ID}", "value"),
#         Input(f"top-k-contributors-{PAGE}-{VIZ_ID}", "value"),
#         Input(f"patterns-{PAGE}-{VIZ_ID}", "value"),
#         Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "start_date"),
#         Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "end_date"),
#     ],
#     background=True,
# )


def create_top_k_cntrbs_graph(repolist, top_k):
    """
    Creates a graph showing the top K contributors by contribution percentage for the bus factor.
    
    Args:
        repolist ([str]): List of repository IDs to calculate the Bus Factor for.
        top_k (int): The number of top contributors to display.

    Returns:
        Plotly graph object if data is available, otherwise a warning log and None.
    """
    # Wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=ctq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=ctq, repos=repolist)

    start = time.perf_counter()
    logging.warning(f"{VIZ_ID} - START")

    # Test if there is data
    if df.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return None, False

    # Data preprocessing to calculate the contribution percentage
    df['contribution_percentage'] = (df['contributions'] / df['total_contributions']) * 100
    df.sort_values(by='contribution_percentage', ascending=False, inplace=True)

    # Creating the figure for the top K contributors
    fig = px.bar(
        df.head(top_k),
        x='cntrb_id',
        y='contribution_percentage',
        title=f'Top {top_k} Contributors by Contribution Percentage'
    )
    fig.update_layout(xaxis_title='Contributor ID', yaxis_title='Contribution Percentage (%)')

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    return fig, Fals


def create_figure(df: pd.DataFrame, repo_id):
    # Filter the DataFrame for a specific repository
    repo_df = df[df['repo_id'] == repo_id]

    # Calculate the contribution percentage of each contributor
    repo_df['contribution_percentage'] = (repo_df['contributions'] / repo_df['total_contributions']) * 100

    # Create a color sequence for the pie chart
    color_seq = px.colors.qualitative.Plotly

    # Create a pie chart
    fig = px.pie(
        repo_df,
        names='cntrb_id',  # Contributor ID
        values='contribution_percentage',  # Percentage of contributions
        color_discrete_sequence=color_seq,
        title=f'Contribution Percentage by Contributor for Repo {repo_id}'
    )

    # Update traces for hover information
    fig.update_traces(
        textinfo='percent+label',
        textposition='inside',
        hovertemplate='Contributor ID: %{label} <br>Contribution Percentage: %{value:.2f}%<extra></extra>',
    )

    # Add legend title
    fig.update_layout(legend_title_text='Contributor ID')

    return fig


#NEW
# Callback for the contrib-importance graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [Input("repo-choices", "value"),  # Assuming "repo-choices" is the ID for a component to choose repositories
     Input(f"top-k-contributors-{PAGE}-{VIZ_ID}", "value")],  # Assuming this is the ID for a component to choose the top_k value
)
def update_bus_factor_graph(repo_choices, top_k_contributors):
    if repo_choices is None or top_k_contributors is None:
        # If the inputs are not provided, return an empty graph or some default figure
        return go.Figure()

    # Assuming create_top_k_cntrbs_graph returns a figure and a boolean indicating if data is available
    fig, has_data = create_top_k_cntrbs_graph(repo_choices, top_k_contributors)

    # If has_data is False, you can decide to return an empty graph or some default figure
    if not has_data:
        return go.Figure()

    return fig