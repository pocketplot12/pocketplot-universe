"""
PocketPlot Universe - scene graph editor (v24).

Each world has a graph of scenes:
  - nodes = scenes (episodes)
  - edges = choices between scenes

Stored in:
  - worlds.scene_nodes_json : [{id, episode_id, x, y, label, color}, ...]
  - worlds.scene_edges_json : [{from_id, to_id, choice_label, choice_index}, ...]

If scene_nodes_json / scene_edges_json are NULL, we synthesize a linear graph
from the episode list (the v23 fallback behavior).

API:
  - load_graph(db, world_id) -> {nodes, edges}
  - save_graph(db, world_id, nodes, edges)
  - synthesize_linear_graph(db, world_id)  # fallback
  - add_node, update_node, delete_node
  - add_edge, delete_edge
"""
import json
import random


def _conn(db):
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


def load_graph(db, world_id):
    """Load the scene graph for a world. Returns {nodes: [...], edges: [...]}."""
    c = _conn(db)
    row = c.execute("SELECT scene_nodes_json, scene_edges_json FROM worlds WHERE id=?",
                    (world_id,)).fetchone()
    nodes_json = row['scene_nodes_json']
    edges_json = row['scene_edges_json']
    if nodes_json and edges_json:
        try:
            nodes = json.loads(nodes_json)
            edges = json.loads(edges_json)
            return {'nodes': nodes, 'edges': edges}
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: synthesize linear graph
    return synthesize_linear_graph(db, world_id)


def synthesize_linear_graph(db, world_id):
    """Build a linear scene graph from the world's episodes."""
    c = _conn(db)
    episodes = c.execute(
        "SELECT id, episode_number, title FROM world_episodes WHERE world_id=? ORDER BY episode_number",
        (world_id,),
    ).fetchall()
    nodes = []
    edges = []
    for i, ep in enumerate(episodes):
        nodes.append({
            'id': f'n{i+1}',
            'episode_id': ep['id'],
            'episode_number': ep['episode_number'],
            'label': ep['title'] or f'Episode {ep["episode_number"]}',
            'x': 100 + (i % 5) * 160,
            'y': 100 + (i // 5) * 140,
            'color': '#c9a04e' if i == 0 else '#5ddef0' if i % 3 == 0 else '#243860',
        })
        if i > 0:
            edges.append({
                'from_id': f'n{i}',
                'to_id': f'n{i+1}',
                'choice_label': 'Continue',
                'choice_index': 0,
            })
    return {'nodes': nodes, 'edges': edges}


def save_graph(db, world_id, nodes, edges):
    """Persist the scene graph."""
    c = _conn(db)
    c.execute(
        "UPDATE worlds SET scene_nodes_json=?, scene_edges_json=? WHERE id=?",
        (json.dumps(nodes), json.dumps(edges), world_id),
    )
    c.commit()


def add_node(db, world_id, label, x=None, y=None, episode_id=None):
    """Add a new scene node. Returns the node dict (with generated id)."""
    graph = load_graph(db, world_id)
    # Generate unique id
    existing = {n['id'] for n in graph['nodes']}
    i = len(graph['nodes']) + 1
    while f'n{i}' in existing:
        i += 1
    new_node = {
        'id': f'n{i}',
        'episode_id': episode_id,
        'label': label or f'Scene {i}',
        'x': x if x is not None else 200 + (i % 5) * 160,
        'y': y if y is not None else 200 + (i // 5) * 140,
        'color': '#c9a04e',
    }
    graph['nodes'].append(new_node)
    save_graph(db, world_id, graph['nodes'], graph['edges'])
    return new_node


def update_node(db, world_id, node_id, **updates):
    """Update a node's properties."""
    graph = load_graph(db, world_id)
    for n in graph['nodes']:
        if n['id'] == node_id:
            n.update(updates)
            break
    save_graph(db, world_id, graph['nodes'], graph['edges'])


def delete_node(db, world_id, node_id):
    """Delete a node + any edges connected to it."""
    graph = load_graph(db, world_id)
    graph['nodes'] = [n for n in graph['nodes'] if n['id'] != node_id]
    graph['edges'] = [e for e in graph['edges']
                      if e['from_id'] != node_id and e['to_id'] != node_id]
    save_graph(db, world_id, graph['nodes'], graph['edges'])


def add_edge(db, world_id, from_id, to_id, choice_label='', choice_index=0):
    """Add a directed edge between two nodes."""
    graph = load_graph(db, world_id)
    # Prevent duplicate
    for e in graph['edges']:
        if e['from_id'] == from_id and e['to_id'] == to_id:
            return e
    edge = {
        'from_id': from_id,
        'to_id': to_id,
        'choice_label': choice_label or 'Continue',
        'choice_index': choice_index,
    }
    graph['edges'].append(edge)
    save_graph(db, world_id, graph['nodes'], graph['edges'])
    return edge


def delete_edge(db, world_id, from_id, to_id):
    """Delete an edge."""
    graph = load_graph(db, world_id)
    graph['edges'] = [e for e in graph['edges']
                      if not (e['from_id'] == from_id and e['to_id'] == to_id)]
    save_graph(db, world_id, graph['nodes'], graph['edges'])


def auto_layout(db, world_id):
    """Auto-arrange nodes in a flowing layout."""
    graph = load_graph(db, world_id)
    if not graph['nodes']:
        return graph
    # BFS from the first node (assumed to be the start)
    start = graph['nodes'][0]
    visited = {start['id']}
    queue = [(start, 0, 0)]  # (node, depth, x_slot)
    layout = {}
    while queue:
        node, depth, slot = queue.pop(0)
        layout[node['id']] = (depth, slot)
        # Find children
        children = [e['to_id'] for e in graph['edges'] if e['from_id'] == node['id']]
        for i, child_id in enumerate(children):
            if child_id not in visited:
                visited.add(child_id)
                queue.append((next(n for n in graph['nodes'] if n['id'] == child_id), depth + 1, slot + i))
    # Apply layout
    for n in graph['nodes']:
        if n['id'] in layout:
            depth, slot = layout[n['id']]
            n['x'] = 100 + slot * 180
            n['y'] = 80 + depth * 140
    save_graph(db, world_id, graph['nodes'], graph['edges'])
    return graph
