
import pytest
from cortex.engine import CortexEngine
from cortex.graph.types import Entity

@pytest.fixture
def engine_with_graph(tmp_path):
    """Create a test engine with graph tables."""
    db_path = tmp_path / "test_graph_rag.db"
    eng = CortexEngine(db_path=str(db_path), auto_embed=False)
    eng.init_db_sync()
    return eng

@pytest.mark.asyncio
async def test_engine_graph_rag_methods(engine_with_graph):
    engine = engine_with_graph
    project = "rag-test"
    
    # Store some facts with connections
    # Use keyword args to avoid ambiguity
    await engine.store(project=project, content="Angular is a frontend framework.") 
    await engine.store(project=project, content="TypeScript is a superset of JavaScript.")
    await engine.store(project=project, content="Angular uses TypeScript for development.")

    # Test get_context_subgraph
    subgraph = await engine.get_context_subgraph(["Angular"], depth=2)
    
    assert subgraph["nodes"]
    assert subgraph["edges"]
    
    node_names = [n["name"] for n in subgraph["nodes"]]
    assert "Angular" in node_names
    assert "TypeScript" in node_names
    
    # Test find_path
    paths = await engine.find_path("Angular", "JavaScript", max_depth=3)
    assert len(paths) > 0
    path = paths[0]
    assert path[0]["source"] == "Angular"
    assert path[0]["target"] == "TypeScript"
    assert path[1]["target"] == "JavaScript"

@pytest.mark.asyncio
async def test_search_with_graph_context(engine_with_graph):
    engine = engine_with_graph
    project = "rag-search-test"
    
    # Populate data
    await engine.store(content="React is a UI library.", project=project)
    await engine.store(content="React uses JSX.", project=project)
    
    # Search with graph_depth=0 (default)
    results = await engine.search("React", project=project)
    assert len(results) > 0
    assert results[0].graph_context is None
    
    # Search with graph_depth=1
    results_graph = await engine.search("React", project=project, graph_depth=1)
    assert len(results_graph) > 0
    # First result should have graph context if it mentions React
    assert results_graph[0].graph_context is not None
    ctx = results_graph[0].graph_context
    nodes = [n["name"] for n in ctx["nodes"]]
    assert "React" in nodes
    # Check that JSX is also there (since React -> JSX relation exists)
    assert "JSX" in nodes
