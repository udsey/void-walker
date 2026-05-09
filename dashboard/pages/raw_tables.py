# raw_tables.py
import dash
from dash import dash_table, html
from dashboard.db import raw_map
from dashboard.styles import TABLE_STYLE

dash.register_page(__name__, path="/")

tables = {name: fn() for name, fn in raw_map.items()}

for name, df in tables.items():
    if "session_id" in df.columns:
        df["session_id"] = df["session_id"].apply(
            lambda x: f"[{x[:8]}...](/session?id={x})" if x else ""
        )

layout = html.Div([
    html.H1("void-walker raw"),
    *[
        html.Div([
            html.H3(name),
            dash_table.DataTable(
                id=f"{name.lower()}-table",
                data=df.to_dict("records"),
                columns=[
                    {"name": c, "id": c, "presentation": "markdown"} 
                    if c == "session_id" else {"name": c, "id": c}
                    for c in df.columns
                ],
                page_size=20,
                sort_action="native",
                filter_action="native",
                **TABLE_STYLE
            ),
            html.Hr()
        ], style={"marginBottom": "40px"})
        for name, df in tables.items()
    ]
])