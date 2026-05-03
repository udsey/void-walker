# void-walker 🚶 State Definition

---

## VoidWalkerState

```python
class VoidWalkerState(TypedDict):
    # Session
    session_id: str
    start_time: datetime

    # Navigation
    current_url: str

    # Memory
    summary: str | None              # episodic memory, overwritten after each node via summarizer
    action_history: list[str]
    messages: list[str]              # last N messages read from canvas, replaced on each read
    outstanding_messages: list[str]  # highlights from current read, replaced on each read
    outstanding_history: set[str]    # all-time deduped outstanding messages across session
    focused_message: str | None      # currently selected message for respond action

    # Social
    invited_friends: int
    friend_messages: list[dict]      # {friend_id, message_text}
```

---

## Notes

**summary**
- Overwritten after every node via an intermediate summarizer node between actions
- LLM reflects: what did I do, why, what happened, how do I feel about it
- Written in persona voice

**messages**
- Replaced on each `read_visible_messages` call
- Keeps last N messages (N configurable)
- Full history covered by summary

**outstanding_messages**
- Replaced on each `read_visible_messages` call
- Selected by `select_outstanding` node from current messages
- What feels interesting *right now*

**outstanding_history**
- Grows over session, never replaced — only appended
- Stored as set, deduped automatically
- Used by `select_outstanding` to detect already-seen messages
- Partially cleared by `forget_outstanding` node (triggered randomly)
- Persona influences what gets forgotten — but trigger is always random

**focused_message**
- Set by `respond_to_message` node
- Pulled from `outstanding_messages`

**friend_messages**
- Injected by parent graph via `notify_friend` node
- Format: `{friend_id, message_text}`
- Simulates: *"hey, I just sent '{text}' in void-cast, can you see it?"*

**persona**
- Not stored in state
- Defined in `initialize_session` node
- Injected as system prompt into every LLM call
