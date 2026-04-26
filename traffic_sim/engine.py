import numpy as np
from .vehicle import Vehicle

DEST_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22']

class SimulationEngine:
    def __init__(self, network, total_steps=150, dt=1.0,
                 vehicle_speed=0.3, congestion_factor=3.0):
        self.network           = network
        self.total_steps       = total_steps
        self.dt                = dt
        self.vehicle_speed     = vehicle_speed
        self.congestion_factor = congestion_factor   # ← passed from main.py
        self.vehicles          = []
        self.current_time      = 0.0
        self._vid              = 0

        dest_ids = sorted(network.sinks.keys())
        self.dest_colors = {d: DEST_COLORS[i % len(DEST_COLORS)] for i, d in enumerate(dest_ids)}

        self.snapshots = []
        self.stats = {
            'total_spawned': 0,
            'total_arrived': 0,
            'travel_times':       [],
            'wait_times':         [],
            'free_flow_times':    [],
            'stop_counts':        [],
            'road_occupancy':     {rid: [] for rid in network.roads},
            'road_queue_lengths': {rid: [] for rid in network.roads},
            'junction_total_delay':   {jid: 0.0 for jid in network.junctions},
            'junction_service_count': {jid: 0   for jid in network.junctions},
            'junction_max_queue':     {jid: 0   for jid in network.junctions},
            'active_counts': [],
        }

    # ------------------------------------------------------------------ helpers
    def _free_flow_time(self, route):
        """Minimum travel time on empty roads (used for delay metric)."""
        t = 0.0
        for i in range(len(route) - 1):
            road = self.network.junctions[route[i]].get_outgoing_to(route[i + 1])
            if road:
                t += road.length / self.vehicle_speed
        return t

    # ------------------------------------------------------------------ steps
    def _spawn_vehicles(self):
        for junc_id, source in self.network.sources.items():
            for dest_id in source.generate(self.current_time):
                if dest_id == junc_id:
                    continue
                # Initial route via static shortest path (no congestion yet at spawn)
                path = self.network.shortest_path(junc_id, dest_id)
                if len(path) < 2:
                    continue
                v = Vehicle(self._vid, junc_id, dest_id,
                            self.dest_colors.get(dest_id, 'gray'))
                v.route          = path
                v.spawn_time     = self.current_time
                v.free_flow_time = self._free_flow_time(path)
                v.stop_count     = 0
                self._vid += 1
                self.stats['total_spawned'] += 1
                first_road = self.network.junctions[path[0]].get_outgoing_to(path[1])
                if first_road and not first_road.is_full:
                    first_road.vehicles.append(v)
                    v.current_road = first_road.road_id
                    v.progress     = 0.0
                    self.vehicles.append(v)

    def _move_vehicles(self):
        for v in self.vehicles:
            if v.arrived:
                continue
            road = self.network.roads[v.current_road]
            v.progress = min(1.0, v.progress + self.vehicle_speed / road.length)
            if v.progress >= 1.0 and v not in road.queue:
                road.queue.append(v)
                v.stop_count += 1

    def _process_junctions(self):
        for junc_id, junc in self.network.junctions.items():
            # Track max queue
            total_q = sum(len(r.queue) for r in junc.incoming_roads)
            if total_q > self.stats['junction_max_queue'][junc_id]:
                self.stats['junction_max_queue'][junc_id] = total_q

            # Sink: absorb all arrived vehicles
            if junc_id in self.network.sinks:
                for road in junc.incoming_roads:
                    for v in list(road.queue):
                        road.queue.remove(v)
                        road.vehicles.remove(v)
                        self.network.sinks[junc_id].absorb(v, self.current_time)
                        tt = self.current_time - v.spawn_time
                        self.stats['travel_times'].append(tt)
                        self.stats['wait_times'].append(v.wait_time)
                        self.stats['free_flow_times'].append(v.free_flow_time)
                        self.stats['stop_counts'].append(v.stop_count)
                        self.stats['total_arrived'] += 1
                continue

            road = junc.schedule_next_incoming()
            if road is None or not road.queue:
                # Accumulate delay for all blocked vehicles
                for r in junc.incoming_roads:
                    for v in r.queue:
                        v.wait_time += self.dt
                        self.stats['junction_total_delay'][junc_id] += self.dt
                continue

            v = road.queue[0]

            # ── DYNAMIC REROUTING ──────────────────────────────────────────
            # Recompute best route from this junction using current congestion
            new_route = self.network.congestion_aware_path(
                junc_id, v.dest_id, self.congestion_factor
            )
            if new_route and len(new_route) >= 2:
                v.route = new_route   # update vehicle's plan
            # ──────────────────────────────────────────────────────────────

            try:
                idx = v.route.index(junc_id)
            except ValueError:
                road.queue.pop(0)
                continue

            if idx + 1 >= len(v.route):
                road.queue.pop(0)
                road.vehicles.remove(v)
                v.arrived = True
                continue

            next_road = junc.get_outgoing_to(v.route[idx + 1])
            if next_road and not next_road.is_full:
                road.queue.remove(v)
                road.vehicles.remove(v)
                next_road.vehicles.append(v)
                v.current_road = next_road.road_id
                v.progress     = 0.0
                self.stats['junction_service_count'][junc_id] += 1
            else:
                # Blocked — wait and accumulate delay
                for r in junc.incoming_roads:
                    for qv in r.queue:
                        qv.wait_time += self.dt
                        self.stats['junction_total_delay'][junc_id] += self.dt

    def _snapshot(self):
        road_states = {}
        for rid, road in self.network.roads.items():
            qlen = len(road.queue)
            road_states[rid] = {
                'occupancy':     road.occupancy,
                'queue_len':     qlen,
                'vehicle_count': len(road.vehicles),
                'capacity':      road.capacity,
            }
            self.stats['road_occupancy'][rid].append(road.occupancy)
            self.stats['road_queue_lengths'][rid].append(qlen)

        frame = {'time': self.current_time, 'vehicles': [], 'road_states': road_states}
        queue_offsets = {}

        for v in self.vehicles:
            if v.arrived:
                continue
            road = self.network.roads[v.current_road]
            fj   = self.network.junctions[road.from_junction]
            tj   = self.network.junctions[road.to_junction]
            is_queued = v in road.queue

            if is_queued:
                rid = road.road_id
                if rid not in queue_offsets:
                    queue_offsets[rid] = 0
                offset_idx = queue_offsets[rid]
                queue_offsets[rid] += 1
                dx, dy = tj.x - fj.x, tj.y - fj.y
                length = max((dx**2 + dy**2)**0.5, 0.001)
                px, py = -dy / length, dx / length
                lateral = (offset_idx - road.capacity / 2) * 0.18
                x = fj.x + 0.90 * dx + lateral * px
                y = fj.y + 0.90 * dy + lateral * py
            else:
                x = fj.x + v.progress * (tj.x - fj.x)
                y = fj.y + v.progress * (tj.y - fj.y)

            frame['vehicles'].append({
                'x': x, 'y': y, 'color': v.color,
                'dest': v.dest_id, 'queued': is_queued,
            })

        self.snapshots.append(frame)
        self.stats['active_counts'].append(len(frame['vehicles']))

    def run(self):
        print(f"Simulation started: {self.total_steps} steps  "
              f"[speed={self.vehicle_speed}, congestion_factor={self.congestion_factor}]")
        for step in range(self.total_steps):
            self.current_time = step * self.dt
            self._spawn_vehicles()
            self._move_vehicles()
            self._process_junctions()
            self._snapshot()
            if step % 20 == 0:
                print(f"  Step {step:4d} | Active: {self.stats['active_counts'][-1]:3d} "
                      f"| Arrived: {self.stats['total_arrived']:4d}")
        print(f"Done. Spawned={self.stats['total_spawned']}  Arrived={self.stats['total_arrived']}")
        return self.stats
