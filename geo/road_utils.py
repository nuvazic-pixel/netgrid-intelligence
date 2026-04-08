import osmnx as ox
import networkx as nx


def get_road_graph(address):
    try:
        return ox.graph_from_place(address, network_type='drive')
    except Exception as e:
        print('Graph error:', e)
        return None


def nearest_node(G, lat, lon):
    return ox.distance.nearest_nodes(G, lon, lat)


def road_distance(G, lat1, lon1, lat2, lon2):
    try:
        n1 = nearest_node(G, lat1, lon1)
        n2 = nearest_node(G, lat2, lon2)
        return nx.shortest_path_length(G, n1, n2, weight='length')
    except Exception:
        return None