"""Dash App."""

import dash
import dash_bootstrap_components as dbc
from dash import Dash

app = Dash(__name__,
           use_pages=True,
           pages_folder="pages",
           external_stylesheets=[dbc.themes.BOOTSTRAP])


app.layout = dbc.Container([
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Overview", href="/overview")),
            dbc.NavItem(dbc.NavLink("Session", href="/session")),
            dbc.NavItem(dbc.NavLink("Personas", href="/personas")),
            dbc.NavItem(dbc.NavLink("Mood", href="/mood")),
            dbc.NavItem(dbc.NavLink("Raw Tables", href="/")),
        ],
        brand="void-walker 🚶",
        color="dark",
        dark=True,
        className="mb-4"
    ),
    dash.page_container
], fluid=True)
