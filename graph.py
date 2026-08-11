from langgraph.graph import StateGraph, END
from schemas import BlogState
from agents.planner import planner_node
from agents.writer import writer_async
from agents.assembler import assembler
from agents.quality import quality_node, quality_rewriter
import config

def publish_node(state: BlogState) -> dict:
    """
    Final node that cleans up the state, counts the final words, and sets the final output.
    """
    print("\n--- Running Node: Publish Node ---")
    draft = state.get("assembled_draft", "")
    metadata = state.get("metadata", {})
    
    word_count = len(draft.split())
    metadata["word_count"] = word_count
    
    quality_scores = state.get("quality_scores", {})
    if "overall_score" in quality_scores:
        metadata["quality_score"] = float(quality_scores["overall_score"])
        
    metadata["revision_count"] = state.get("quality_revision_count", 0)
    
    return {
        "final_blog": draft,
        "metadata": metadata
    }

def quality_gate(state: BlogState) -> str:
    """
    Quality evaluation router with max 1 retry pass.
    """
    scores = state.get("quality_scores", {})
    overall_score = scores.get("overall_score", 0.0)
    revision_count = state.get("quality_revision_count", 0)
    max_revisions = 1
    threshold = config.QUALITY_GATE_THRESHOLD
    
    if overall_score < threshold and revision_count < max_revisions:
        print(f"Quality Gate: Score {overall_score:.2f} < Threshold {threshold} (Revision {revision_count}/{max_revisions}). Routing to quality_rewriter.")
        return "quality_rewriter"
        
    print(f"Quality Gate: Score {overall_score:.2f} passed or retry cap reached. Routing to publish_node.")
    return "publish_node"

# -------------------------------------------------------------
# Graph Definition
# -------------------------------------------------------------

workflow = StateGraph(BlogState)

# Add nodes
workflow.add_node("planner_node", planner_node)
workflow.add_node("writer_async", writer_async)
workflow.add_node("assembler", assembler)
workflow.add_node("quality_node", quality_node)
workflow.add_node("quality_rewriter", quality_rewriter)
workflow.add_node("publish_node", publish_node)

# Set Entry Point
workflow.set_entry_point("planner_node")

# Setup static edges
workflow.add_edge("planner_node", "writer_async")
workflow.add_edge("writer_async", "assembler")
workflow.add_edge("assembler", "quality_node")

# Quality evaluation conditional routing
workflow.add_conditional_edges(
    "quality_node",
    quality_gate,
    {
        "quality_rewriter": "quality_rewriter",
        "publish_node": "publish_node"
    }
)
workflow.add_edge("quality_rewriter", "quality_node")
workflow.add_edge("publish_node", END)

# Compile Graph
graph = workflow.compile()
