class Sink:
    """Absorbs vehicles that reach their destination."""
    def __init__(self, sink_id, junction_id):
        self.sink_id = sink_id
        self.junction_id = junction_id
        self.arrived_vehicles = []

    def absorb(self, vehicle, current_time):
        vehicle.arrived = True
        vehicle.arrive_time = current_time
        self.arrived_vehicles.append(vehicle)
