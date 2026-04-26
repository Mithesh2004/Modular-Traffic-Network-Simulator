class Road:
    def __init__(self, road_id, from_junction, to_junction, capacity=5, length=1.0):
        self.road_id = road_id
        self.from_junction = from_junction
        self.to_junction = to_junction
        self.capacity = capacity
        self.length = length
        self.vehicles = []   # all vehicles on road
        self.queue = []      # vehicles at end, waiting to enter next junction

    @property
    def is_full(self):
        return len(self.vehicles) >= self.capacity

    @property
    def occupancy(self):
        return len(self.vehicles) / self.capacity if self.capacity > 0 else 0
