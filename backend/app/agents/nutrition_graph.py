from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    NutritionGraphState,
    analyze_goal,
    generate_smoothie_plan_node,
    safety_check,
)
from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothiePlanResponse


def build_nutrition_graph():
    graph = StateGraph(NutritionGraphState)

    graph.add_node("analyze_goal", analyze_goal)
    graph.add_node("generate_smoothie_plan", generate_smoothie_plan_node)
    graph.add_node("safety_check", safety_check)

    graph.add_edge(START, "analyze_goal")
    graph.add_edge("analyze_goal", "generate_smoothie_plan")
    graph.add_edge("generate_smoothie_plan", "safety_check")
    graph.add_edge("safety_check", END)

    return graph.compile()


nutrition_graph = build_nutrition_graph()


def run_nutrition_graph(profile: ProfileInput) -> SmoothiePlanResponse:
    result = nutrition_graph.invoke({"profile": profile})
    return result["smoothie_plan"]
