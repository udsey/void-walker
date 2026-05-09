import dash
import plotly.express as px
from dash import dcc, html
import dash_bootstrap_components as dbc
from dashboard.db import overview_map

dash.register_page(__name__, path="/overview")

data = {name: fn() for name, fn in overview_map.items()}
kpis = data["kpis"].iloc[0]


def kpi_card(title, value):
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.H6(title, style={"color": "#888888", "letterSpacing": "0.08em", "fontWeight": "300"}),
                html.H3(str(value), style={"color": "#ffffff", "fontWeight": "300"})
            ])
        ], color="dark", outline=True),
        width=4,
        className="mb-3"
    )


sessions_over_time = data["sessions_over_time"]
action_dist = data["action_distribution"]
archetype_stats = data["archetype_stats"]
exit_reasons = data["exit_reasons"]

layout = html.Div([
    html.H1("overview", className="mb-4"),

    # KPI cards 2x3
    dbc.Row([
        kpi_card("total sessions", kpis["total_sessions"]),
        kpi_card("total actions", kpis["total_actions"]),
        kpi_card("total invites", kpis["total_invites"]),
        kpi_card("messages sent", kpis["total_messages_sent"]),
        kpi_card("messages failed", kpis["total_messages_failed"]),
        kpi_card("feedbacks", kpis["total_feedbacks"]),
        kpi_card("avg actions / session", kpis["avg_actions_per_session"]),
        kpi_card("avg messages / session", kpis["avg_messages_per_session"]),
        kpi_card("mood shifts", kpis["total_mood_shifts"]),
    ], className="mb-4"),

    # Charts row 1
    dbc.Row([
        dbc.Col(dcc.Graph(figure=px.line(
            sessions_over_time, x="hour", y="sessions",
            title="sessions over time",
            template="plotly_dark",
            markers=True,
            color_discrete_sequence=["#7c6fcd"]
        ))
            , width=6),
        dbc.Col(dcc.Graph(figure=px.pie(
            data["friend_vs_solo"], names="type", values="count",
            title="friend vs solo",
            template="plotly_dark",
            color_discrete_sequence=["#7c6fcd", "#7a9e7e", "#c4956a", "#b07090", "#8fa8c8", "#a89070", "#6b9e9e", "#9e7a7a", "#7a8fa8"]
        )), width=3),
        dbc.Col(dcc.Graph(figure=px.pie(
            exit_reasons, names="exit_reason", values="count",
            title="exit reasons",
            template="plotly_dark",
            color_discrete_sequence=["#7c6fcd", "#7a9e7e", "#c4956a", "#b07090", "#8fa8c8", "#a89070", "#6b9e9e", "#9e7a7a", "#7a8fa8"]
        )), width=3),
    ], className="mb-4"),

    # Charts row 2
    dbc.Row([
        dbc.Col(dcc.Graph(figure=px.bar(
            action_dist, x="times_used", y="action",
            orientation="h",
            title="most used actions",
            template="plotly_dark",
            color_discrete_sequence=["#7c6fcd"]
        ).update_layout(yaxis={"categoryorder": "total ascending"})), width=6),
        dbc.Col(dcc.Graph(figure=px.bar(
            archetype_stats, x="archetype", y="avg_duration_minutes",
            title="avg session duration by archetype (minutes)",
            template="plotly_dark",
            hover_data=["sessions", "most_common_exit"],
            color_discrete_sequence=["#7c6fcd"]
        )), width=6),
    ]),
])