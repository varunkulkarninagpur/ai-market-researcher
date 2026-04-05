import os
import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.messages import SystemMessage, HumanMessage

# --- 1. Streamlit UI Setup ---
st.set_page_config(page_title="AI Research Firm", page_icon="📈", layout="centered")

with st.sidebar:
    st.header("⚙️ Configuration")
    # This is a massive portfolio flex: never hardcode API keys in UI apps!
    api_key = st.text_input("Enter Groq API Key:", type="password")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
    st.markdown("---")
    st.markdown("**Architecture:**")
    st.markdown("- **Agent 1:** Web Researcher")
    st.markdown("- **Agent 2:** Business Analyst")
    st.markdown("- **Memory:** LangGraph Checkpoints")
    st.markdown("- **LLM:** Llama 3.3 70B (Groq)")

st.title("🤖 Multi-Agent Market Research")
st.write("Enter a market or industry to generate a data-driven SWOT analysis.")

# --- 2. Graph State & Nodes ---
class MarketResearchState(TypedDict):
    topic: str
    research_content: str
    swot_analysis: str

def researcher_agent(state: MarketResearchState):
    topic = state["topic"]
    search_tool = DuckDuckGoSearchResults()
    raw_search_results = search_tool.invoke(f"latest market data and statistics for {topic}")
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)
    system_prompt = """You are a senior market research assistant. 
    Read raw web search results and extract hard facts, statistics, and key players.
    Output a clean, bulleted list of the most important data points."""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Topic: {topic}\n\nRaw Search Data:\n{raw_search_results}")
    ])
    return {"research_content": response.content}

def analyst_agent(state: MarketResearchState):
    topic = state["topic"]
    research = state["research_content"] 
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)
    system_prompt = """You are a brilliant strategic business analyst.
    Convert raw market research into a professional SWOT Analysis (Strengths, Weaknesses, Opportunities, Threats).
    Use clear Markdown formatting. Base analysis STRICTLY on the provided data."""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Topic: {topic}\n\nResearch Data:\n{research}")
    ])
    return {"swot_analysis": response.content}

# --- 3. Build & Cache the Graph ---
# We cache the graph compilation so Streamlit doesn't rebuild it on every button click
@st.cache_resource
def build_graph():
    builder = StateGraph(MarketResearchState)
    builder.add_node("Researcher", researcher_agent)
    builder.add_node("Analyst", analyst_agent)
    builder.set_entry_point("Researcher")
    builder.add_edge("Researcher", "Analyst")
    builder.add_edge("Analyst", END)
    memory = MemorySaver()
    # Still pausing before the Analyst!
    return builder.compile(checkpointer=memory, interrupt_before=["Analyst"])

graph = build_graph()

# --- 4. Streamlit App Logic ---
# Session state to keep track of our thread
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "ui_run_1"

topic = st.text_input("What market should we research?", placeholder="e.g., EV battery recycling startups")

if st.button("Start Research Phase"):
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar first!")
    elif topic:
        with st.spinner("Agent 1 (Researcher) is scouring the web..."):
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            initial_state = {"topic": topic, "research_content": "", "swot_analysis": ""}
            
            # Run up to the breakpoint
            graph.invoke(initial_state, config)
            st.success("Research complete! Awaiting human approval.")

# Check the current state of the graph
config = {"configurable": {"thread_id": st.session_state.thread_id}}
current_state = graph.get_state(config)

# If the graph is paused at our breakpoint, show the approval UI
if current_state.next == ('Analyst',):
    st.markdown("### 🚨 Human Approval Required")
    st.info("Please review Agent 1's research before authorizing Agent 2 to run the analysis.")
    
    with st.expander("View Raw Research Data", expanded=True):
        st.markdown(current_state.values.get("research_content", ""))
        
    if st.button("✅ Approve Data & Generate SWOT", type="primary"):
        with st.spinner("Agent 2 (Analyst) is building the strategy..."):
            # Passing None tells LangGraph to resume from the pause
            graph.invoke(None, config)
            st.rerun() # Refresh the page to show final output

# If the graph is completely finished, show the final SWOT and download button
if current_state.values.get("swot_analysis") and not current_state.next:
    st.markdown("### 🧠 Final SWOT Analysis")
    swot_text = current_state.values.get("swot_analysis")
    st.markdown(swot_text)
    
    # Replaces the Editor Agent by allowing browser downloads
    st.download_button(
        label="Download Report (.md)",
        data=f"# Market Research Report: {current_state.values.get('topic')}\n\n## 1. Raw Market Data\n{current_state.values.get('research_content')}\n\n## 2. SWOT Analysis\n{swot_text}",
        file_name=f"{current_state.values.get('topic').replace(' ', '_').lower()}_report.md",
        mime="text/markdown"
    )