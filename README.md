# AI-AGENT
A basic AI Agent built with Python, Ollama, and the Ministral model. It uses a manually implemented while loop for tool calling and execution without LangChain or LangGraph. The agent can fetch real-time weather, retrieve stock prices, and create files through Python functions, with an interactive Streamlit dashboard.


# 🤖 AI Agent using Python and Ollama

A basic AI Agent built using Python, Ollama, and the Ministral model. It can understand user queries, select appropriate tools, execute tasks, and generate responses through a manually implemented `while` loop without using LangChain or LangGraph.

## 🧠 What is an LLM?

A Large Language Model (LLM) is like the brain of an AI system. It understands user queries and generates responses based on its training and the context provided. However, it cannot automatically fetch real-time information or perform external actions without tools.

## 🤖 What is an AI Agent?

An AI Agent extends an LLM with the ability to use tools and perform tasks. The LLM helps decide what action to take, while Python functions execute the actual operations.

## 🦙 Why Ollama and Ministral?

- **Ollama:** Runs supported language models locally on your computer without requiring a hosted LLM inference API.
- **Ministral:** The language model used to interpret user queries and help select appropriate tools.

## 🛠️ Available Tools

- 🌦️ **`get_weather`** — Fetches current weather information for a city.
- 📈 **`realtime_stock_price`** — Retrieves available stock-price data using `yfinance`.
- 📄 **`write_to_file`** — Creates a file with the specified name and content.

## 🔄 Workflow

**User Query → Plan → Action → Observation → Final Output**

The Python `while` loop manages tool selection, execution, and observations until the agent reaches a stopping condition.

This is an example of **manual orchestration and iterative execution**. Although it involves multiple steps, an agent loop is not the same as Chain of Thought (CoT).

## ⚙️ Why No LangChain or LangGraph?

I implemented the workflow manually to understand how tool calling, Python functions, observations, and agent execution work behind the scenes before using orchestration frameworks.

## 🧰 Technologies Used

- Python
- Ollama
- Ministral model
- Streamlit
- yfinance
- Python HTTP utilities

## 🚀 Run the Project

```bash
pip install streamlit ollama yfinance openai python-dotenv requests
ollama pull ministral-3:latest
streamlit run app.py
```

Make sure the model tag and application filename match your code.

## 🎯 Learning Outcomes

- Understanding LLMs and AI Agents
- Implementing tool calling with Python
- Building a manual agent loop using `while`
- Integrating external data sources
- Creating an interactive Streamlit dashboard

**My first hands-on AI Agent project — learning by building!** 🚀
