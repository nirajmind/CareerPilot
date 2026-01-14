from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Optional
import operator
import json

from app.gemini import GeminiClient, extract_text_from_video, embed
from app.rag import search, upsert
from app.utils.logger import setup_logger

logger = setup_logger()

# --- Graph State ---

class AgentState(TypedDict):
    """
    Defines the state of the agent's workflow.
    Handles both text and video inputs.
    """
    resume_text: Optional[str]
    jd_text: Optional[str]
    video_file_path: Optional[str]
    analysis_cache_key: str
    final_result: Annotated[str, operator.setitem]
    vector_search_results: List[dict]
    generated_knowledge: str

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

        # Build the graph
        workflow.set_entry_point("route_input")

        # 1. Route based on input type (video or text)
        workflow.add_conditional_edges(
            "route_input",
            self.decide_input_path,
            {
                "video": "process_video",
                "text": "check_cache" # For text input, skip video processing
            }
        )
        
        # 2. If video, process it, then check cache
        workflow.add_edge("process_video", "check_cache")

        # 3. After checking cache, either exit (hit) or continue (miss)
        workflow.add_conditional_edges(
            "check_cache",
            self.decide_after_cache,
            {
                "continue": "search_vectors",
                "exit": END,
            },
        )

        # 4. After searching vectors, decide if we need to generate new knowledge
        workflow.add_conditional_edges(
            "search_vectors",
            self.decide_to_generate_knowledge,
            {
                "generate": "generate_knowledge",
                "augment": "perform_final_analysis",
            },
        )
        
        # 5. If we generate knowledge, we must ingest it
        workflow.add_edge("generate_knowledge", "ingest_knowledge")
        
        # 6. After ingesting, perform the final analysis
        workflow.add_edge("ingest_knowledge", "perform_final_analysis")
        
        # 7. The final analysis is the last step before the end
        workflow.add_edge("perform_final_analysis", END)

        return workflow.compile()

    # --- Node Implementations ---

    def route_input(self, state: AgentState):
        """ The entry point to the graph, does nothing, just for routing. """
        logger.info("Agent: Routing input.")
        pass

    def decide_input_path(self, state: AgentState):
        """ Determines the workflow path based on input type. """
        if state.get("video_file_path"):
            logger.info("Agent: Video input detected.")
            return "video"
        logger.info("Agent: Text input detected.")
        return "text"

    async def process_video(self, state: AgentState):
        logger.info("Agent: Processing video to extract text.")
        extracted_text = await extract_text_from_video(self.gemini_client, state["video_file_path"])
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
        if cached_result:
            logger.info("Agent: Cache hit.")
            return {"final_result": json.loads(cached_result)}
        logger.info("Agent: Cache miss.")
        return {"analysis_cache_key": key}

    def decide_after_cache(self, state: AgentState):
        """ Determines the next step after checking the cache. """
        if state.get("final_result"):
            return "exit" # Exit the graph if a cached result was found
        return "continue"

    async def search_vectors(self, state: AgentState):
        logger.info("Agent: Searching MongoDB for vector context.")
        query_embedding = await embed(self.gemini_client, state["jd_text"])
        results = search(query_embedding, top_k=3)
        return {"vector_search_results": results}

    def decide_to_generate_knowledge(self, state: AgentState):
        logger.info("Agent: Deciding whether to generate new knowledge.")
        if not state["vector_search_results"]:
            logger.info("Agent: Vector store is empty. Proceeding to generate knowledge.")
            return "generate"
        logger.info("Agent: Found context in vector store. Proceeding to final analysis.")
        return "augment"

    async def generate_knowledge(self, state: AgentState):
        logger.info("Agent: Generating foundational knowledge from JD.")
        prompt = await self.gemini_client.prompts.get("generate_knowledge")
        formatted_prompt = prompt.format(jd_text=state["jd_text"])
        
        response = await self.gemini_client.call(
            "generate_knowledge",
            self.gemini_client.client.models.generate_content,
            model=self.gemini_client.chat_model,
            contents=formatted_prompt,
        )
        return {"generated_knowledge": response.text}

    async def ingest_knowledge(self, state: AgentState):
        logger.info("Agent: Ingesting newly generated knowledge into vector store.")
        embedding = await embed(self.gemini_client, state["generated_knowledge"])
        document = {
            "text": state["generated_knowledge"],
            "embedding": embedding,
            "source": "generated_from_jd"
        }
        await upsert(document)
        # Add generated knowledge to search results for the current run
        current_results = state.get("vector_search_results", [])
        current_results.append({"text": state["generated_knowledge"]})
        return {"vector_search_results": current_results}

    async def perform_final_analysis(self, state: AgentState):
        """
        Performs the final analysis by synthesizing the resume, JD,
        and retrieved knowledge from the vector store.
        """
        logger.info("Agent: Performing final analysis with retrieved knowledge.")
        
        context = "\n".join([res["text"] for res in state["vector_search_results"]])

        prompt = await self.gemini_client.prompts.get("final_analysis")
        formatted_prompt = prompt.format(
            context=context,
            resume_text=state["resume_text"],
            jd_text=state["jd_text"],
        )

        response = await self.gemini_client.call(
            "final_analysis",
            self.gemini_client.client.models.generate_content,
            model=self.gemini_client.chat_model,
            contents=formatted_prompt,
        )
        
        final_result = self.gemini_client.json_utils.safe_json_parse(response.text)
        await self.redis_client.set(state["analysis_cache_key"], json.dumps(final_result), ex=3600)
        return {"final_result": final_result}
