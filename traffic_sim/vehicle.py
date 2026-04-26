class Vehicle:
    def __init__(self, vid, source_id, dest_id, color='gray'):
        self.vid = vid
        self.source_id = source_id
        self.dest_id = dest_id
        self.color = color
        self.route = []           # ordered list of junction IDs
        self.current_road = None  # road_id
        self.progress = 0.0       # 0.0 → 1.0 along current road
        self.arrived = False
        self.spawn_time = None
        self.arrive_time = None
        self.wait_time = 0.0
