"""Raw Tables."""
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, html

from dashboard.db import raw_map
from dashboard.styles import TABLE_STYLE

dash.register_page(__name__, path="/tables")

tables = {name: fn() for name, fn in raw_map.items()}

for name, df in tables.items():
    if "session_id" in df.columns:
        df["session_id"] = df["session_id"].apply(
            lambda x: f"[{str(x)[:6]}...](/session?id={x})" if x else ""
        )


layout = html.Div([
    dbc.Modal([dbc.ModalBody(id="cell-modal-body")],
              id="cell-modal",
              is_open=False),
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


for name in tables:
    @callback(
        Output("cell-modal", "is_open", allow_duplicate=True),
        Output("cell-modal-body", "children", allow_duplicate=True),
        Input(f"{name.lower()}-table", "active_cell"),
        State(f"{name.lower()}-table", "derived_virtual_data"),
        prevent_initial_call=True
    )
    def show_cell(active_cell, data):
        if not active_cell or not data:
            return False, None
        row = data[active_cell["row"]]
        value = row[active_cell["column_id"]]
        return True, str(value)
