"""
chat_ui.py — Google ADK-style Chat App with JWT Authentication, Loading Animations, and PyDataUI DataTable Support.
"""

import os
import re
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

import jwt
from jwt import InvalidTokenError
from pydantic import BaseModel, Field

from pydataui import App, State, Html
from pydataui.html import (
    Div, Span, Section, Header, Main, Nav, H1, H2, H3, P, Strong, Pre, Svg, Path
)
from pydataui.components.shadcn import (
    ShadCard, ShadCardHeader, ShadCardTitle, ShadCardDescription,
    ShadCardContent, ShadBadge, ShadButton, ShadInput, ShadSeparator
)
from pydataui.components import (
    Container, Flex, Grid, HStack, VStack, Button, Input, Markdown, Table, Badge, Code, Form, Spinner, DataTable
)

from agent.supportAgent.tools import engine, text
from agent.graph import app as graph_app
from agent.chat_app import chat_resonse
from agent.llm_models import set_temporary_api_key
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


# ----------------------------------------------------------------------
# 1. JWT Authentication & Models
# ----------------------------------------------------------------------

JWT_SECRET = os.getenv("JWT_SECRET", "FDEProject")
ALGORITHM = "HS256"


def create_token(user_id: str) -> str:
    """Generate signed JWT access token for customer."""
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> str:
    """Verify JWT access token and return subject customer_id."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id or not isinstance(user_id, str):
            return None
        return user_id
    except InvalidTokenError:
        return None


class Auth(BaseModel):
    email: str
    password: int


class AgentRequest_Auth(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    auth: Auth = Field(description="authenticate")


def authentication(auth: Auth):
    """Authenticate customer against login_credentials table in database."""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT customer_id, full_name
                FROM login_credentials
                WHERE email = :email
                  AND password = :password
            """),
            {
                "email": auth.email,
                "password": auth.password,
            }
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


# ----------------------------------------------------------------------
# 2. Table Parsing & Component Builders
# ----------------------------------------------------------------------

def render_tool_call_card(tc: dict) -> Html:
    """Renders a Google ADK-style tool call execution card."""
    tool_name = tc.get("name", "tool")
    tool_id = tc.get("id", "call")
    status = tc.get("status", "completed").upper()
    args_json = json.dumps(tc.get("args", {}), indent=2)

    raw_output = tc.get("output", "")
    try:
        parsed_out = json.loads(raw_output)
        output_display = json.dumps(parsed_out, indent=2)
    except Exception:
        output_display = raw_output

    badge_color = "bg-emerald-500/20 text-emerald-400 border-emerald-500/40" if status == "COMPLETED" else "bg-amber-500/20 text-amber-400 border-amber-500/40"

    card_html = f"""
    <div class="my-3 rounded-xl border border-border/80 bg-zinc-950/90 shadow-md overflow-hidden transition-all hover:border-emerald-500/50">
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-2 bg-zinc-900/90 border-b border-border/60">
            <div class="flex items-center gap-2">
                <span class="flex h-5 w-5 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400 text-xs">🛠️</span>
                <span class="font-mono text-xs font-semibold text-emerald-400 tracking-wide">{tool_name}</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wider border {badge_color}">{status}</span>
            </div>
            <span class="text-[11px] font-mono text-muted-foreground">ID: {tool_id[:12]}</span>
        </div>

        <!-- Body -->
        <div class="p-3 space-y-2 text-xs">
            <details open class="group">
                <summary class="cursor-pointer font-semibold text-zinc-400 hover:text-zinc-200 flex items-center gap-1 select-none py-0.5">
                    <span class="text-[10px] text-zinc-500 group-open:rotate-90 transition-transform">▶</span>
                    <span>Arguments (Input)</span>
                </summary>
                <div class="mt-1 rounded-lg bg-zinc-900/80 p-2.5 border border-zinc-800">
                    <pre class="font-mono text-zinc-300 text-[11px] overflow-x-auto leading-relaxed"><code>{args_json}</code></pre>
                </div>
            </details>

            <details open class="group">
                <summary class="cursor-pointer font-semibold text-zinc-400 hover:text-zinc-200 flex items-center gap-1 select-none py-0.5">
                    <span class="text-[10px] text-zinc-500 group-open:rotate-90 transition-transform">▶</span>
                    <span>Result (Output)</span>
                </summary>
                <div class="mt-1 rounded-lg bg-zinc-900/80 p-2.5 border border-zinc-800">
                    <pre class="font-mono text-emerald-300 text-[11px] overflow-x-auto leading-relaxed"><code>{output_display}</code></pre>
                </div>
            </details>
        </div>
    </div>
    """
    return Html(card_html)


