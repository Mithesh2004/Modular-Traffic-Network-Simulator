import heapq

class Network:
    def __init__(self):
        self.junctions = {}
        self.roads     = {}
        self.sources   = {}
        self.sinks     = {}

    def add_junction(self, junction):
        self.junctions[junction.junction_id] = junction

    def add_road(self, road):
        self.roads[road.road_id] = road
        self.junctions[road.from_junction].add_outgoing(road)
        self.junctions[road.to_junction].add_incoming(road)

    def add_source(self, source):
        self.sources[source.junction_id] = source

    def add_sink(self, sink):
        self.sinks[sink.junction_id] = sink

    def shortest_path(self, from_id, to_id):
        """Static Dijkstra — used only at spawn time for free-flow reference."""
        return self._dijkstra(from_id, to_id, congestion_factor=0.0)

    def congestion_aware_path(self, from_id, to_id, congestion_factor=3.0):
        """
        Dynamic Dijkstra — effective cost = length * (1 + factor * occupancy).
        Called at every junction so vehicles reroute around congestion.
          occupancy=0%  → normal cost  (free road)
          occupancy=50% → 1 + 3*0.5 = 2.5x cost
          occupancy=100%→ 1 + 3*1.0 = 4x cost  (nearly blocked)
        """
        return self._dijkstra(from_id, to_id, congestion_factor=congestion_factor)

    def _dijkstra(self, from_id, to_id, congestion_factor=0.0):
        dist = {jid: float('inf') for jid in self.junctions}
        prev = {jid: None for jid in self.junctions}
        dist[from_id] = 0
        pq = [(0, from_id)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for road in self.junctions[u].outgoing_roads:
                v = road.to_junction
                effective_cost = road.length * (1.0 + congestion_factor * road.occupancy)
                nd = d + effective_cost
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        if dist[to_id] == float('inf'):
            return []
        path, cur = [], to_id
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        return list(reversed(path))
