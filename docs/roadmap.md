# void-walker 🚶 Roadmap

> An autonomous LLM agent that wanders void-cast — filling the void, testing the app, and simulating human behavior. Three-in-one: QA tool, content seeder, and LLM behavior observatory.

---

## Stack

- **Language:** Python
- **Agent framework:** LangChain (LangGraph)
- **Browser automation:** Selenium
- **LLM:** Ollama (local)
- **Logging DB:** PostgreSQL (local, separate from void-cast)
- **Target:** void-cast on fly.io

---

## Phase 1 — Selenium Scripts

> Foundation layer. Every graph node depends on these.

- [ ] `open_browser(url)` — launch browser session, navigate to void-cast
- [ ] `close_browser()` — gracefully exit session
- [ ] `read_visible_messages()` — scrape currently visible message elements from canvas
- [ ] `send_message(text)` — locate input, type, submit. Returns: `sent` | `rate_limit_error`
- [ ] `press_share()` — click share button, capture and return generated URL
- [ ] `open_url(url)` — navigate to a given URL (used for shared links / friend invite)
- [ ] `press_explore()` — click explore/teleport button, return confirmation
- [ ] `move_around(dx, dy)` — simulate canvas pan via mousedown → mousemove → mouseup with given delta
- [ ] `open_info_window(window_name)` — open a specific UI window (about, help, etc.), read content, close
- [ ] `exit_site()` — close browser session cleanly

---

## Phase 2 — Graph State

> Everything the agent knows and remembers during a session.

- [ ] Define `VoidWalkerState` dataclass / TypedDict:
  - `current_url` — active URL including position params
  - `shared_url` — URL captured after pressing share
  - `thoughts` — LLM scratchpad, updated after each action
  - `messages` — list of messages read from canvas
  - `action_history` — ordered list of actions taken this session
  - `visited_positions` — list of (x, y) coords explored
  - `invited_friends` — count of friend sessions spawned
  - `friend_messages` — incoming notifications from friend graphs `{friend_id, message_text}`
  - `focused_message` — currently selected message for respond action
  - `persona` — assigned persona object for this session
  - `session_id` — unique ID for logging
  - `start_time` — for time limit enforcement

---

## Phase 3 — Persona System

- [ ] Define `Persona` structure: `name`, `description`, `system_prompt`, `vibe`
- [ ] Write a set of base personas (e.g. bored wanderer, philosophical insomniac, lost tourist, anxious lurker, chaotic poster...)
- [ ] Random persona assignment on session start
- [ ] Friend sessions receive a different randomly assigned persona + intro: *"your friend sent you an invite to void-cast"*
- [ ] Friend session has an additional entry node: **Open or Ignore invite** (LLM decides)

---

## Phase 4 — LangGraph Nodes

> Core agent graph. All nodes are LLM-driven. Select action is the central router.

- [ ] **select_action** *(conditional router)* — LLM receives: current thoughts, action history, visible messages, friend_messages, persona. Decides next node.
- [ ] **read_visible_messages** — calls selenium script, updates `state.messages`. Returns list of messages.
- [ ] **send_message** — LLM decides what to write based on persona + context. Calls selenium script. Updates action history. Returns: `sent` | `rate_limit_error`
- [ ] **respond_to_message** — LLM picks a focused message from state, decides what to reply, sends via selenium. Updates `focused_message` and action history.
- [ ] **open_window** — LLM picks a window to open. Calls selenium script. Returns window content. Updates thoughts.
- [ ] **press_explore** — calls selenium script to teleport. Updates `visited_positions`. Returns: `moved to a new position`
- [ ] **press_share** — calls selenium script. Stores URL in `state.shared_url`. Returns: `now you can share this place`
- [ ] **move_around** — calls selenium script with random dx/dy from current position. Updates `visited_positions`.
- [ ] **notify_friend** *(available when `invited_friends > 0`)* — selects a friend, injects last sent message into `friend.state.friend_messages` as `{friend_id, message_text}`. Simulates: *"hey, I just sent '{text}' in void-cast, can you see it?"*
- [ ] **invite_friend** *(available when under friend limit)* — uses `state.shared_url`, spawns an independent VoidWalker graph with a new persona. Increments `invited_friends`.
- [ ] **write_feedback** — LLM reflects on session, writes a comment about the app into the void. Logged to DB.
- [ ] **exit_site** *(end node)* — closes browser, finalizes session log.

---

## Phase 5 — Session Limits & Interrupts

- [ ] `MAX_SESSION_DURATION` — time limit per session, configurable. Triggers graceful exit if exceeded.
- [ ] `MAX_FRIENDS` — cap on number of friend sessions spawned per run.
- [ ] Interrupt handler — on timeout, route to `exit_site` cleanly.

---

## Phase 6 — Logging (Local PostgreSQL)

> Local DB, fully separate from void-cast infrastructure.

- [ ] Design schema:
  - `sessions` — session_id, persona, start_time, end_time, total_actions, invited_friends
  - `actions` — session_id, timestamp, action_type, input, result, thoughts_snapshot
  - `messages_read` — session_id, timestamp, message_text
  - `messages_sent` — session_id, timestamp, message_text, status
  - `feedback` — session_id, timestamp, feedback_text
- [ ] Write logger utility — called after every node execution
- [ ] Session summary report on exit — printed to console + stored in DB

---

## Phase 7 — void-cast Test Mode

> Small addition to void-cast to support testing.

- [ ] Add `TESTING_MODE` env flag to void-cast
- [ ] When enabled: relax or bypass IP-based rate limiting
- [ ] Optional: accept a test header to identify walker sessions in logs

---

## Phase 8 — Multi-Agent Simulation

> The fun part 👻

- [ ] Run multiple independent VoidWalker sessions simultaneously
- [ ] Each session: different persona, different behavior
- [ ] Observe cross-session interactions naturally via SSE (the void syncs them)
- [ ] Aggregate logs across sessions for behavior analysis

---

## Stretch Goals

- [ ] Web dashboard to replay session logs and visualize action sequences
- [ ] Persona tuning based on observed behavior patterns
- [ ] Export session data as "user behavior test reports"
- [ ] Publish findings as a weird little social experiment 👁️