def render_assistant_content(text: str) -> Div:
    """Render assistant message, converting Markdown tables into PyDataUI sortable DataTables and styling."""
    if not text:
        return Div()

    # Regex to detect markdown tables
    table_pattern = re.compile(
        r'(\|[^\n]+\|\r?\n\|[-:\s|]+\|\r?\n(?:\|[^\n]+\|\r?\n?)+)',
        re.MULTILINE
    )

    match = table_pattern.search(text)
    if not match:
        return Div(Markdown(text), class_name="overflow-x-auto")

    before = text[:match.start()].strip()
    table_str = match.group(0).strip()
    after = text[match.end():].strip()

    elements = []
    if before:
        elements.append(Markdown(before))

    # Parse table lines into headers and rows for PyDataUI DataTable
    try:
        lines = [l.strip() for l in table_str.splitlines() if l.strip()]
        headers = [h.strip() for h in lines[0].split('|')[1:-1]]
        rows = []
        for line in lines[2:]:
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) == len(headers):
                rows.append(dict(zip(headers, cols)))

        if rows:
            elements.append(
                Div(
                    DataTable(data=rows, sortable=True),
                    class_name="my-3 overflow-x-auto rounded-xl border border-border/80 bg-zinc-950/60 shadow-md p-1"
                )
            )
        else:
            elements.append(Markdown(table_str))
    except Exception:
        elements.append(Markdown(table_str))

    if after:
        elements.append(Markdown(after))

    return Div(*elements, class_name="overflow-x-auto space-y-2")


