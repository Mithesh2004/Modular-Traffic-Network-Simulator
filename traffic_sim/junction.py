class Junction:
    """Supports 2-way, 3-way, and 4-way junctions."""
    VALID_TYPES = {'2-way', '3-way', '4-way', 'source', 'sink', 'intersection'}

    def __init__(self, junction_id, junction_type='intersection', x=0.0, y=0.0):
        assert junction_type in self.VALID_TYPES, f"Unknown junction type: {junction_type}"
        self.junction_id = junction_id
        self.junction_type = junction_type
        self.x = x
        self.y = y
        self.incoming_roads = []
        self.outgoing_roads = []
        self._rr_index = 0  # round-robin pointer

    def add_incoming(self, road):
        self.incoming_roads.append(road)

    def add_outgoing(self, road):
        self.outgoing_roads.append(road)

    def get_outgoing_to(self, next_junction_id):
        for road in self.outgoing_roads:
            if road.to_junction == next_junction_id:
                return road
        return None

    def schedule_next_incoming(self):
        """Round-robin: return next incoming road that has vehicles queued."""
        active = [r for r in self.incoming_roads if r.queue]
        if not active:
            return None
        self._rr_index = self._rr_index % len(active)
        chosen = active[self._rr_index]
        self._rr_index = (self._rr_index + 1) % len(active)
        return chosen
