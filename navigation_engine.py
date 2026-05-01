"""
Navigation Engine — Graph-based indoor navigation for 4th floor R&D building.
Uses Dijkstra's shortest path with turn-by-turn directions.
"""

import heapq


class NavigationGraph:
    """Graph-based indoor navigation with shortest path and directions."""

    def __init__(self):
        self.graph = {}          # {node: [(neighbor, weight), ...]}
        self.node_positions = {} # {node: (x, y)} for floor plan
        self.node_info = {}      # {node: {type, wing, side, description}}
        self._build_graph()

    def _build_graph(self):
        """Build the floor plan graph. Elevator at center, A-wing left, B-wing right."""

        # --- central landmarks ---
        self._add_node('elevator', 800, 620, 'landmark', None, None, 'Elevator (4th Floor)')
        self._add_node('door_elevator', 800, 510, 'landmark', None, None, 'Door near Elevator')
        self._add_node('corridor_mid', 800, 380, 'corridor', None, None, 'Main Corridor Junction')

        # --- corridor waypoints (A-wing, going left) ---
        self._add_node('corridor_a1', 700, 380, 'corridor', 'A', None, 'A-Wing Corridor 1')
        self._add_node('corridor_a2', 580, 380, 'corridor', 'A', None, 'A-Wing Corridor 2')
        self._add_node('corridor_a3', 460, 380, 'corridor', 'A', None, 'A-Wing Corridor 3')
        self._add_node('corridor_a4', 340, 380, 'corridor', 'A', None, 'A-Wing Corridor 4')
        self._add_node('corridor_a5', 230, 380, 'corridor', 'A', None, 'A-Wing Corridor 5')
        self._add_node('corridor_a6', 140, 380, 'corridor', 'A', None, 'A-Wing Corridor 6')
        self._add_node('corridor_a7', 60, 380, 'corridor', 'A', None, 'A-Wing Corridor 7')

        # --- corridor waypoints (B-wing, going right) ---
        self._add_node('corridor_b1', 910, 380, 'corridor', 'B', None, 'B-Wing Corridor 1')
        self._add_node('corridor_b2', 1030, 380, 'corridor', 'B', None, 'B-Wing Corridor 2')
        self._add_node('corridor_b3', 1140, 380, 'corridor', 'B', None, 'B-Wing Corridor 3')
        self._add_node('corridor_b4', 1260, 380, 'corridor', 'B', None, 'B-Wing Corridor 4')
        self._add_node('corridor_b5', 1370, 380, 'corridor', 'B', None, 'B-Wing Corridor 5')
        self._add_node('corridor_b6', 1470, 380, 'corridor', 'B', None, 'B-Wing Corridor 6')
        self._add_node('corridor_b7', 1550, 380, 'corridor', 'B', None, 'B-Wing Corridor 7')

        # G landmark
        self._add_node('G', 855, 380, 'landmark', None, None, 'G')

        # --- A-wing rooms (left/south side) ---
        self._add_node('A-412_left',  110, 440, 'room', 'A', 'left', 'Room A-412')
        self._add_node('A-411_left',  155, 500, 'room', 'A', 'left', 'Room A-411')
        self._add_node('A-410_left',  210, 440, 'room', 'A', 'left', 'Room A-410')
        self._add_node('A-409_left',  260, 500, 'room', 'A', 'left', 'Room A-409')
        self._add_node('A-408_left',  320, 440, 'room', 'A', 'left', 'Room A-408')
        self._add_node('A-407_left',  370, 500, 'room', 'A', 'left', 'Room A-407')
        self._add_node('A-406_left',  460, 440, 'room', 'A', 'left', 'Room A-406')
        self._add_node('A-405_left',  520, 500, 'room', 'A', 'left', 'Room A-405')
        self._add_node('A-404_left',  570, 440, 'room', 'A', 'left', 'Room A-404')
        self._add_node('A-403_left',  620, 500, 'room', 'A', 'left', 'Room A-403')
        self._add_node('A-402_left',  680, 440, 'room', 'A', 'left', 'Room A-402')
        self._add_node('A-401_left',  720, 500, 'room', 'A', 'left', 'Room A-401')

        # --- A-wing rooms (right/north side) ---
        self._add_node('A-413_Right', 60,  280, 'room', 'A', 'right', 'Room A-413')
        self._add_node('A-415_Right', 300, 250, 'room', 'A', 'right', 'Room A-415')
        self._add_node('A-416_Right', 380, 300, 'room', 'A', 'right', 'Room A-416')
        self._add_node('A-418_Right', 680, 250, 'room', 'A', 'right', 'Room A-418')
        self._add_node('A-419_Right', 730, 300, 'room', 'A', 'right', 'Room A-419')

        # --- B-wing rooms (right/south side) ---
        self._add_node('B-401_Right',  890, 440, 'room', 'B', 'right', 'Room B-401')
        self._add_node('B-402_Right',  940, 500, 'room', 'B', 'right', 'Room B-402')
        self._add_node('B-403_Right', 1000, 440, 'room', 'B', 'right', 'Room B-403')
        self._add_node('B-404_Right', 1050, 500, 'room', 'B', 'right', 'Room B-404')
        self._add_node('B-405_Right', 1100, 440, 'room', 'B', 'right', 'Room B-405')
        self._add_node('B-406_Right', 1150, 500, 'room', 'B', 'right', 'Room B-406')
        self._add_node('B-407_Right', 1230, 440, 'room', 'B', 'right', 'Room B-407')
        self._add_node('B-408_Right', 1280, 500, 'room', 'B', 'right', 'Room B-408')
        self._add_node('B-409_Right', 1340, 440, 'room', 'B', 'right', 'Room B-409')
        self._add_node('B-410_Right', 1390, 500, 'room', 'B', 'right', 'Room B-410')
        self._add_node('B-411_Right', 1440, 440, 'room', 'B', 'right', 'Room B-411')
        self._add_node('B-412_Right', 1500, 500, 'room', 'B', 'right', 'Room B-412')

        # --- B-wing rooms (left/north side) ---
        self._add_node('B-413_left', 1550, 280, 'room', 'B', 'left', 'Room B-413')
        self._add_node('B-415_left', 1340, 250, 'room', 'B', 'left', 'Room B-415')
        self._add_node('B-416_left', 1260, 300, 'room', 'B', 'left', 'Room B-416')
        self._add_node('B-418_left',  940, 250, 'room', 'B', 'left', 'Room B-418')
        self._add_node('B-419_left',  890, 300, 'room', 'B', 'left', 'Room B-419')

        # --- edges (step distances) ---

        # elevator to corridor
        self._add_edge('elevator', 'door_elevator', 6)
        self._add_edge('door_elevator', 'corridor_mid', 6)

        # corridor spine — A wing
        self._add_edge('corridor_mid', 'corridor_a1', 4)
        self._add_edge('corridor_a1', 'corridor_a2', 5)
        self._add_edge('corridor_a2', 'corridor_a3', 5)
        self._add_edge('corridor_a3', 'corridor_a4', 5)
        self._add_edge('corridor_a4', 'corridor_a5', 5)
        self._add_edge('corridor_a5', 'corridor_a6', 4)
        self._add_edge('corridor_a6', 'corridor_a7', 4)

        # corridor spine — B wing
        self._add_edge('corridor_mid', 'corridor_b1', 4)
        self._add_edge('corridor_b1', 'corridor_b2', 5)
        self._add_edge('corridor_b2', 'corridor_b3', 5)
        self._add_edge('corridor_b3', 'corridor_b4', 5)
        self._add_edge('corridor_b4', 'corridor_b5', 5)
        self._add_edge('corridor_b5', 'corridor_b6', 4)
        self._add_edge('corridor_b6', 'corridor_b7', 4)

        # A-wing left rooms -> corridor
        self._add_edge('A-401_left', 'corridor_a1', 3)
        self._add_edge('A-402_left', 'corridor_a1', 3)
        self._add_edge('A-403_left', 'corridor_a2', 3)
        self._add_edge('A-404_left', 'corridor_a2', 3)
        self._add_edge('A-405_left', 'corridor_a2', 3)
        self._add_edge('A-406_left', 'corridor_a3', 3)
        self._add_edge('A-407_left', 'corridor_a4', 3)
        self._add_edge('A-408_left', 'corridor_a4', 3)
        self._add_edge('A-409_left', 'corridor_a5', 3)
        self._add_edge('A-410_left', 'corridor_a5', 3)
        self._add_edge('A-411_left', 'corridor_a6', 3)
        self._add_edge('A-412_left', 'corridor_a6', 3)

        # A-wing right rooms -> corridor
        self._add_edge('A-413_Right', 'corridor_a7', 4)
        self._add_edge('A-415_Right', 'corridor_a4', 4)
        self._add_edge('A-416_Right', 'corridor_a3', 3)
        self._add_edge('A-418_Right', 'corridor_a1', 4)
        self._add_edge('A-419_Right', 'corridor_a1', 3)

        # G landmark
        self._add_edge('G', 'corridor_mid', 16)

        # B-wing right rooms -> corridor
        self._add_edge('B-401_Right', 'corridor_b1', 3)
        self._add_edge('B-402_Right', 'corridor_b1', 3)
        self._add_edge('B-403_Right', 'corridor_b2', 3)
        self._add_edge('B-404_Right', 'corridor_b2', 3)
        self._add_edge('B-405_Right', 'corridor_b2', 3)
        self._add_edge('B-406_Right', 'corridor_b3', 3)
        self._add_edge('B-407_Right', 'corridor_b4', 3)
        self._add_edge('B-408_Right', 'corridor_b4', 3)
        self._add_edge('B-409_Right', 'corridor_b5', 3)
        self._add_edge('B-410_Right', 'corridor_b5', 3)
        self._add_edge('B-411_Right', 'corridor_b6', 3)
        self._add_edge('B-412_Right', 'corridor_b6', 3)

        # B-wing left rooms -> corridor
        self._add_edge('B-413_left', 'corridor_b7', 4)
        self._add_edge('B-415_left', 'corridor_b5', 4)
        self._add_edge('B-416_left', 'corridor_b4', 3)
        self._add_edge('B-418_left', 'corridor_b1', 4)
        self._add_edge('B-419_left', 'corridor_b1', 3)

    def _add_node(self, node_id, x, y, node_type, wing, side, description):
        """Add a node to the graph."""
        if node_id not in self.graph:
            self.graph[node_id] = []
        self.node_positions[node_id] = (x, y)
        self.node_info[node_id] = {
            'type': node_type, 'wing': wing,
            'side': side, 'description': description
        }

    def _add_edge(self, node_a, node_b, weight):
        """Add an undirected edge between two nodes."""
        if node_a not in self.graph:
            self.graph[node_a] = []
        if node_b not in self.graph:
            self.graph[node_b] = []
        self.graph[node_a].append((node_b, weight))
        self.graph[node_b].append((node_a, weight))

    def find_shortest_path(self, start, end):
        """Find shortest path using Dijkstra's. Returns path, distance, directions."""
        if start not in self.graph or end not in self.graph:
            return None

        distances = {node: float('inf') for node in self.graph}
        distances[start] = 0
        previous = {node: None for node in self.graph}
        pq = [(0, start)]
        visited = set()

        while pq:
            current_dist, current_node = heapq.heappop(pq)
            if current_node in visited:
                continue
            visited.add(current_node)
            if current_node == end:
                break
            for neighbor, weight in self.graph[current_node]:
                if neighbor in visited:
                    continue
                new_dist = current_dist + weight
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current_node
                    heapq.heappush(pq, (new_dist, neighbor))

        if distances[end] == float('inf'):
            return None

        # reconstruct path
        path = []
        current = end
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()

        directions = self._generate_directions(path)
        path_positions = [self.node_positions[node] for node in path]

        return {
            'path': path,
            'distance': round(distances[end], 1),
            'directions': directions,
            'path_positions': path_positions
        }

    def _generate_directions(self, path):
        """Generate human-readable turn-by-turn directions."""
        if len(path) < 2:
            return ["You are already at the destination!"]

        directions = []
        start_info = self.node_info[path[0]]
        end_info = self.node_info[path[-1]]

        directions.append(f"📍 Start at: {start_info['description']}")

        i = 0
        while i < len(path) - 1:
            current = path[i]
            next_node = path[i + 1]
            curr_info = self.node_info[current]
            next_info = self.node_info[next_node]
            curr_pos = self.node_positions[current]
            next_pos = self.node_positions[next_node]

            if curr_info['type'] == 'landmark' and current == 'elevator':
                directions.append("🚶 Exit the elevator")

            elif curr_info['type'] == 'landmark' and current == 'door_elevator':
                directions.append("🚪 Walk through the door towards the main corridor")

            elif curr_info['type'] == 'room' and next_info['type'] == 'corridor':
                directions.append(f"🚶 Exit {curr_info['description']} into the corridor")

            elif curr_info['type'] == 'corridor' and next_info['type'] == 'corridor':
                dx = next_pos[0] - curr_pos[0]
                dy = next_pos[1] - curr_pos[1]

                if i > 0:
                    prev_pos = self.node_positions[path[i - 1]]
                    prev_dx = curr_pos[0] - prev_pos[0]
                    prev_dy = curr_pos[1] - prev_pos[1]

                    # detect turns
                    if abs(prev_dy) > abs(prev_dx) and abs(dx) > abs(dy):
                        if dx > 0:
                            directions.append("↪️ Turn RIGHT towards B-Wing")
                        else:
                            directions.append("↩️ Turn LEFT towards A-Wing")
                    elif abs(prev_dx) > abs(prev_dy) and abs(dy) > abs(dx):
                        if dy > 0:
                            directions.append("⬇️ Walk towards the elevator area")
                        else:
                            directions.append("⬆️ Walk towards the corridor")

            elif curr_info['type'] == 'corridor' and next_info['type'] == 'landmark':
                if next_node == 'door_elevator':
                    directions.append("🚪 Walk towards the elevator door")
                elif next_node == 'elevator':
                    directions.append("🛗 Proceed to the elevator")

            elif curr_info['type'] == 'corridor' and next_info['type'] == 'room':
                side_desc = ""
                if next_info['side'] == 'left':
                    side_desc = "on your LEFT (south side)" if next_info['wing'] == 'A' else "on your LEFT (north side)"
                elif next_info['side'] == 'right':
                    side_desc = "on your RIGHT (north side)" if next_info['wing'] == 'A' else "on your RIGHT (south side)"
                directions.append(f"🚪 {next_info['description']} is {side_desc}")

            i += 1

        # calculate corridor walking distance
        corridor_segments = []
        seg_start = None
        seg_distance = 0
        for j in range(len(path) - 1):
            if self.node_info[path[j]]['type'] == 'corridor' and self.node_info[path[j+1]]['type'] == 'corridor':
                if seg_start is None:
                    seg_start = j
                for neighbor, w in self.graph[path[j]]:
                    if neighbor == path[j+1]:
                        seg_distance += w
                        break
            else:
                if seg_start is not None:
                    corridor_segments.append((seg_start, j, seg_distance))
                    seg_start = None
                    seg_distance = 0
        if seg_start is not None:
            corridor_segments.append((seg_start, len(path)-1, seg_distance))

        if corridor_segments:
            total_corridor = sum(s[2] for s in corridor_segments)
            directions.insert(len(directions) - 1,
                f"🚶 Walk along the corridor (~{int(total_corridor)} meters)")

        directions.append(f"✅ You have arrived at: {end_info['description']}")

        # estimated time
        total_dist = sum(
            next(w for n, w in self.graph[path[j]] if n == path[j+1])
            for j in range(len(path)-1)
        )
        est_time = max(1, int(total_dist / 1.2 / 60))
        directions.append(f"⏱️ Estimated walking time: ~{est_time} min")

        return directions

    def get_room_name(self, location_label):
        """Convert 'A-401_left' to 'A-401', but preserve mid_corridor directions."""
        if 'mid_corridor' in location_label.lower():
            return location_label
        return location_label.replace('_left', '').replace('_Right', '').replace('_right', '')

    def find_node_for_location(self, location_label):
        """Find the graph node matching a WiFi location label or user input."""
        if not location_label:
            return None
            
        location_label = location_label.strip()
        
        if location_label in self.graph:
            return location_label
            
        # Try case-insensitive exact match
        lower_label = location_label.lower()
        for node in self.graph:
            if node.lower() == lower_label:
                return node
                
        # Try matching base room name (e.g., 'B-412' matches 'B-412_Right')
        clean_input = location_label.replace('-', '').lower()
        for node in self.graph:
            node_base = node.split('_')[0].replace('-', '').lower()
            if node_base == clean_input:
                return node
                
        return None

    def get_navigable_rooms(self):
        """Get all rooms and landmarks for the destination dropdown."""
        rooms = []
        for node_id, info in self.node_info.items():
            if info['type'] in ('room', 'landmark'):
                rooms.append({
                    'id': node_id, 'name': info['description'],
                    'wing': info['wing'], 'side': info['side']
                })
        rooms.sort(key=lambda r: (
            0 if r['wing'] is None else (1 if r['wing'] == 'A' else 2),
            r['name']
        ))
        return rooms

    def get_graph_data(self):
        """Export graph for frontend rendering."""
        nodes = []
        for node_id, (x, y) in self.node_positions.items():
            info = self.node_info[node_id]
            nodes.append({
                'id': node_id, 'x': x, 'y': y,
                'type': info['type'], 'wing': info['wing'],
                'side': info['side'], 'description': info['description']
            })

        edges = []
        seen = set()
        for node_id, neighbors in self.graph.items():
            for neighbor, weight in neighbors:
                edge_key = tuple(sorted([node_id, neighbor]))
                if edge_key not in seen:
                    seen.add(edge_key)
                    edges.append({'from': node_id, 'to': neighbor, 'weight': weight})

        return {'nodes': nodes, 'edges': edges}
