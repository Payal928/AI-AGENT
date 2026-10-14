import json
import os
import requests
import streamlit as st
import yfinance as yf
from openai import OpenAI
from urllib.parse import quote


# ---------------- LLM SETUP (Ollama) ----------------

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
BASE_MODEL = "ministral-3:latest"


# ---------------- YOUR TOOLS (unchanged) ----------------


def get_weather(city: str):
    '''
    Helps to get the weather details of any specific city.
    Returns a success or failure message.
    '''
    url = f"https://wttr.in/{quote(city)}?format=%C+%t"
    headers = {
        "User-Agent": "curl/8.0"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return f"The weather in {city} is {response.text.strip()}"
        else:
            return f"Error: Received status code {response.status_code}"
    except requests.RequestException as e:
        return f"Something went wrong: {e}"


def write_to_file(filename: str, content: str):
    '''
    Writes the content to a file with UTF-8 encoding.
    Returns a success or failure message.
    '''
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"file '{filename}' created successfully."
    except Exception as e:
        return f"Failed to write file: {e}"


def realtime_stock_price(symbol: str):
    '''
    Gets the latest stock price for a ticker symbol.
    Example symbols: AAPL, TSLA, RELIANCE.NS (NSE), TCS.BO (BSE)
    '''
    try:
        price = yf.Ticker(symbol).fast_info["last_price"]
        return f"The latest price of {symbol} is {price:.2f}"
    except Exception as e:
        return f"Failed to fetch price for {symbol}: {e}"


available_tools = {
    "get_weather": get_weather,
    "write_to_file": write_to_file,
    "realtime_stock_price": realtime_stock_price,
}

# ---------------- SYSTEM PROMPT ----------------
# Plain string (not an f-string), so single braces are correct.

SYSTEM_PROMPT = '''
You are a helpful AI assistant who resolves the user query using tools.
You work in plan, action, observe and output steps.

Rules:
- Return exactly ONE JSON object per response.
- Perform one step at a time and wait for the next input.
- You DO have the tools listed below. Never say you cannot use them.
- After you receive an OBSERVATION, your next response must be step "output", unless another tool is still needed.
- Answer in English. Do not give extra advice.
- For stock prices, convert the company name to a ticker (Indian: add .NS, e.g. TCS.NS. US: plain, e.g. AAPL).

Output JSON format:
{"step": "plan | action | output", "content": "your thinking", "function": "tool name (action only)", "input": "tool input (action only)", "output": "final answer (output only)"}

Available Tools:
- "get_weather": input is a city name string. Returns current weather.
- "realtime_stock_price": input is a ticker symbol string. Returns the latest price.
- "write_to_file": input is {"filename": "name.ext", "content": "file text"}. Saves the file.

Example 1:
User query: What is the weather of <CITY>?
{"step": "plan", "content": "I should call get_weather"}
{"step": "action", "function": "get_weather", "input": "<CITY>"}
(you then receive the observation)
{"step": "output", "output": "Short answer using the observation"}

Example 2:
User query: What is the latest stock price of <COMPANY>?
{"step": "plan", "content": "I need the ticker symbol, then call realtime_stock_price"}
{"step": "action", "function": "realtime_stock_price", "input": "<SYMBOL>"}
(you then receive the observation)
{"step": "output", "output": "Short answer using the observation"}
'''


# ---------------- AGENT LOOP (shows every step on the dashboard) ----------------

def run_agent_on_dashboard(user_query: str, max_steps: int = 10):
    messages = [{"role": "user", "content": user_query}]
    plan_count = 0

    for _ in range(max_steps):
        try:
            response = client.chat.completions.create(
                model=BASE_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
                temperature=0,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            st.error(f"Could not reach Ollama: {e}")
            return

        response_text = response.choices[0].message.content
        if not response_text or not response_text.strip():
            st.error("Model returned an empty response.")
            return

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            st.error(f"Model returned invalid JSON: {response_text}")
            return

        messages.append({"role": "assistant", "content": response_text})
        step = parsed.get("step")

        # ---- PLAN ----
        if step == "plan":
            plan_count += 1
            st.info(f"🧠 **LLM THINKS..** {parsed.get('content')}")
            if plan_count >= 3:
                messages.append({
                    "role": "user",
                    "content": "Stop planning. Return step 'action' or step 'output' now.",
                })

        # ---- ACTION ----
        elif step == "action":
            plan_count = 0
            tool_name = parsed.get("function")
            tool_input = parsed.get("input")
            st.warning(f"⚙️ **LLM takes action** with tool: `{tool_name}` and input: `{tool_input}`")

            if tool_name not in available_tools:
                output = f"Tool '{tool_name}' does not exist."
            else:
                try:
                    with st.spinner(f"Calling {tool_name}..."):
                        if isinstance(tool_input, dict):
                            output = available_tools[tool_name](**tool_input)
                        else:
                            output = available_tools[tool_name](tool_input)
                except Exception as e:
                    output = f"Tool failed: {e}. Check the argument names and try again."

            st.code(output, language="text")   # the observation
            st.caption("👀 Observation from the tool")

            messages.append({
                "role": "user",
                "content": (
                    f"OBSERVATION from tool '{tool_name}': {output}\n"
                    'If this answers the user, reply NOW with {"step": "output", "output": "<answer>"}. '
                    "Do not plan again."
                ),
            })

        # ---- OUTPUT ----
        elif step == "output":
            st.success(f"✅ **Final answer:** {parsed.get('output')}")
            return

        else:
            st.error(f"Unknown step: {parsed}")
            return

    st.error("Stopped: too many steps.")


# ---------------- STREAMLIT INTERFACE ----------------

st.set_page_config(page_title="AI Agent Dashboard", page_icon="🤖", layout="wide")


# ---------- Theme (same design + larger fonts) ----------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 55%, #0f172a 100%);
    font-size: 20px;
}

.stApp, .stApp p, .stApp label, .stApp li {
    color: #e2e8f0;
    font-size: 21px !important;
    line-height: 1.6;
}

/* Sidebar - same background and border */
[data-testid="stSidebar"] {
    background: #0b1120;
    border-right: 1px solid #334155;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    font-size: 20px !important;
    line-height: 1.6 !important;
}

[data-testid="stSidebar"] h2 {
    font-size: 28px !important;
}

/* Hero banner - same design */
.hero {
    padding: 34px 38px;
    border-radius: 20px;
    background: linear-gradient(120deg, #6366f1 0%, #8b5cf6 50%, #06b6d4 100%);
    box-shadow: 0 10px 40px rgba(99,102,241,0.35);
    margin-bottom: 26px;
}

.hero h1 {
    color: #ffffff;
    font-size: 2.8rem;
    margin: 0;
    font-weight: 800;
}

.hero p {
    color: #e0e7ff;
    font-size: 23px !important;
    margin: 12px 0 0 0;
}

/* Badges - same colors and shape */
.badge {
    display: inline-block;
    padding: 7px 15px;
    margin: 14px 8px 0 0;
    border-radius: 999px;
    background: rgba(255,255,255,0.18);
    color: #ffffff;
    font-size: 19px !important;
    font-weight: 600;
}

/* Tool cards - same layout and styling */
.tool-card {
    padding: 22px;
    border-radius: 16px;
    height: 100%;
    background: rgba(30,41,59,0.85);
    border: 1px solid #475569;
    border-top: 4px solid var(--accent);
}

.tool-card h3 {
    color: #ffffff;
    font-size: 27px !important;
    margin: 0 0 10px 0;
}

.tool-card code {
    color: #67e8f9;
    background: #0f172a;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 19px !important;
}

.tool-card p {
    color: #cbd5e1;
    font-size: 21px !important;
    line-height: 1.6 !important;
    margin: 12px 0 0 0;
}

.tool-card .why {
    color: #fcd34d;
    font-weight: 600;
}

/* Model information card - same design */
.model-card {
    padding: 18px;
    border-radius: 14px;
    background: linear-gradient(135deg, #1e293b, #312e81);
    border: 1px solid #6366f1;
}

.model-card h4 {
    color: #ffffff;
    margin: 0 0 10px 0;
    font-size: 25px !important;
}

.model-card p {
    color: #c7d2fe;
    margin: 5px 0;
    font-size: 20px !important;
    line-height: 1.6 !important;
}

/* Try these suggestions - same design */
.try-label {
    font-size: 22px !important;
    font-weight: 700;
    margin-bottom: 8px;
}

.try-chip {
    display: inline-block;
    font-size: 19px !important;
    line-height: 1.6;
    padding: 6px 10px;
    margin: 4px 5px 4px 0;
    background: #27345b;
    color: #ffffff;
    border-radius: 8px;
}

/* Input field - same background and border */
.stTextInput label {
    font-size: 22px !important;
    color: #ffffff !important;
}

.stTextInput input {
    background: #1e293b;
    color: #ffffff;
    border: 1px solid #6366f1;
    border-radius: 10px;
    font-size: 22px !important;
    padding: 12px;
}

/* Buttons - same gradient and shape */
.stButton > button {
    background: linear-gradient(90deg, #6366f1, #06b6d4);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 28px;
    font-weight: 700;
    font-size: 21px !important;
}

.stButton > button:hover {
    filter: brightness(1.15);
    color: #ffffff;
}

/* Headings - same colors */
h1, h2, h3, h4 {
    color: #ffffff !important;
}

/* Agent steps and other Streamlit messages */
[data-testid="stMarkdownContainer"] p {
    font-size: 21px !important;
    line-height: 1.6 !important;
}

[data-testid="stAlert"] p {
    font-size: 21px !important;
}

/* Code and captions */
.stCaption, [data-testid="stCaptionContainer"] {
    font-size: 19px !important;
}

/* Same responsive layout */
@media (max-width: 768px) {
    .hero {
        padding: 24px;
    }

    .hero h1 {
        font-size: 2rem;
    }

    .hero p {
        font-size: 21px !important;
    }

    .tool-card p {
        font-size: 19px !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ---------- Hero banner ----------
st.markdown(f"""
<div class="hero">
<h1>🤖 AI Agent Dashboard</h1>
<p>An autonomous agent that plans, picks a tool, acts, observes and answers.</p>
<span class="badge">🦙 Ollama (local)</span>
<span class="badge">🧠 Model: {BASE_MODEL}</span>
<span class="badge">🔁 Plan → Action → Observe → Output</span>
</div>
""", unsafe_allow_html=True)


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🛠️ Available Tools")
    st.markdown("""
<p style="font-size:1.05rem;"><b>🌤️ get_weather</b><br>
<span style="color:#94a3b8;">Live weather of any city</span></p>
<p style="font-size:1.05rem;"><b>📈 realtime_stock_price</b><br>
<span style="color:#94a3b8;">Latest price of a stock ticker</span></p>
<p style="font-size:1.05rem;"><b>📝 write_to_file</b><br>
<span style="color:#94a3b8;">Saves text into a file</span></p>
""", unsafe_allow_html=True)

    st.divider()

    st.markdown(f"""
<div class="model-card">
<h4>🧠 LLM Engine</h4>
<p><b>Runtime:</b> Ollama (runs locally)</p>
<p><b>Model:</b> {BASE_MODEL}</p>
<p><b>Provider:</b> Mistral AI</p>
<p><b>Temperature:</b> 0</p>
</div>
""", unsafe_allow_html=True)


# ---------- Tool cards ----------
st.markdown("## 🧰 Tools the agent can use")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
<div class="tool-card" style="--accent:#38bdf8;">
<h3>🌤️ Weather</h3>
<code>get_weather</code>
<p>Fetches the current weather of a city from wttr.in.</p>
<p class="why">Why: an LLM cannot know today's weather, so it calls this tool.</p>
</div>
""", unsafe_allow_html=True)

with c2:
    st.markdown("""
<div class="tool-card" style="--accent:#34d399;">
<h3>📈 Stock Price</h3>
<code>realtime_stock_price</code>
<p>Gets the latest traded price of a ticker using yfinance.</p>
<p class="why">Why: stock prices change every second, so the model's memory is useless here.</p>
</div>
""", unsafe_allow_html=True)

with c3:
    st.markdown("""
<div class="tool-card" style="--accent:#f472b6;">
<h3>📝 File Writer</h3>
<code>write_to_file</code>
<p>Creates a file with the given name and content.</p>
<p class="why">Why: an LLM can only produce text, so this tool lets it act on your computer.</p>
</div>
""", unsafe_allow_html=True)

st.write("")


# ---------- Query section ----------
st.markdown("## 💬 Ask the agent")

st.markdown("""
<div class="try-label">💡 Try these:</div>
<span class="try-chip">What is the weather of Delhi?</span>
<span class="try-chip">What is the latest stock price of TCS?</span>
<span class="try-chip">Create a file hello.txt with the text hello world</span>
""", unsafe_allow_html=True)

query = st.text_input(
    "Enter your query",
    placeholder="What is the weather of Delhi?"
)

if st.button("🚀 Run agent"):
    if query.strip():
        st.divider()
        st.markdown("## 🔍 Agent steps")
        run_agent_on_dashboard(query.strip())
    else:
        st.warning("Please type a query.")
