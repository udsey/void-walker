

import dash
from dash import Input, Output, State, dcc, html

from dashboard.utils.observer_utils import redis_sync

dash.register_page(__name__, path="/session-view")

layout = html.Div([
    dcc.Interval(id="session-view-poll", interval=20000),
    dcc.Location(id="session-view-location"),
    dcc.Store(id="session-view-url-store"),
    html.Div(id="session-view-dummy")
])

@dash.callback(
    Output("session-view-url-store", "data"),
    Input("session-view-poll", "n_intervals"),
    State("session-view-location", "search"),  # gets ?session_id=xxx from URL
    prevent_initial_call=False
)
def follow_session(_, search):
    if not search:
        return dash.no_update
    session_id = search.replace("?session_id=", "")
    url = redis_sync.get(f"observer:session:{session_id}:url")
    if url:
        return url
    return dash.no_update


dash.clientside_callback(
    """
    function(url) {
        if (!url) return null;
        if (!window._sessionTab || window._sessionTab.closed) {
            window._sessionTab = window.open(url, "session-follower");
            window._sessionTabUrl = url;
        } else if (url !== window._sessionTabUrl) {
            window._sessionTab.location.href = url;
            window._sessionTabUrl = url;
        }
        return null;
    }
    """,
    Output("session-view-dummy", "children"),
    Input("session-view-url-store", "data"),
)
