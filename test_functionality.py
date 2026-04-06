#!/usr/bin/env python3
"""Comprehensive functionality test for Purple Team GPT."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def test_imports():
    """Test all critical imports work."""
    print("\n" + "="*60)
    print("TEST 1: Import Checks")
    print("="*60)
    
    errors = []
    
    try:
        from purple_team_gpt import __version__, __app_name__
        print(f"[PASS] Package import - {__app_name__} v{__version__}")
    except Exception as e:
        errors.append(f"[FAIL] Package import: {e}")
    
    try:
        from purple_team_gpt.config import get_settings, Settings, LLMSettings
        print("[PASS] Config module import")
    except Exception as e:
        errors.append(f"[FAIL] Config import: {e}")
    
    try:
        from purple_team_gpt.core.llm.engine import LLMEngine, Conversation, Message
        print("[PASS] LLM Engine import")
    except Exception as e:
        errors.append(f"[FAIL] LLM Engine import: {e}")
    
    try:
        from purple_team_gpt.core.rag.vector_store import VectorStore
        print("[PASS] Vector Store import")
    except Exception as e:
        errors.append(f"[FAIL] Vector Store import: {e}")
    
    try:
        from purple_team_gpt.core.orchestrator import PurpleOrchestrator, Session, SessionStatus
        print("[PASS] Orchestrator import")
    except Exception as e:
        errors.append(f"[FAIL] Orchestrator import: {e}")
    
    try:
        from purple_team_gpt.agents.base import BaseAgent, AgentRole, AgentState, Finding
        print("[PASS] Base Agent import")
    except Exception as e:
        errors.append(f"[FAIL] Base Agent import: {e}")
    
    try:
        from purple_team_gpt.agents.red_agent import RedAgent, ToolRunner
        print("[PASS] Red Agent import")
    except Exception as e:
        errors.append(f"[FAIL] Red Agent import: {e}")
    
    try:
        from purple_team_gpt.agents.blue_agent import BlueAgent, DefenseToolRunner
        print("[PASS] Blue Agent import")
    except Exception as e:
        errors.append(f"[FAIL] Blue Agent import: {e}")
    
    try:
        from purple_team_gpt.feedback.store import FeedbackStore
        print("[PASS] Feedback Store import")
    except Exception as e:
        errors.append(f"[FAIL] Feedback Store import: {e}")
    
    for err in errors:
        print(err)
    
    return len(errors) == 0


def test_config():
    """Test configuration loading."""
    print("\n" + "="*60)
    print("TEST 2: Configuration")
    print("="*60)
    
    try:
        from purple_team_gpt.config import get_settings
        settings = get_settings()
        
        print(f"[INFO] LLM Provider: {settings.llm.default_provider}")
        print(f"[INFO] Default Model: {settings.llm.default_model}")
        print(f"[INFO] Temperature: {settings.llm.temperature}")
        print(f"[INFO] Max Tokens: {settings.llm.max_tokens}")
        print(f"[INFO] Safe Mode: {settings.agent.safe_mode}")
        print(f"[INFO] Max Steps: {settings.agent.max_steps}")
        print(f"[INFO] Chroma Persist Dir: {settings.chroma.persist_dir}")
        
        # Check for API keys (masked)
        has_openai = bool(settings.llm.openai_api_key)
        has_anthropic = bool(settings.llm.anthropic_api_key)
        has_groq = bool(settings.llm.groq_api_key)
        has_deepseek = bool(settings.llm.deepseek_api_key)
        has_mistral = bool(settings.llm.mistral_api_key)
        
        print(f"[INFO] OpenAI API Key: {'Set' if has_openai else 'Not Set'}")
        print(f"[INFO] Anthropic API Key: {'Set' if has_anthropic else 'Not Set'}")
        print(f"[INFO] Groq API Key: {'Set' if has_groq else 'Not Set'}")
        print(f"[INFO] DeepSeek API Key: {'Set' if has_deepseek else 'Not Set'}")
        print(f"[INFO] Mistral API Key: {'Set' if has_mistral else 'Not Set'}")
        
        print("[PASS] Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Configuration error: {e}")
        return False


def test_llm_engine():
    """Test LLM engine initialization."""
    print("\n" + "="*60)
    print("TEST 3: LLM Engine")
    print("="*60)
    
    try:
        from purple_team_gpt.config import get_settings
        from purple_team_gpt.core.llm.engine import LLMEngine, Conversation
        
        settings = get_settings()
        engine = LLMEngine(settings.llm)
        
        providers = engine.get_available_providers()
        print(f"[INFO] Available Providers: {providers}")
        
        is_configured = engine.is_configured()
        print(f"[INFO] Configured: {is_configured}")
        
        # Test conversation
        conv = Conversation()
        conv.add_user("Test message")
        api_format = conv.to_api_format()
        print(f"[INFO] Conversation format: {len(api_format)} messages")
        
        print("[PASS] LLM Engine initialized successfully")
        return True
    except Exception as e:
        print(f"[FAIL] LLM Engine error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """Test Vector Store initialization."""
    print("\n" + "="*60)
    print("TEST 4: Vector Store")
    print("="*60)
    
    try:
        from purple_team_gpt.config import get_settings, ChromaSettings
        from purple_team_gpt.core.rag.vector_store import VectorStore
        from purple_team_gpt.core.rag.embeddings import EmbeddingEngine, EmbeddingProvider
        
        settings = get_settings()
        
        # Use local embeddings for testing
        embedding_engine = EmbeddingEngine(
            llm_settings=settings.llm,
            provider=EmbeddingProvider.LOCAL,
        )
        
        # Use test directory
        test_settings = ChromaSettings(
            host="localhost",
            port=8001,
            persist_dir="./data/test_chromadb",
        )
        
        store = VectorStore(test_settings, embedding_engine)
        store.initialize_collections()
        
        print(f"[INFO] Collections initialized: {len(store.COLLECTIONS)}")
        
        # Test adding a document
        import asyncio
        async def test_add():
            ids = await store.add(
                "attack_patterns",
                ["Test attack pattern for reconnaissance"],
                metadatas=[{"test": True}],
            )
            return ids
        
        ids = asyncio.run(test_add())
        print(f"[INFO] Added test document: {ids[0] if ids else 'None'}")
        
        print("[PASS] Vector Store initialized successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Vector Store error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_feedback_store():
    """Test Feedback Store."""
    print("\n" + "="*60)
    print("TEST 5: Feedback Store")
    print("="*60)
    
    try:
        from purple_team_gpt.feedback.store import FeedbackStore
        from purple_team_gpt.feedback.models import FeedbackEntry, AgentType
        
        store = FeedbackStore(db_path="./data/test_feedback.db")
        
        # Create a test entry with all required fields
        entry = FeedbackEntry(
            session_id="test-session-123",
            interaction_id="test-interaction-456",
            agent_type=AgentType.RED,
            prompt="What are the vulnerabilities in this network?",
            response="I found 3 open ports and 2 potential vulnerabilities.",
            rating=5,
            comment="Excellent test!",
        )
        
        saved = store.add_feedback(entry)
        print(f"[INFO] Added feedback entry: ID={saved.id}")
        
        # Retrieve it
        retrieved = store.get_feedback(saved.id)
        print(f"[INFO] Retrieved feedback: Rating={retrieved.rating}")
        
        # Get stats
        stats = store.get_stats()
        print(f"[INFO] Stats: Total={stats.total_feedback}, Avg Rating={stats.average_rating:.2f}")
        
        print("[PASS] Feedback Store working correctly")
        return True
    except Exception as e:
        print(f"[FAIL] Feedback Store error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_runners():
    """Test Tool Runner validation."""
    print("\n" + "="*60)
    print("TEST 6: Tool Runners")
    print("="*60)
    
    try:
        from purple_team_gpt.agents.red_agent import ToolRunner
        from purple_team_gpt.agents.blue_agent import DefenseToolRunner
        
        # Test Red Agent Tool Runner
        red_runner = ToolRunner(safe_mode=True)
        
        # Valid command
        valid, error = red_runner._validate_command("nmap -sV target", "nmap")
        print(f"[INFO] Red Tool - Valid nmap: {valid}")
        
        # Invalid tool
        valid, error = red_runner._validate_command("rm -rf /", "rm")
        print(f"[INFO] Red Tool - Invalid rm: {valid} ({error})")
        
        # Destructive pattern in safe mode
        valid, error = red_runner._validate_command("curl http://rm.example.com", "curl")
        print(f"[INFO] Red Tool - Destructive pattern: {valid} ({error})")
        
        # Test Blue Agent Tool Runner
        blue_runner = DefenseToolRunner(safe_mode=True)
        
        # Valid command
        valid, error = blue_runner._validate_command("ps aux", "ps")
        print(f"[INFO] Blue Tool - Valid ps: {valid}")
        
        # Dangerous pattern
        valid, error = blue_runner._validate_command("rm -rf /", "rm")
        print(f"[INFO] Blue Tool - Dangerous rm: {valid} ({error})")
        
        print("[PASS] Tool Runners validation working")
        return True
    except Exception as e:
        print(f"[FAIL] Tool Runners error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_orchestrator():
    """Test Orchestrator initialization."""
    print("\n" + "="*60)
    print("TEST 7: Orchestrator")
    print("="*60)
    
    try:
        from purple_team_gpt.config import get_settings, ChromaSettings
        from purple_team_gpt.core.llm.engine import LLMEngine
        from purple_team_gpt.core.rag.vector_store import VectorStore
        from purple_team_gpt.core.rag.embeddings import EmbeddingEngine, EmbeddingProvider
        from purple_team_gpt.core.orchestrator import PurpleOrchestrator
        
        settings = get_settings()
        
        # Initialize components
        llm_engine = LLMEngine(settings.llm)
        
        embedding_engine = EmbeddingEngine(
            llm_settings=settings.llm,
            provider=EmbeddingProvider.LOCAL,
        )
        
        test_chroma = ChromaSettings(
            host="localhost",
            port=8001,
            persist_dir="./data/test_chromadb",
        )
        
        vector_store = VectorStore(test_chroma, embedding_engine)
        vector_store.initialize_collections()
        
        # Create orchestrator
        orchestrator = PurpleOrchestrator(
            engine=llm_engine,
            vector_store=vector_store,
            max_steps=10,
            safe_mode=True,
        )
        
        print(f"[INFO] Orchestrator initialized")
        
        # Create a session
        session = orchestrator.create_session(
            target="192.168.1.1",
            scope="Test session",
        )
        
        print(f"[INFO] Session created: {session.id}")
        print(f"[INFO] Session status: {session.status}")
        
        # List sessions
        sessions = orchestrator.list_sessions()
        print(f"[INFO] Total sessions: {len(sessions)}")
        
        # Get metrics
        metrics = orchestrator.get_metrics(session.id)
        print(f"[INFO] Metrics: {metrics}")
        
        print("[PASS] Orchestrator working correctly")
        return True
    except Exception as e:
        print(f"[FAIL] Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_app():
    """Test FastAPI app creation."""
    print("\n" + "="*60)
    print("TEST 8: FastAPI Application")
    print("="*60)
    
    try:
        # Set required env var
        os.environ["APP_SECRET_KEY"] = "test-secret-key-for-testing-only"
        
        from purple_team_gpt.backend.main import app
        
        print(f"[INFO] App title: {app.title}")
        print(f"[INFO] App version: {app.version}")
        
        # Check routes
        routes = [route.path for route in app.routes]
        print(f"[INFO] Routes: {len(routes)}")
        
        expected_routes = ["/", "/health", "/status"]
        for route in expected_routes:
            if route in routes:
                print(f"[INFO] Route {route}: Present")
            else:
                print(f"[WARN] Route {route}: Missing")
        
        print("[PASS] FastAPI app created successfully")
        return True
    except Exception as e:
        print(f"[FAIL] FastAPI error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("PURPLE TEAM GPT - FUNCTIONALITY TEST")
    print("="*60)
    
    results = {
        "Imports": test_imports(),
        "Config": test_config(),
        "LLM Engine": test_llm_engine(),
        "Vector Store": test_vector_store(),
        "Feedback Store": test_feedback_store(),
        "Tool Runners": test_tool_runners(),
        "Orchestrator": asyncio.run(test_orchestrator()),
        "FastAPI App": test_fastapi_app(),
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {name}: [{status}]")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)