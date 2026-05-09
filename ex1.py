import search
import utils

# רשימת ה-ID של הסטודנטים
id = ["123456789"] 

class ElevatorsProblem(search.Problem):
    def __init__(self, initial):
        search.Problem.__init__(self, initial)

    def successor(self, state):
        successors = []
        height, elevators, persons = state

        for e_idx, e_info in enumerate(elevators):
            e_id, e_floor, e_reachable, e_max_w, e_curr_w = e_info

            # --- 1. זיהוי קומות רלוונטיות (Target Floors) ---
            relevant_floors = set()
            for p_info in persons:
                p_id, p_loc, p_w, p_g = p_info
                
                # קומה שבה אדם מחכה בחוץ
                if isinstance(p_loc, int) and p_loc in e_reachable:
                    if e_curr_w + p_w <= e_max_w:
                        relevant_floors.add(p_loc)
                
                # קומה שהיא היעד של מישהו בתוך המעלית הזו
                if p_loc == e_id:
                    if p_g in e_reachable:
                        relevant_floors.add(p_g)
                    else:
                        # קומת מעבר (Transfer): קומה שמשותפת למעלית נוספת
                        for other_e in elevators:
                            if other_e[0] != e_id:
                                common = set(e_reachable).intersection(set(other_e[2]))
                                relevant_floors.update(common)

            # --- 2. MOVE ---
            for target_floor in relevant_floors:
                if target_floor == e_floor:
                    continue
                new_elevators = list(elevators)
                new_elevators[e_idx] = (e_id, target_floor, e_reachable, e_max_w, e_curr_w)
                successors.append((f"MOVE{{{e_id},{target_floor}}}", (height, tuple(new_elevators), persons)))

            # --- 3. ENTER / EXIT ---
            for p_idx, p_info in enumerate(persons):
                p_id, p_loc, p_w, p_g = p_info

                # ENTER
                if isinstance(p_loc, int) and p_loc == e_floor and e_curr_w + p_w <= e_max_w:
                    new_elevators = list(elevators)
                    new_elevators[e_idx] = (e_id, e_floor, e_reachable, e_max_w, e_curr_w + p_w)
                    new_persons = list(persons)
                    new_persons[p_idx] = (p_id, e_id, p_w, p_g)
                    successors.append((f"ENTER{{{p_id},{e_id}}}", (height, tuple(new_elevators), tuple(new_persons))))

                # EXIT
                if p_loc == e_id:
                    # אדם יוצא אם זה היעד שלו או קומת מעבר
                    is_transfer = any(e_floor in oe[2] for oe in elevators if oe[0] != e_id)
                    if e_floor == p_g or is_transfer:
                        new_elevators = list(elevators)
                        new_elevators[e_idx] = (e_id, e_floor, e_reachable, e_max_w, e_curr_w - p_w)
                        new_persons = list(persons)
                        new_persons[p_idx] = (p_id, e_floor, p_w, p_g)
                        successors.append((f"EXIT{{{p_id},{e_id}}}", (height, tuple(new_elevators), tuple(new_persons))))

        return successors

    def goal_test(self, state):
        return all(isinstance(p[1], int) and p[1] == p[3] for p in state[2])

    def h_astar(self, node):
        return 0;

def create_elevators_problem(game):
    elev_list = []
    for eid, info in game["Elevators"].items():
        elev_list.append((str(eid), info[0], tuple(sorted(list(info[1]))), info[2], 0))
    pers_list = []
    for pid, info in game["Persons"].items():
        pers_list.append((pid, info[0], info[1], info[2]))
    return ElevatorsProblem((game["height"], tuple(elev_list), tuple(pers_list)))