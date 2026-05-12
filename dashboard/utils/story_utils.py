"""Story utils."""


import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

from dashboard.db import novel_map

ACTION_MAP = {
    'observe_website': 'observing the void',
    'check_new_messages': 'checking for messages',
    'move_around': 'drifting further into the dark',
    'press_explore': 'pressing explore',
    'open_window': 'opening a window',
    'invite_friend': 'inviting a friend',
    'send_message': 'sending a message',
    'send_feedback': 'leaving feedback',
    'decide_open_website': 'standing at the edge',
    'respond_to_message': 'responding to someone',
    'open_website': 'entering the void',
    'close_website': 'closes website'
}

BASIC_ACTIONS = {'move_around', 'press_explore',
                 'open_window', 'observe_website',
                 'check_new_messages', 'open_website', 'close_website'}

def create_title(walker_id: str) -> str:
    """Create title."""
    return f"Walker #{walker_id[:8]}"


def create_header(persona: pd.DataFrame
                  ) -> dict:
    """Create header."""
    native_l = persona.mother_language.values[0]
    mood_line = f"{persona.mood.values[0]} → {persona.final_mood.values[0]}"
    second_l = ", ".join(
        [lng.strip("{}") for lng in persona.second_languages.values.tolist()])
    header = {"name": f"{persona.name.values[0]}",
              "gender": f"{persona.gender.values[0]}",
              "age":    f"{persona.age.values[0]}",
              "archetype": f"{persona.archetype.values[0]}",
              "country": f"{persona.country.values[0]}",
              "languages": f"{native_l} (native), {second_l}",
              "mood": f"{mood_line}"
    }
    sub_title = f"Session #{str(persona.session_id.values[0])[:8]}"

    return {
        'header': header,
        'sub_title': sub_title
    }


def create_event_block(session_breakdown: pd.DataFrame) -> dict:
    """Create story content."""

    events = []
    last_mood = None
    footer = ''

    for _, row in session_breakdown.iterrows():
        action_name = row.action_name
        if action_name == 'summarize':
            summary = row.summary
            footer = {
                'end reason': row.exit_reason,
                'subject note': summary
            }
            continue


        mood = row.mood_before or last_mood
        prefix = f"{row.mood_before}ly " if row.mood_shift and mood else ""
        header = f"[{row.time}] < {prefix}{ACTION_MAP[row.action_name]} >"


        if row.action_name == 'invite_friend':
            text = f"to {row.friend_name}:\n\n{row.invite_message}"
        elif row.action_name == "send_message":
            if row.message_is_sent:
                text = f"— {row.message.replace('—', '-')}"
            else:
                text = f"{row.function_result}"
        elif row.action_name == "respond_to_message":
            if row.message_is_sent:
                text = f"— {row.reply_to.replace('—', '-')}\n"
                text += f"\n— {row.message.replace('—', '-')}"
            else:
                text = f"{row.function_result}"
        elif row.action_name == 'send_feedback':
            text = f"leave your feedback here:\n\n{row.feedback}"
        else:
            text = ''

        events.append({
            'header': header,
            'text': text,
            'reflection': row.reflection.strip()
                if isinstance(row.reflection, str) and row.reflection.strip()
                else None,

            'selection': row.selection_reason.strip()
                if (isinstance(row.selection_reason, str)
                    and row.selection_reason.strip())
                else None,

            'llm_answer': row.llm_answer.strip()
                if isinstance(row.llm_answer, str) and row.llm_answer.strip()
                else None,
        })

    return {
        'events': events,
        'footer': footer
        }


def create_story(session_id: str) -> tuple:
    """Generate session story."""

    session_breakdown = novel_map['session_breakdown'](session_id)
    persona = novel_map['persona'](session_id)

    if persona.empty:
        raise ValueError("No such session_id")

    title = create_title(walker_id=session_id)
    header = create_header(persona=persona)
    event_block = create_event_block(session_breakdown=session_breakdown)

    content_dict = {'title': title}
    content_dict.update(header)
    content_dict.update(event_block)

    return content_dict



env = Environment(loader=FileSystemLoader('dashboard/utils'))
template = env.get_template('story_pdf.html')


def create_story_pdf(story: dict) -> bytes:
    """Generate pdf version of story."""
    try:
        html_content = template.render(story=story)
        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[CSS(filename='dashboard/utils/story.css')]
        )
        return pdf_bytes
    except Exception as e:
        print(f"PDF generation error: {e}")
        raise

