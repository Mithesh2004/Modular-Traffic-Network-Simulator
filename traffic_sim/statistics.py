import numpy as np

class Statistics:
    """
    Computes and stores all performance metrics after simulation ends.

    Categories:
        1. Vehicle-Level      — individual journey quality
        2. Network-Level      — system-wide efficiency
        3. Road/Segment-Level — per-road bottleneck analysis
        4. Junction-Level     — per-junction delay and utilisation
    """

    def __init__(self, stats: dict, network, total_steps: int, dt: float):
        self.raw   = stats
        self.net   = network
        self.steps = total_steps
        self.dt    = dt
        self.results = {}
        self._compute()

    # ------------------------------------------------------------------ compute
    def _compute(self):
        r = self.results
        s = self.raw
        n = self.steps

        tt  = np.array(s['travel_times'])    if s['travel_times']    else np.array([0])
        wt  = np.array(s['wait_times'])      if s['wait_times']      else np.array([0])
        fft = np.array(s['free_flow_times']) if s['free_flow_times'] else np.array([0])
        sc  = np.array(s['stop_counts'])     if s['stop_counts']     else np.array([0])

        # ── 1. Vehicle-Level ───────────────────────────────────────────────────
        delay = tt - fft   # extra time caused by congestion
        r['vehicle'] = {
            'avg_travel_time_delay':
                (np.mean(delay), 'steps',
                 'Mean extra time per vehicle due to congestion (actual − free-flow)'),
            'avg_wait_time':
                (np.mean(wt), 'steps',
                 'Mean time each vehicle spent queued at junctions'),
            'avg_stops_per_vehicle':
                (np.mean(sc), 'stops',
                 'Mean number of times a vehicle entered a queue during its trip'),
        }

        # ── 2. Network-Level ──────────────────────────────────────────────────
        spawned  = max(s['total_spawned'], 1)
        arrived  = s['total_arrived']
        throughput = arrived / (n * self.dt)   # vehicles per time unit

        # Network efficiency: free-flow time / actual time (1.0 = perfect)
        efficiency = float(np.mean(fft) / np.mean(tt)) if np.mean(tt) > 0 else 1.0

        r['network'] = {
            'throughput':
                (round(throughput, 4), 'vehicles/step',
                 'Vehicles successfully arriving at sinks per simulation step'),
            'arrival_rate':
                (round(100 * arrived / spawned, 1), '%',
                 'Percentage of spawned vehicles that completed their journey'),
            'network_efficiency':
                (round(efficiency, 3), 'ratio (0–1)',
                 'Free-flow travel time / actual travel time; 1.0 = no congestion'),
        }

        # ── 3. Road/Segment-Level ─────────────────────────────────────────────
        road_metrics = {}
        for rid in self.net.roads:
            occ = np.array(s['road_occupancy'][rid])
            ql  = np.array(s['road_queue_lengths'][rid])
            road_metrics[rid] = {
                'mean_occupancy':   round(float(np.mean(occ)), 3),
                'mean_queue_len':   round(float(np.mean(ql)),  3),
                'time_in_congestion': int(np.sum(occ > 0.66)),  # steps above 66%
            }
        r['road'] = road_metrics

        # ── 4. Junction-Level ─────────────────────────────────────────────────
        junc_metrics = {}
        for jid in self.net.junctions:
            if jid in self.net.sinks or jid in self.net.sources:
                continue
            served  = max(s['junction_service_count'][jid], 1)
            total_d = s['junction_total_delay'][jid]
            max_q   = s['junction_max_queue'][jid]

            # Busy fraction: steps where any incoming road had a queue
            busy_steps = sum(
                1 for step_idx in range(n)
                if any(
                    s['road_queue_lengths'][r.road_id][step_idx] > 0
                    for r in self.net.junctions[jid].incoming_roads
                    if r.road_id in s['road_queue_lengths']
                    and step_idx < len(s['road_queue_lengths'][r.road_id])
                )
            )
            junc_metrics[jid] = {
                'avg_delay_per_vehicle': round(total_d / served, 3),
                'max_queue_length':      max_q,
                'utilisation_pct':       round(100 * busy_steps / n, 1),
            }
        r['junction'] = junc_metrics

    # ------------------------------------------------------------------ display
    def summary(self):
        r = self.results
        lines = []

        lines.append("=" * 62)
        lines.append(" TRAFFIC SIMULATION METRICS REPORT")
        lines.append("=" * 62)

        lines.append("\n── 1. Vehicle-Level Metrics ─────────────────────────────────")
        for key, (val, unit, desc) in r['vehicle'].items():
            lines.append(f"  {key:<30} {val:>8.3f}  {unit}")
            lines.append(f"  {'':>30}   ↳ {desc}")

        lines.append("\n── 2. Network-Level Metrics ─────────────────────────────────")
        for key, (val, unit, desc) in r['network'].items():
            lines.append(f"  {key:<30} {val:>8}  {unit}")
            lines.append(f"  {'':>30}   ↳ {desc}")

        lines.append("\n── 3. Road/Segment-Level Metrics ────────────────────────────")
        lines.append(f"  {'Road':<6} {'Occ':>7} {'AvgQ':>7} {'CongSteps':>10}")
        lines.append(f"  {'-'*6} {'-'*7} {'-'*7} {'-'*10}")
        for rid, m in sorted(r['road'].items()):
            lines.append(
                f"  {str(rid):<6} {m['mean_occupancy']:>7.3f} "
                f"{m['mean_queue_len']:>7.3f} {m['time_in_congestion']:>10}"
            )

        lines.append("\n── 4. Junction-Level Metrics ────────────────────────────────")
        lines.append(f"  {'Junc':<6} {'AvgDelay':>9} {'MaxQ':>6} {'Util%':>7}")
        lines.append(f"  {'-'*6} {'-'*9} {'-'*6} {'-'*7}")
        for jid, m in sorted(r['junction'].items(), key=lambda x: str(x[0])):
            lines.append(
                f"  J{str(jid):<5} {m['avg_delay_per_vehicle']:>9.3f} "
                f"{m['max_queue_length']:>6} {m['utilisation_pct']:>6.1f}%"
            )

        lines.append("\n" + "=" * 62)
        report = "\n".join(lines)
        print(report)
        return report
