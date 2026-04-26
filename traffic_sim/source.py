import numpy as np

class TrafficSource:
    """Generates vehicles at a junction at constant or Poisson rate."""
    def __init__(self, source_id, junction_id, destinations, rate=0.3, mode='poisson'):
        self.source_id = source_id
        self.junction_id = junction_id
        self.destinations = destinations  # list of dest junction IDs
        self.rate = rate                  # λ vehicles/step (Poisson) or exact (constant)
        self.mode = mode                  # 'poisson' or 'constant'

    def generate(self, current_time):
        """Returns list of destination IDs for new vehicles."""
        if self.mode == 'poisson':
            n = np.random.poisson(self.rate)
        else:
            n = max(0, int(self.rate))
        return [np.random.choice(self.destinations) for _ in range(n)]
