
import os
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.messages import SystemMessage, HumanMessage

# --- 1. Authentication & Setup ---
os.environ["GROQ_API_KEY"] = "gsk_your_api_key_here" # KEEP YOUR KEY HERE!

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)
search_tool = DuckDuckGoSearchResults()

# --- 2. Define the State ---
class MarketResearchState(TypedDict):
    topic: str
    research_content: str
    swot_analysis: str
    human_feedback: str








# --- 3. Node Definitions (Our Agents) ---
def researcher_agent(state: MarketResearchState):
    print("\n[🔎] RESEARCHER: Gathering data from the web...")
    topic = state["topic"]
    
    raw_search_results = search_tool.invoke(f"latest market data and statistics for {topic}")
    
    system_prompt = """You are a senior market research assistant. 
    Your job is to read raw web search results and extract hard facts, statistics, and key players.
    Do NOT write an essay. Output a clean, bulleted list of the most important data points.
    If the data is irrelevant, state that you couldn't find good data."""
    
    human_prompt = f"Topic: {topic}\n\nRaw Search Data:\n{raw_search_results}"
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])
    
    print("[✅] RESEARCHER: Data gathered.")
    return {"research_content": response.content}






def analyst_agent(state: MarketResearchState):
    print("\n[🧠] ANALYST: Analyzing research and building SWOT...")
    topic = state["topic"]
    research = state["research_content"] 
    
    system_prompt = """You are a brilliant strategic business analyst.
    Your job is to read raw market research and convert it into a professional SWOT Analysis (Strengths, Weaknesses, Opportunities, Threats).
    Use clear Markdown formatting. Be concise but insightful. 
    You must base your analysis STRICTLY on the provided research data."""
    
    human_prompt = f"Topic: {topic}\n\nResearch Data:\n{research}"
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])
    
    print("[✅] ANALYST: SWOT Analysis complete.")
    return {"swot_analysis": response.content}








def editor_agent(state: MarketResearchState):
    print("\n[📝] EDITOR: Formatting and saving to file...")
    
    # Create a safe filename based on the topic
    safe_topic = state["topic"].replace(" ", "_").lower()
    filename = f"{safe_topic}_report.md"
    
    # Write the research and SWOT to a local Markdown file
    with open(filename, "w", encoding="utf-8") as file:
        file.write(f"# Market Research Report: {state['topic']}\n\n")
        file.write("## 1. Raw Market Data\n")
        file.write(state["research_content"] + "\n\n")
        file.write("## 2. SWOT Analysis\n")
        file.write(state["swot_analysis"] + "\n")
        
    print(f"[✅] EDITOR: File successfully saved as '{filename}'")
    return {} # No need to update the state here






# --- 4. Build the Graph ---
builder = StateGraph(MarketResearchState)

builder.add_node("Researcher", researcher_agent)
builder.add_node("Analyst", analyst_agent)
builder.add_node("Editor", editor_agent)

builder.set_entry_point("Researcher")
builder.add_edge("Researcher", "Analyst")
builder.add_edge("Analyst", "Editor")
builder.add_edge("Editor", END)

memory = MemorySaver()

# THE MAGIC TRICK: We tell the graph to pause BEFORE the Analyst node
graph = builder.compile(checkpointer=memory, interrupt_before=["Analyst"])





# --- 5. Run the Graph with Human-in-the-Loop ---
if __name__ == "__main__":
    print("🚀 Starting the Market Research Firm...")
    
    # We use a new thread_id so memory starts fresh
    config = {"configurable": {"thread_id": "production_run_1"}}
    
    initial_state = {
        "topic": "SaaS startups specializing in AI customer support",
        "research_content": "",
        "swot_analysis": "",
        "human_feedback": ""
    }
    
    # 1. Start the graph. It will run the Researcher and then PAUSE.
    graph.invoke(initial_state, config)
    
    # 2. Get the current state of the graph (The memory right now)
    current_state = graph.get_state(config)
    
    print("\n" + "="*50)
    print("🚨 HUMAN APPROVAL REQUIRED 🚨")
    print("="*50)
    print("\nHere is what the Researcher found:\n")
    print(current_state.values.get("research_content"))
    print("\n" + "="*50)
    
    # 3. Ask the user for permission to continue
    user_input = input("\nPress ENTER to approve this data and generate the SWOT analysis, or type 'quit' to exit: ")
    
    if user_input.lower() != 'quit':
        # 4. By passing `None`, we tell LangGraph to resume from where it paused!
        graph.invoke(None, config)
        print("\n🎉 Workflow complete! Check your project folder for the new .md file.")
    else:
        print("\n🛑 Workflow aborted by user.")