def render_chat_stream(history: list) -> Div:
    """Render conversation turns with user bubbles, tool execution cards, assistant replies, and loading state."""
    if not history:
        return Div(
            Div(
                Span("🤖", class_name="text-4xl mb-3 block"),
                H3("Customer Support Agent", class_name="text-lg font-bold text-foreground mb-1"),
                P("Ask questions regarding your purchases, invoices, or customer profile. Tool calls and responses will appear below in real time.",
                  class_name="text-sm text-muted-foreground max-w-md mx-auto mb-4"),
                Div(
                    Span("Try one of these quick test prompts:", class_name="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 block"),
                    Flex(
                        Button("🔍 Check My Purchase", variant="outline", size="sm", on_click=ChatAppState.run_sample_lookup),
                        Button("🧾 Generate My Invoice", variant="outline", size="sm", on_click=ChatAppState.run_sample_invoice),
                        Button("📋 View Account Details", variant="outline", size="sm", on_click=ChatAppState.run_sample_columns),
                        gap="sm", wrap="wrap", justify="center"
                    ),
                    class_name="bg-muted/30 p-4 rounded-xl border border-border"
                ),
                class_name="text-center py-12 px-4"
            ),
            # Loading indicator container for HTMX
            Html("""
            <div id="chat-loading-indicator" class="htmx-indicator hidden items-center gap-3 p-3.5 my-3 rounded-2xl rounded-tl-sm bg-zinc-900/90 border border-emerald-500/40 text-emerald-400 shadow-md mr-auto max-w-md animate-pulse">
                <div class="flex items-center gap-2.5">
                    <span class="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-500/20 text-emerald-400 text-xs">🤖</span>
                    <div class="flex space-x-1 items-center px-1">
                        <span class="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                        <span class="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                        <span class="w-2 h-2 bg-emerald-400 rounded-full animate-bounce"></span>
                    </div>
                    <span class="text-xs font-mono font-medium text-zinc-300">Agent reasoning & executing tools...</span>
                </div>
            </div>
            """),
            id="chat-messages-container",
            class_name="flex-1 overflow-y-auto pr-2"
        )

    turn_elements = []
    for turn in history:
        user_msg = turn.get("user", "")
        tool_calls = turn.get("tool_calls", [])
        assistant_msg = turn.get("assistant", "")

        elements = []

        # 1. User Message (Right Aligned Bubble)
        if user_msg:
            elements.append(
                Div(
                    Div(
                        Span("👤 You", class_name="text-[11px] font-semibold text-zinc-400 mb-1 block"),
                        P(user_msg, class_name="text-sm leading-relaxed text-zinc-100"),
                        class_name="max-w-[85%] rounded-2xl rounded-tr-sm px-4 py-3 bg-zinc-800 border border-zinc-700 shadow-md ml-auto"
                    ),
                    class_name="flex justify-end mb-4"
                )
            )

        # 2. Tool Calls (Google ADK cards)
        if tool_calls:
            for tc in tool_calls:
                elements.append(render_tool_call_card(tc))

        # 3. Assistant Message with Enhanced PyDataUI Table Rendering
        if assistant_msg:
            elements.append(
                Div(
                    Div(
                        Span("🤖 Assistant", class_name="text-[11px] font-semibold text-emerald-400 mb-1 block"),
                        render_assistant_content(assistant_msg),
                        class_name="max-w-[95%] rounded-2xl rounded-tl-sm px-4 py-3 bg-card border border-border text-foreground shadow-sm mr-auto overflow-x-auto"
                    ),
                    class_name="flex justify-start mb-4"
                )
            )

        turn_elements.append(Div(*elements, class_name="mb-6"))

    # Append loading animation element at the bottom of message history
    loading_html = Html("""
    <div id="chat-loading-indicator" class="htmx-indicator hidden items-center gap-3 p-3.5 my-3 rounded-2xl rounded-tl-sm bg-zinc-900/90 border border-emerald-500/40 text-emerald-400 shadow-md mr-auto max-w-md animate-pulse">
        <div class="flex items-center gap-2.5">
            <span class="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-500/20 text-emerald-400 text-xs">🤖</span>
            <div class="flex space-x-1 items-center px-1">
                <span class="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span class="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span class="w-2 h-2 bg-emerald-400 rounded-full animate-bounce"></span>
            </div>
            <span class="text-xs font-mono font-medium text-zinc-300">Agent reasoning & executing tools...</span>
        </div>
    </div>
    """)
    turn_elements.append(loading_html)

    return Div(*turn_elements, id="chat-messages-container", class_name="flex-1 overflow-y-auto pr-2 space-y-4")


# ----------------------------------------------------------------------
# 3. Reactive State
# ----------------------------------------------------------------------

def get_active_model_label() -> str:
    """Format a human-readable, masked display label of the currently loaded API key."""
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        masked = groq_key[:6] + "..." + groq_key[-4:] if len(groq_key) > 10 else "******"
        return f"Groq ⚡ ({masked})"
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if google_key:
        masked = google_key[:6] + "..." + google_key[-4:] if len(google_key) > 10 else "******"
        return f"Gemini ✨ ({masked})"
    return "No Key Set ⚠️"


