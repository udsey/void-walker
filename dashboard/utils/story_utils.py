"""Story utils."""


import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

from dashboard.db import novel_map

ACTION_MAP = {
    'observe_website': 'OBSERVING THE VOID',
    'check_new_messages': 'CHECKING FOR MESSAGES',
    'move_around': 'DRIFTING FURTHER INTO THE DARK',
    'press_explore': 'PRESSING EXPLORE',
    'open_window': 'OPENING A WINDOW',
    'invite_friend': 'INVITING A FRIEND',
    'send_message': 'SENDING A MESSAGE',
    'send_feedback': 'LEAVING FEEDBACK',
    'decide_open_website': 'STANDING AT THE EDGE',
    'respond_to_message': 'RESPONDING TO SOMEONE',
    'open_website': 'ENTERING THE VOID',
    'close_website': 'LEAVING THE VOID'}

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

    for i, row in session_breakdown.iterrows():
        action_name = row.action_name
        if action_name == 'summarize':
            summary = row.summary
            footer = {
                'end reason': row.exit_reason,
                'subject note': summary
            }
            continue


        mood = row.mood_before or last_mood
        mood = f"({mood})" if mood and isinstance(mood, str) else ''
        header = f"[{row.time}] {mood} < {ACTION_MAP[row.action_name]} >"
        system_error = None

        if isinstance(row.function_result, str):
            system_message = row.function_result.strip()
            if len(system_message) > 600:
                system_message = system_message[:600] + '...'
        else:
            system_message = None


        if row.action_name == 'invite_friend':
            text = f"to {row.friend_name}:\n\n{row.invite_message}"
        elif row.action_name == "send_message":
            text = f"— {row.message.replace('—', '-')}"
            if not row.message_is_sent:
                system_error, system_message = system_message, None
        elif row.action_name == "respond_to_message":
            text = f"— {row.reply_to.replace('—', '-')}\n"
            text += f"\n— {row.message.replace('—', '-')}"
            if not row.message_is_sent:
                system_error, system_message = system_message, None
        elif row.action_name == 'send_feedback':
            text = f"leave your feedback here:\n\n{row.feedback}"
        else:
            text = ''

        last_mood = mood


        events.append({
            'header': header,
            'text': text,
            'system_message': system_message,
            'system_error': system_error,
            'reflection': row.reflection.strip()
                if isinstance(row.reflection, str) and row.reflection.strip()
                else None,
            'selection': row.selection_reason.strip()
                if isinstance(row.selection_reason, str)
                and row.selection_reason.strip()
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

    content_dict = {'title': title,
                    'session_id': session_id}
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

