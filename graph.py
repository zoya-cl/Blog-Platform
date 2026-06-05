from langgraph.graph import StateGraph, END
from schemas import BlogState
from agents.intake import intake_node
from agents.planner import planner_node
from agents.writer import writer_async, coherence_editor
from agents.assembler import assembler
from agents.hallucination_detector import hallucination_detector
from agents.rewriter import hallucination_rewriter, quality_rewriter
from agents.quality import quality_node
import config

def publish_node(state: BlogState) -> dict:
    """
    Final node that cleans up the state, counts the final words, and sets the final output.
    """
    print("\n--- Running Node: Publish Node ---")
    draft = state.get("assembled_draft", "")
    metadata = state.get("metadata", {})
    
    # Calculate final word count
    word_count = len(draft.split())
    metadata["word_count"] = word_count
    
    # Sync final quality score if graded
    quality_scores = state.get("quality_scores", {})
    if "overall_score" in quality_scores:
        metadata["quality_score"] = float(quality_scores["overall_score"])
        
    # Sync revision counts
    metadata["revision_count"] = (
        state.get("hallucination_revision_count", 0) +
        state.get("quality_revision_count", 0) +
        state.get("seo_revision_count", 0)
    )
    
    return {
        "final_blog": draft,
        "metadata": metadata
    }

# -------------------------------------------------------------
# Conditional Routers
# -------------------------------------------------------------

def hallucination_gate(state: BlogState) -> str:
    """
    Checks if the draft contains hallucinations. Routes to rewriter if issues exist, else to quality.
    """
    report = state.get("hallucination_report", {})
    has_hallucinations = report.get("has_hallucinations", False)
    revision_count = state.get("hallucination_revision_count", 0)
    max_revisions = config.RETRY_CAPS.get("hallucination_rewriter", 2)
    
    if has_hallucinations and revision_count < max_revisions:
        print(f"Hallucination Gate: Hallucinations detected (Revision {revision_count}/{max_revisions}). Routing to rewriter.")
        return "hallucination_rewriter"
        
    print("Hallucination Gate: No hallucinations or revision limit reached. Routing to quality check.")
    return "quality_node"

def quality_gate(state: BlogState) -> str:
    """
    Checks if the blog draft passes the quality threshold. Routes to rewriter if failing, else directly to final safeguard.
    """
    scores = state.get("quality_scores", {})
    overall_score = scores.get("overall_score", 0.0)
    revision_count = state.get("quality_revision_count", 0)
    max_revisions = config.RETRY_CAPS.get("quality_rewriter", 2)
    threshold = config.QUALITY_GATE_THRESHOLD
    
    if overall_score < threshold and revision_count < max_revisions:
        print(f"Quality Gate: Score {overall_score:.2f} < Threshold {threshold} (Revision {revision_count}/{max_revisions}). Routing to rewriter.")
        return "quality_rewriter"
        
    print(f"Quality Gate: Score {overall_score:.2f} passed or revision limit reached. Routing to final safeguard check.")
    return "final_hallucination_check"

def final_hallucination_check(state: BlogState) -> dict:
    """
    A lightweight, final non-looping hallucination safeguard node that runs after the Quality/SEO edits.
    It runs detection once, and if any new hallucinations were introduced by the quality editor,
    it applies a targeted revision pass once before publishing.
    """
    print("\n--- Running Node: Final Lightweight Hallucination Check ---")
    # Run the detector logic on the state
    detector_out = hallucination_detector(state)
    
    # Merge detector outputs to check report
    detector_state = {**state, **detector_out}
    report = detector_state.get("hallucination_report", {})
    has_hallucinations = report.get("has_hallucinations", False)
    
    if has_hallucinations:
        print("Final Safeguard: Quality rewrites introduced new hallucinations. Running targeted rewrite...")
        # Run hallucination rewriter exactly once to resolve them
        rewriter_out = hallucination_rewriter(detector_state)
        return {
            "assembled_draft": rewriter_out.get("assembled_draft", state.get("assembled_draft")),
            "hallucination_report": report
        }
    
    print("Final Safeguard: No new hallucinations detected. Proceeding to Publish.")
    return {}

# -------------------------------------------------------------
# Graph Definition
# -------------------------------------------------------------

# Initialize the StateGraph
workflow = StateGraph(BlogState)

# Add all nodes
workflow.add_node("intake_node", intake_node)
workflow.add_node("planner_node", planner_node)
workflow.add_node("writer_async", writer_async)
workflow.add_node("coherence_editor", coherence_editor)
workflow.add_node("assembler", assembler)
workflow.add_node("hallucination_detector", hallucination_detector)
workflow.add_node("hallucination_rewriter", hallucination_rewriter)
workflow.add_node("quality_node", quality_node)
workflow.add_node("quality_rewriter", quality_rewriter)
workflow.add_node("final_hallucination_check", final_hallucination_check)
workflow.add_node("publish_node", publish_node)

# Set Entry Point
workflow.set_entry_point("intake_node")

# Setup static edges
workflow.add_edge("intake_node", "planner_node")
workflow.add_edge("planner_node", "writer_async")
workflow.add_edge("writer_async", "coherence_editor")
workflow.add_edge("coherence_editor", "assembler")

from agents.image_planner import image_planner_node
from agents.image_generator import image_generator_node

# Connect assembler to evaluation nodes (via image generation stage)
workflow.add_node("image_planner", image_planner_node)
workflow.add_node("image_generator", image_generator_node)

workflow.add_edge("assembler", "image_planner")
workflow.add_edge("image_planner", "image_generator")
workflow.add_edge("image_generator", "hallucination_detector")

# Hallucination evaluation & routing
workflow.add_conditional_edges(
    "hallucination_detector",
    hallucination_gate,
    {
        "hallucination_rewriter": "hallucination_rewriter",
        "quality_node": "quality_node"
    }
)
workflow.add_edge("hallucination_rewriter", "hallucination_detector")

# Quality evaluation & routing
workflow.add_conditional_edges(
    "quality_node",
    quality_gate,
    {
        "quality_rewriter": "quality_rewriter",
        "final_hallucination_check": "final_hallucination_check"
    }
)
workflow.add_edge("quality_rewriter", "quality_node")

# Final safeguard to publish edge
workflow.add_edge("final_hallucination_check", "publish_node")

# End edge
workflow.add_edge("publish_node", END)

# Compile Graph
graph = workflow.compile()
