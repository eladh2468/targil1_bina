import search
import utils

# Student IDs
id = ["214880015"] 
"נערתי בבינה כדי להפוך את הרעיונות שלי לאיפטום ובניית העולם לקוד שאפשר להריץ"
"בנוסף, לאחר תקינות הקוד, נעזרתי בבינה בשביל להתייעץ על רעיונות חדשים לפרונינג בנוסף למה שחשבתי לבדי"

class ElevatorsProblem(search.Problem):
    """
    Elevator Problem Solver using A* Search.
    Optimized for high performance through aggressive state pruning 
    and an informed admissible heuristic.
    """
    def __init__(self, initial):
        search.Problem.__init__(self, initial)

    def successor(self, state):
        """
        Generates valid successors while pruning the search space.
        Uses Symmetry Breaking, empty elevator movement rule, 
        and Directional Picking to reduce the branching factor.
        """
        successors = []
        height, elevators, persons = state

        for e_idx, e_info in enumerate(elevators):
            e_id, e_floor, e_reachable, e_max_w, e_curr_w = e_info

            # --- 1. Symmetry Breaking ---
            # Prevents redundant states when identical empty elevators are at the same floor.
            is_redundant = False
            for prev_idx in range(e_idx):
                prev_e = elevators[prev_idx]
                if prev_e[2] == e_reachable and prev_e[3] == e_max_w:
                    if prev_e[1] == e_floor and prev_e[4] == 0 and e_curr_w == 0:
                        is_redundant = True
                        break
            if is_redundant:
                continue

            # --- 2. Direction Tracking ---
            # Tracks movement direction (1 for Up, -1 for Down) to enable directional picking.
            direction = 0  
            passengers_in_elevator = [p for p in persons if p[1] == e_id]
            if passengers_in_elevator:
                if passengers_in_elevator[0][3] > e_floor: direction = 1
                elif passengers_in_elevator[0][3] < e_floor: direction = -1

            # --- 3. Relevant Floors Identification (Rule 4 Implementation) ---
            # Determines floors worth visiting to avoid useless MOVE actions.
            relevant_floors = set()
            
            for p_info in persons:
                p_id, p_loc, p_w, p_g = p_info
                
                # Rule 4: Empty elevators only move to floors where passengers are waiting.
                if e_curr_w == 0:
                    if isinstance(p_loc, int) and p_loc != p_g and p_loc in e_reachable:
                        relevant_floors.add(p_loc)
                
                # Loaded elevators: Move to passenger destinations or transfer floors.
                else:
                    if p_loc == e_id:
                        if p_g in e_reachable:
                            relevant_floors.add(p_g)
                        else:
                            # Transfer Floors: Intersections with other elevator ranges.
                            for other_e in elevators:
                                if other_e[0] != e_id:
                                    common = set(e_reachable).intersection(set(other_e[2]))
                                    relevant_floors.update(common)
                    
                    # Directional Picking: Pick up passengers waiting in the same direction.
                    elif isinstance(p_loc, int) and p_loc != p_g and p_loc in e_reachable:
                        if e_curr_w + p_w <= e_max_w:
                            person_dir = 1 if p_g > p_loc else -1
                            if person_dir == direction and (p_loc - e_floor) * direction > 0:
                                relevant_floors.add(p_loc)

            # --- 4. MOVE Actions ---
            for target_floor in relevant_floors:
                if target_floor == e_floor:
                    continue
                new_elevators = list(elevators)
                new_elevators[e_idx] = (e_id, target_floor, e_reachable, e_max_w, e_curr_w)
                successors.append((f"MOVE{{{e_id},{target_floor}}}", (height, tuple(new_elevators), persons)))

            # --- 5. ENTER / EXIT Actions (Rule 5: Prioritization) ---
            
            # EXIT Actions: Checked first to free up weight capacity immediately.
            for p_idx, p_info in enumerate(persons):
                p_id, p_loc, p_w, p_g = p_info
                if p_loc == e_id:
                    is_transfer = any(e_floor in oe[2] for oe in elevators if oe[0] != e_id)
                    if e_floor == p_g or is_transfer:
                        new_elev_info = (e_id, e_floor, e_reachable, e_max_w, e_curr_w - p_w)
                        new_elevators = list(elevators)
                        new_elevators[e_idx] = new_elev_info
                        new_persons = list(persons)
                        new_persons[p_idx] = (p_id, e_floor, p_w, p_g)
                        successors.append((f"EXIT{{{p_id},{e_id}}}", (height, tuple(new_elevators), tuple(new_persons))))

            # ENTER Actions: Sorted by weight (Heavy to Light) to maximize capacity usage.
            people_at_floor = [p for p in persons if isinstance(p[1], int) and p[1] == e_floor]
            people_at_floor.sort(key=lambda x: x[2], reverse=True)
            
            for p_info in people_at_floor:
                p_id, p_loc, p_w, p_g = p_info
                if p_loc != p_g and e_curr_w + p_w <= e_max_w:
                    orig_idx = next(i for i, p in enumerate(persons) if p[0] == p_id)
                    new_elev_info = (e_id, e_floor, e_reachable, e_max_w, e_curr_w + p_w)
                    new_elevators = list(elevators)
                    new_elevators[e_idx] = new_elev_info
                    new_persons = list(persons)
                    new_persons[orig_idx] = (p_id, e_id, p_w, p_g)
                    successors.append((f"ENTER{{{p_id},{e_id}}}", (height, tuple(new_elevators), tuple(new_persons))))

        return successors

    def goal_test(self, state):
        """Returns True if all persons are at their target floors."""
        return all(isinstance(p[1], int) and p[1] == p[3] for p in state[2])

    def h_astar(self, node):
        """
        Admissible Heuristic: Counts mandatory atomic steps (ENTER/EXIT).
        Includes transfer penalties and a micro-tiebreaker for floor distance.
        This provides the primary performance boost for complex transfers (e.g., M3/M7).
        """
        state = node.state
        elevators = state[1]
        persons = state[2]
        h = 0
        
        for p in persons:
            p_loc, p_goal = p[1], p[3]
            if p_loc == p_goal:
                continue
            
            # Base Atomic Cost
            if isinstance(p_loc, str): # Passenger inside elevator
                e_info = next(e for e in elevators if e[0] == p_loc)
                # 1 if direct destination, 3 if transfer needed (EXIT + ENTER + EXIT)
                h += 1 if p_goal in e_info[2] else 3
            else: # Passenger waiting at floor
                # 2 if direct (ENTER + EXIT), 4 if transfer (ENTER + EXIT + ENTER + EXIT)
                can_go_direct = any(p_loc in e[2] and p_goal in e[2] for e in elevators)
                h += 2 if can_go_direct else 4
            
            # Tie-Breaker: Distance-based nudge to guide A* towards the goal floor.
            curr_floor = p_loc if isinstance(p_loc, int) else next(e[1] for e in elevators if e[0] == p_loc)
            h += abs(curr_floor - p_goal) * 0.01 
            
        return h

def create_elevators_problem(game):
    """Factory function to build the problem instance from game dictionary."""
    elev_list = []
    for eid, info in game["Elevators"].items():
        # (ID, Floor, ReachableFloors, MaxWeight, CurrentLoad)
        elev_list.append((str(eid), info[0], tuple(sorted(list(info[1]))), info[2], 0))
    pers_list = []
    for pid, info in game["Persons"].items():
        # (ID, Location, Weight, Goal)
        pers_list.append((pid, info[0], info[1], info[2]))
    return ElevatorsProblem((game["height"], tuple(elev_list), tuple(pers_list)))