class ChatAppState(State):
    """Reactive State managing JWT authentication, agent conversation, and tool call execution."""
    is_authenticated: bool = False
    jwt_token: str = ""
    login_email: str = ""
    login_password: str = ""
    login_error: str = ""
    auth_user: dict = {}
    temp_api_key: str = ""

    ui_api_key_input: str = ""
    show_key_drawer: bool = False
    key_status_message: str = ""
    active_key_display: str = get_active_model_label()

    user_input: str = ""
    thread_id: str = "session_01"
    history: list = []
    total_tool_calls: int = 0
    status_text: str = "Ready"

    def toggle_key_drawer(self):
        """Toggle in-chat API key configuration drawer."""
        self.show_key_drawer = not self.show_key_drawer
        self.active_key_display = get_active_model_label()

    def apply_ui_api_key(self):
        """Apply temporary API key from in-chat drawer."""
        raw = self.ui_api_key_input.strip()
        if not raw:
            self.key_status_message = "⚠️ Please enter a non-empty API key."
            return
        provider = "gemini" if raw.startswith("AIza") else "groq"
        set_temporary_api_key(raw, provider=provider)
        self.ui_api_key_input = ""
        self.active_key_display = get_active_model_label()
        self.key_status_message = f"✅ Applied {self.active_key_display} in temporary memory!"
        self.status_text = self.key_status_message

    def clear_ui_api_key(self):
        """Clear temporary API keys from environment."""
        os.environ.pop("GROQ_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)
        set_temporary_api_key("")
        self.active_key_display = get_active_model_label()
        self.key_status_message = "🗑️ Cleared API keys from temporary memory."
        self.status_text = "API keys removed from environment."

    def apply_login_api_key(self):
        """Apply temporary API key directly from login card."""
        raw = self.temp_api_key.strip()
        if not raw:
            self.login_error = "Please enter an API key to apply."
            return
        provider = "gemini" if raw.startswith("AIza") else "groq"
        set_temporary_api_key(raw, provider=provider)
        self.active_key_display = get_active_model_label()
        self.login_error = ""
        self.status_text = f"✅ Applied {self.active_key_display} in temporary memory!"

    def login(self):
        """Validate user credentials against database and generate JWT access token."""
        email = self.login_email.strip()
        pwd_str = str(self.login_password).strip()

        if not email or not pwd_str:
            self.login_error = "Please provide both email and numeric password."
            return

        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT customer_id, full_name, password
                    FROM login_credentials
                    WHERE email = :email
                """),
                {"email": email}
            ).mappings().first()

        if not row or str(row["password"]) != pwd_str:
            self.login_error = "Invalid credentials. Please verify your email and password."
            return

        if self.temp_api_key.strip():
            provider = "gemini" if self.temp_api_key.strip().startswith("AIza") else "groq"
            set_temporary_api_key(self.temp_api_key.strip(), provider=provider)
            self.active_key_display = get_active_model_label()

        customer_id = str(row["customer_id"])
        token = create_token(customer_id)

        self.jwt_token = token
        self.is_authenticated = True
        self.auth_user = {
            "customer_id": customer_id,
            "full_name": row.get("full_name", customer_id),
            "email": email,
        }
        self.login_error = ""
        self.status_text = f"JWT Authenticated: {row.get('full_name')} ({customer_id})"
        self.thread_id = f"session_{customer_id.lower()}"

    def logout(self):
        """Log out and revoke JWT session state."""
        self.jwt_token = ""
        self.is_authenticated = False
        self.auth_user = {}
        self.login_email = ""
        self.login_password = ""
        self.login_error = ""
        self.history = []
        self.total_tool_calls = 0
        self.status_text = "Logged out."

    def fill_demo_user1(self):
        """Fill demo credentials for Kiran Iyer."""
        self.login_email = "customer0001@example.test"
        self.login_password = "60115"
        self.login_error = ""

    def fill_demo_user2(self):
        """Fill demo credentials for Sara Sharma."""
        self.login_email = "customer0002@example.test"
        self.login_password = "41040"
        self.login_error = ""

    async def send_message(self, message: str = ""):
        """Send user input authenticated via JWT token with loading indicator."""
        query = message.strip() if message else self.user_input.strip()
        if not query:
            return

        if not self.is_authenticated or not self.jwt_token:
            self.status_text = "Please log in first."
            self.is_authenticated = False
            return

        # Validate JWT token
        user_id = verify_token(self.jwt_token)
        if not user_id:
            self.status_text = "JWT token expired or invalid. Please re-login."
            self.is_authenticated = False
            self.jwt_token = ""
            return

        self.user_input = ""
        self.status_text = "Processing request & invoking agent tools..."

        try:
            # Wire query with JWT verified customer_id matching app.py
            res = await chat_resonse(
                query=query + f"\n customer specific authenticate info : customer_id : {user_id}",
                thread_id=self.thread_id,
            )

            # Safely serialize output directly as string (no .get call)
            assistant_output = str(res) if isinstance(res, str) else str(getattr(res, "content", res))

            # Retrieve any tool execution trace from graph state
            tool_calls = []
            try:
                state = await graph_app.aget_state({"configurable": {"thread_id": self.thread_id}})
                if state and hasattr(state, "values") and "messages" in state.values:
                    for m in reversed(state.values["messages"]):
                        if isinstance(m, HumanMessage):
                            break
                        if isinstance(m, ToolMessage):
                            tool_calls.insert(0, {
                                "id": getattr(m, "tool_call_id", ""),
                                "name": getattr(m, "name", "tool"),
                                "args": {},
                                "output": str(m.content),
                                "status": "completed",
                            })
                        elif isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                            for tc in m.tool_calls:
                                tc_id = tc.get("id", "")
                                existing = next((t for t in tool_calls if t["id"] == tc_id), None)
                                if existing:
                                    existing["name"] = tc.get("name", existing["name"])
                                    existing["args"] = tc.get("args", {})
                                else:
                                    tool_calls.insert(0, {
                                        "id": tc_id,
                                        "name": tc.get("name", "tool"),
                                        "args": tc.get("args", {}),
                                        "output": None,
                                        "status": "completed",
                                    })
            except Exception:
                tool_calls = []

            self.history.append({
                "user": query,
                "tool_calls": tool_calls,
                "assistant": assistant_output,
            })
            self.total_tool_calls += len(tool_calls)
            self.status_text = f"Agent completed turn. Total tools executed: {self.total_tool_calls}"
        except Exception as e:
            self.status_text = f"Error: {str(e)}"

    async def run_sample_lookup(self):
        """Quick action: Lookup customer details."""
        await self.send_message(
            "Please check the details for my purchase, specifically the item and price."
        )

    async def run_sample_invoice(self):
        """Quick action: Generate invoice."""
        await self.send_message(
            "Please generate an invoice for my recent purchase."
        )

    async def run_sample_columns(self):
        """Quick action: Discover database columns."""
        await self.send_message(
            "What database columns are available for my customer account?"
        )

    def new_session(self):
        """Start a brand new session with fresh thread ID."""
        prefix = self.auth_user.get("customer_id", "user").lower() if self.auth_user else "session"
        self.thread_id = f"{prefix}_{uuid.uuid4().hex[:6]}"
        self.history = []
        self.total_tool_calls = 0
        self.status_text = f"Started new session: {self.thread_id}"

    def clear_history(self):
        """Clear current conversation display."""
        self.history = []
        self.total_tool_calls = 0
        self.status_text = "Conversation cleared."


# ----------------------------------------------------------------------
# 4. Login View
# ----------------------------------------------------------------------

def render_login_page() -> Section:
    """Render customer login page."""
    error_element = None
    if ChatAppState.login_error:
        error_element = Div(
            Span("⚠️ ", class_name="mr-1"),
            Span(ChatAppState.login_error, class_name="text-xs font-semibold"),
            class_name="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-center"
        )

    login_card = ShadCard(
        ShadCardHeader(
            Div(
                Span("🔐", class_name="text-3xl mb-2 block"),
                ShadCardTitle("Customer Portal Login"),
                ShadCardDescription("Sign in with your email and numeric password. A JWT access token will be issued for your session."),
                class_name="text-center"
            ),
            class_name="p-6 pb-4 border-b border-border/60"
        ),
        ShadCardContent(
            Div(
                error_element if error_element else Div(),
                Form(
                    Div(
                        Span("Email Address", class_name="text-xs font-semibold text-muted-foreground mb-1 block"),
                        Input(
                            bind=ChatAppState.login_email,
                            type="email",
                            placeholder="e.g. customer0001@example.test",
                            size="md",
                            required=True,
                            class_name="w-full"
                        ),
                        class_name="mb-4"
                    ),
                    Div(
                        Span("Numeric Password", class_name="text-xs font-semibold text-muted-foreground mb-1 block"),
                        Input(
                            bind=ChatAppState.login_password,
                            type="password",
                            placeholder="e.g. 60115",
                            size="md",
                            required=True,
                            class_name="w-full"
                        ),
                        class_name="mb-5"
                    ),
                    Div(
                        Flex(
                            Span("Temporary API Key (Groq or Gemini)", class_name="text-xs font-semibold text-muted-foreground"),
                            Span(ChatAppState.active_key_display, class_name="text-[11px] font-mono text-amber-400"),
                            justify="space-between", align="center", class_name="mb-1"
                        ),
                        Flex(
                            Input(
                                bind=ChatAppState.temp_api_key,
                                type="password",
                                placeholder="e.g. gsk_... (Groq) or AIza... (Gemini)",
                                size="md",
                                class_name="flex-1"
                            ),
                            Button("Apply ⚡", variant="outline", size="md", on_click=ChatAppState.apply_login_api_key),
                            gap="xs", align="center"
                        ),
                        Span("Held temporarily in memory (os.environ) for this session only; not saved permanently.", class_name="text-[10px] text-muted-foreground/80 mt-1 block"),
                        class_name="mb-5"
                    ),
                    Button("Sign In with JWT 🚀", variant="primary", size="md", type="submit", class_name="w-full justify-center"),
                    on_submit=ChatAppState.login
                ),
                # Quick Demo Logins
                Div(
                    Span("Demo Accounts (Click to auto-fill):", class_name="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block mb-2"),
                    Flex(
                        Button("👤 Kiran Iyer (60115)", variant="outline", size="xs", on_click=ChatAppState.fill_demo_user1),
                        Button("👤 Sara Sharma (41040)", variant="outline", size="xs", on_click=ChatAppState.fill_demo_user2),
                        gap="xs", wrap="wrap", justify="center"
                    ),
                    class_name="mt-6 pt-4 border-t border-border/60 text-center"
                ),
                class_name="p-4"
            )
        ),
        class_name="max-w-md w-full mx-auto shadow-2xl border-border bg-card"
    )

    return Section(
        Container(
            login_card,
            class_name="min-h-screen flex items-center justify-center p-4 bg-background"
        ),
        class_name="min-h-screen bg-background flex items-center justify-center"
    )


# ----------------------------------------------------------------------
# 5. App Definition & Custom Styling
# ----------------------------------------------------------------------

CUSTOM_CSS = """
/* PyDataUI DataTable & Markdown Table Styling Enhancements */
.pdu-datatable-wrapper {
    overflow-x: auto !important;
    width: 100% !important;
}
.pdu-table, .pdu-markdown table, .prose table {
    width: 100% !important;
    border-collapse: collapse !important;
    font-size: 0.8125rem !important;
    margin: 0.5rem 0 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 0.5rem !important;
    overflow: hidden !important;
}
.pdu-table th, .pdu-markdown th, .prose th {
    background-color: rgba(255, 255, 255, 0.06) !important;
    color: #34d399 !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    padding: 0.625rem 0.875rem !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    text-align: left !important;
}
.pdu-table th:last-child, .pdu-markdown th:last-child, .prose th:last-child {
    border-right: none !important;
}
.pdu-table td, .pdu-markdown td, .prose td {
    padding: 0.55rem 0.875rem !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    color: #e4e4e7 !important;
}
.pdu-table td:last-child, .pdu-markdown td:last-child, .prose td:last-child {
    border-right: none !important;
}
.pdu-table tr:last-child td, .pdu-markdown tr:last-child td, .prose tr:last-child td {
    border-bottom: none !important;
}
.pdu-table tr:nth-child(even), .pdu-markdown tr:nth-child(even), .prose tr:nth-child(even) {
    background-color: rgba(255, 255, 255, 0.02) !important;
}
.pdu-table tr:hover, .pdu-markdown tr:hover, .prose tr:hover {
    background-color: rgba(52, 211, 153, 0.08) !important;
    transition: background-color 0.15s ease !important;
}
/* HTMX Loading indicator show/hide styles */
.htmx-indicator {
    display: none;
}
.htmx-request.htmx-indicator,
form.htmx-request ~ #chat-loading-indicator,
.htmx-request #chat-loading-indicator {
    display: flex !important;
}
"""

app = App(
    title="Customer Support Agent Playground",
    theme="light",
    palette="zinc",
    custom_css=CUSTOM_CSS
)


@app.page("/")
def home():
    if not ChatAppState.is_authenticated:
        return render_login_page()

    # 1. Header with Customer & Session Info
    header = Header(
        Nav(
            Flex(
                Div(
                    Span("⚡", class_name="text-2xl"),
                    Div(
                        H1("Customer Support Agent", class_name="text-lg font-bold tracking-tight text-foreground"),
                        P(f"Logged in as {ChatAppState.auth_user.get('full_name', 'Customer')} ({ChatAppState.login_email})", class_name="text-xs text-muted-foreground"),
                    ),
                    class_name="flex items-center gap-3"
                ),
                Flex(
                    ShadBadge(
                        ChatAppState.active_key_display,
                        variant="secondary",
                        class_name="font-mono text-xs text-amber-400 border border-amber-500/30"
                    ),
                    Button("🔑 Set API Key", variant="outline", size="sm", on_click=ChatAppState.toggle_key_drawer),
                    ShadBadge("JWT Verified 🛡️", variant="outline", class_name="font-mono text-xs text-emerald-400 border-emerald-500/40"),
                    ShadBadge(f"Customer: {ChatAppState.auth_user.get('customer_id', '')}", variant="secondary", class_name="font-mono text-xs"),
                    ShadBadge(f"Session: {ChatAppState.thread_id}", variant="secondary", class_name="font-mono text-xs"),
                    ShadBadge(f"Tools Called: {ChatAppState.total_tool_calls}", variant="outline", class_name="font-mono text-xs text-emerald-400 border-emerald-500/40"),
                    Button("➕ New Chat", variant="outline", size="sm", on_click=ChatAppState.new_session),
                    Button("🧹 Clear", variant="ghost", size="sm", on_click=ChatAppState.clear_history),
                    Button("🚪 Logout", variant="outline", size="sm", on_click=ChatAppState.logout),
                    gap="sm", align="center"
                ),
                justify="space-between", align="center", class_name="max-w-4xl mx-auto p-4"
            ),
            class_name="border-b border-border bg-card/60 backdrop-blur-xl sticky top-0 z-40"
        )
    )

    # 2. Chat Conversation & Tool Trace Panel
    chat_panel = ShadCard(
        ShadCardHeader(
            Flex(
                Div(
                    ShadCardTitle("Agent Conversation & Tool Calls"),
                    ShadCardDescription("Live execution trace of LangGraph agent & tools"),
                ),
                ShadBadge("Live Trace", variant="secondary", class_name="text-[11px] font-mono"),
                justify="space-between", align="center"
            ),
            class_name="p-4 pb-3 border-b border-border/60"
        ),
        ShadCardContent(
            Div(
                # Chat Messages feed
                render_chat_stream(ChatAppState.history),

                # Status Bar
                Div(
                    Span("Status: ", class_name="text-xs text-muted-foreground font-semibold"),
                    Span(ChatAppState.status_text, class_name="text-xs text-foreground font-mono"),
                    class_name="py-2 px-3 rounded-md bg-muted/40 border border-border/60 my-2"
                ),

                # Suggested Chips
                Flex(
                    Button("🔍 Check My Purchase", variant="outline", size="xs", on_click=ChatAppState.run_sample_lookup),
                    Button("🧾 Generate My Invoice", variant="outline", size="xs", on_click=ChatAppState.run_sample_invoice),
                    Button("📋 View Account Details", variant="outline", size="xs", on_click=ChatAppState.run_sample_columns),
                    gap="xs", wrap="wrap", class_name="mb-3"
                ),

                # Message Input Form
                Form(
                    Flex(
                        Input(
                            bind=ChatAppState.user_input,
                            placeholder="Type a message or instruction... (e.g. Check my purchase details)",
                            size="md",
                            class_name="flex-1"
                        ),
                        Button(
                            Span("Send 🚀", class_name="send-btn-label"),
                            Span("Thinking... ⏳", class_name="send-btn-loading hidden"),
                            variant="primary",
                            size="md",
                            type="submit",
                            id="send-btn"
                        ),
                        gap="sm", align="center"
                    ),
                    on_submit=ChatAppState.send_message
                ),

                # Interactive HTMX Request Lifecycle Script for instant loading animations
                Html("""
                <script>
                document.addEventListener('htmx:beforeRequest', function(evt) {
                    var indicator = document.getElementById('chat-loading-indicator');
                    if (indicator) {
                        indicator.classList.remove('hidden');
                        indicator.classList.add('flex');
                    }
                    var btn = document.getElementById('send-btn');
                    if (btn) {
                        btn.setAttribute('disabled', 'true');
                        var lbl = btn.querySelector('.send-btn-label');
                        var load = btn.querySelector('.send-btn-loading');
                        if (lbl) lbl.classList.add('hidden');
                        if (load) load.classList.remove('hidden');
                    }
                    var feed = document.getElementById('chat-messages-container');
                    if (feed) feed.scrollTop = feed.scrollHeight;
                });
                document.addEventListener('htmx:afterRequest', function(evt) {
                    var indicator = document.getElementById('chat-loading-indicator');
                    if (indicator) {
                        indicator.classList.add('hidden');
                        indicator.classList.remove('flex');
                    }
                    var btn = document.getElementById('send-btn');
                    if (btn) {
                        btn.removeAttribute('disabled');
                        var lbl = btn.querySelector('.send-btn-label');
                        var load = btn.querySelector('.send-btn-loading');
                        if (lbl) lbl.classList.remove('hidden');
                        if (load) load.classList.add('hidden');
                    }
                    var feed = document.getElementById('chat-messages-container');
                    if (feed) feed.scrollTop = feed.scrollHeight;
                });
                </script>
                """),

                class_name="flex flex-col h-[650px] p-2"
            )
        ),
        class_name="w-full border-border shadow-lg"
    )

    # 2. In-Chat Temporary API Key Configuration Drawer
    key_drawer = Div(
        ShadCard(
            ShadCardHeader(
                Flex(
                    Div(
                        ShadCardTitle("🔑 Temporary API Key Configuration (In-Memory)"),
                        ShadCardDescription("Enter your Groq or Gemini API key. Stored only in RAM (os.environ) for this active session — never saved permanently to disk or .env."),
                    ),
                    Button("✕ Close", variant="ghost", size="xs", on_click=ChatAppState.toggle_key_drawer),
                    justify="space-between", align="center"
                ),
                class_name="p-4 pb-2 border-b border-border/60"
            ),
            ShadCardContent(
                Div(
                    Flex(
                        Input(
                            bind=ChatAppState.ui_api_key_input,
                            type="password",
                            placeholder="Paste your Groq (gsk_...) or Gemini (AIza...) API key here...",
                            size="sm",
                            class_name="flex-1"
                        ),
                        Button("💾 Apply Key", variant="primary", size="sm", on_click=ChatAppState.apply_ui_api_key),
                        Button("🗑️ Clear Key", variant="destructive", size="sm", on_click=ChatAppState.clear_ui_api_key),
                        gap="sm", align="center"
                    ),
                    Div(
                        Span(ChatAppState.key_status_message, class_name="text-xs font-mono text-emerald-400 block mt-2")
                    ) if ChatAppState.key_status_message else Div(),
                    class_name="p-3"
                )
            ),
            class_name="mb-4 border-amber-500/40 bg-zinc-950/90 shadow-xl"
        )
    ) if ChatAppState.show_key_drawer else Div()

    # Main Layout
    return Section(
        header,
        Main(
            Container(
                key_drawer,
                chat_panel,
                class_name="max-w-4xl mx-auto p-4"
            )
        ),
        class_name="min-h-screen bg-background"
    )


chat_app = app

# ----------------------------------------------------------------------
# 6. Application Entrypoint
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
