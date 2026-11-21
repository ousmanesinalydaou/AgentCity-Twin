from .simulation.engine import shortest


def supports_network(edges, demand):
    if not edges or not demand:
        return not edges and not demand
    graph = {}
    for index, (a, b, _, _, _) in enumerate(edges):
        graph.setdefault(a, []).append((b, index))
        graph.setdefault(b, []).append((a, index))
    costs = [edge[2] for edge in edges]
    return all(a != b and shortest(graph, a, b, costs) for a, b, _ in demand)
