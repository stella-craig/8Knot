from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

import visualization cards
from .visualizations.change_request_reviews import gc_change_request_reviews
from .visualizations.code_change_commits import gc_code_change_commits
from .visualizations.code_change_lines import gc_code_change_lines
from .visualizations.contributors import gc_contributors
from .visualizations.technical_forks import gc_technical_forks

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/collaboration")

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(gc_change_request_reviews, width=6),
                dbc.Col(gc_code_change_commits, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_code_change_lines, width=6),
                dbc.Col(gc_contributors, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_technical_forks, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
    ],
    fluid=True,
)
