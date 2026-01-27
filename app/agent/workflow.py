from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
import json

from app.gemini import GeminiClient, extract_text_from_video, embed
from app.gemini.json_utils import safe_json_parse
from app.rag import search, upsert
from app.utils.logger import setup_logger
from app.utils.time_tracker import TimeTracker # Using your existing TimeTracker class

logger = setup_logger()

# --- Graph State ---

class AgentState(TypedDict):
    """
    Defines the state of the agent's workflow, including the time tracker.
    """
    resume_text: str
    jd_text: str
    video_file_path: str
    analysis_cache_key: str
    final_result: dict
    vector_search_results: List[dict]
    generated_knowledge: str
    tracker: TimeTracker # Add the tracker instance to the state

# --- Graph Nodes ---

class CareerPilotAgent:
    def __init__(self, gemini_client: GeminiClient, redis_client):
        self.gemini_client = gemini_client
        self.redis_client = redis_client
        self.workflow = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Define the nodes
        workflow.add_node("route_input", self.route_input)
        workflow.add_node("process_video", self.process_video)
        workflow.add_node("check_cache", self.check_cache)
        workflow.add_node("search_vectors", self.search_vectors)
        workflow.add_node("generate_knowledge", self.generate_knowledge)
        workflow.add_node("ingest_knowledge", self.ingest_knowledge)
        workflow.add_node("perform_final_analysis", self.perform_final_analysis)
        workflow.add_node("finalize_output", self.finalize_output)

        # Build the graph
        workflow.set_entry_point("route_input")

        # 1. Route based on input type (video or text)
        workflow.add_conditional_edges(
            "route_input", self.decide_input_path,
            {"video": "process_video", "text": "check_cache"}
        )
        
        # 2. If video, process it, then check cache
        workflow.add_edge("process_video", "check_cache")

        # 3. After checking cache, either exit (hit) or continue (miss)
        workflow.add_conditional_edges(
            "check_cache",
            self.decide_after_cache,
            {
                "continue": "search_vectors",
                "exit": END,  # Corrected: Exit directly on cache hit
            },
        )

        # 4. After searching vectors, decide if we need to generate new knowledge
        workflow.add_conditional_edges(
            "search_vectors", self.decide_to_generate_knowledge,
            {"generate": "generate_knowledge", "augment": "perform_final_analysis"}
        )
        
        # 5. If we generate knowledge, we must ingest it before final analysis
        workflow.add_edge("generate_knowledge", "ingest_knowledge")
        workflow.add_edge("ingest_knowledge", "perform_final_analysis")
        
        # 6. After the main analysis, finalize the output to add the performance report
        workflow.add_edge("perform_final_analysis", "finalize_output")
        
        # 7. The finalization step is the true end of an uncached run
        workflow.add_edge("finalize_output", END)

        return workflow.compile()

    # --- Node Implementations ---

    def route_input(self, state: AgentState):
        """ The entry point, initializes the TimeTracker. """
        logger.info("Agent: Routing input and starting timer.")
        tracker = TimeTracker()
        tracker.mark("agent_workflow_started")
        return {"tracker": tracker}

    def decide_input_path(self, state: AgentState):
        if state.get("video_file_path"): return "video"
        return "text"

    async def process_video(self, state: AgentState):
        logger.info("Agent: Processing video to extract text.")
        extracted_text = await extract_text_from_video(self.gemini_client, state["video_file_path"])
        state["tracker"].mark("video_processed")
        if not extracted_text.get("resume_text") or not extracted_text.get("jd_text"):
            raise ValueError("Could not extract resume or JD from video.")
        return {
            "resume_text": extracted_text["resume_text"],
            "jd_text": extracted_text["jd_text"],
        }

    async def check_cache(self, state: AgentState):
        logger.info("Agent: Checking Redis cache for analysis.")
        key = f"analysis:{hash(state['resume_text'] + state['jd_text'])}"
        cached_result = await self.redis_client.get(key)
        state["tracker"].mark("cache_checked")
        if cached_result:
            logger.info("Agent: Cache hit.")
            # We don't need to add performance metrics to a cached result
            return {"final_result": json.loads(cached_result)}
        logger.info("Agent: Cache miss.")
        return {"analysis_cache_key": key}

    def decide_after_cache(self, state: AgentState):
        if state.get("final_result"): return "exit"
        return "continue"

    async def search_vectors(self, state: AgentState):
        logger.info("Agent: Searching MongoDB for vector context.")
        query_embedding = await embed(self.gemini_client, state["jd_text"])
        state["tracker"].mark("jd_embedded_for_search")
        results = await search(query_embedding, top_k=3)
        state["tracker"].mark("vector_search_complete")
        return {"vector_search_results": results}

    def decide_to_generate_knowledge(self, state: AgentState):
        if not state["vector_search_results"]: return "generate"
        return "augment"

    async def generate_knowledge(self, state: AgentState):
        logger.info("Agent: Generating foundational knowledge from JD.")
        prompt = await self.gemini_client.prompts.get("generate_knowledge")
        formatted_prompt = prompt.format(jd_text=state["jd_text"])
        
        payload = {
            "contents": [{"parts": [{"text": formatted_prompt}]}]
        }
        
        response = await self.gemini_client.call(
            "generate_knowledge", 
            f"{self.gemini_client.chat_model}:generateContent",
            payload
        )
        state["tracker"].mark("knowledge_generated")
        
        try:
            text = response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            logger.error(f"Generate knowledge response invalid: {response}")
            raise ValueError("Invalid response from Gemini")
            
        return {"generated_knowledge": text}

    async def ingest_knowledge(self, state: AgentState):
        logger.info("Agent: Ingesting newly generated knowledge into vector store.")
        embedding = await embed(self.gemini_client, state["generated_knowledge"])
        state["tracker"].mark("knowledge_embedded_for_ingestion")
        document = {
            "text": state["generated_knowledge"], "embedding": embedding,
            "source": "generated_from_jd"
        }
        await upsert(document)
        state["tracker"].mark("knowledge_ingested")
        current_results = state.get("vector_search_results", [])
        current_results.append({"text": state["generated_knowledge"]})
        return {"vector_search_results": current_results}

    async def perform_final_analysis(self, state: AgentState):
        logger.info("Agent: Performing final analysis with retrieved knowledge.")
        logger.debug("=== CURRENT AGENT STATE ===\n" + json.dumps(state, indent=2, ensure_ascii=False))
        # Validate required fields
        if not state.get("resume_text") or not state.get("jd_text"):
            logger.error("Missing resume_text or jd_text in state")
            return {"final_result": {"error": "Missing resume or JD"}}

        if not state.get("vector_search_results"):
            logger.error("Missing vector_search_results in state")
            return {"final_result": {"error": "No vector context"}}

        # Build context safely
        context = "\n".join([res["text"] for res in state["vector_search_results"]])
        prompt = await self.gemini_client.prompts.get("final_analysis")
        formatted_prompt = prompt.format(
            context=context, resume_text=state["resume_text"], jd_text=state["jd_text"],
        )
        
        payload = {
            "contents": [{"parts": [{"text": formatted_prompt}]}]
        }
        
        response = await self.gemini_client.call(
            "final_analysis", 
            f"{self.gemini_client.chat_model}:generateContent",
            payload
        )
        state["tracker"].mark("final_analysis_complete")
        
        try:
            text = response["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            logger.error(f"Final analysis response invalid: {response}")
            raise ValueError("Invalid response from Gemini")
            
        final_result = safe_json_parse(text)
        if cache_key := state.get("analysis_cache_key"):
            await self.redis_client.set(cache_key, json.dumps(final_result), ex=3600)
            state["tracker"].mark("final_result_cached")
        return {"final_result": final_result}

    def finalize_output(self, state: AgentState):
        """Attaches the performance metrics report to the final result."""
        logger.info("Agent: Finalizing output and attaching performance metrics.")
        final_result = state.get("final_result", {})
        tracker = state["tracker"]
        final_result["performance_metrics"] = tracker.report()
        return {"final_result": final_result}

