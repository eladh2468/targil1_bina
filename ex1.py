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

            # --- 1. שבירת סימטריה (Symmetry Breaking) ---
            is_redundant = False
            for prev_idx in range(e_idx):
                prev_e = elevators[prev_idx]
                if prev_e[2] == e_reachable and prev_e[3] == e_max_w:
                    if prev_e[1] == e_floor and prev_e[4] == 0 and e_curr_w == 0:
                        is_redundant = True
                        break
            if is_redundant:
                continue

            # --- 2. זיהוי כיוון המעלית הנוכחי ---
            direction = 0  # 0 = פנויה, 1 = למעלה, -1 = למטה
            passengers_in_elevator = [p for p in persons if p[1] == e_id]
            if passengers_in_elevator:
                if passengers_in_elevator[0][3] > e_floor: direction = 1
                elif passengers_in_elevator[0][3] < e_floor: direction = -1

            # --- 3. זיהוי קומות רלוונטיות (חוק 4 משולב פה) ---
            relevant_floors = set()
            
            for p_info in persons:
                p_id, p_loc, p_w, p_g = p_info
                
                # אם המעלית ריקה - נעה רק לקומות שיש בהן אנשים שמחכים (חוק 4)
                if e_curr_w == 0:
                    if isinstance(p_loc, int) and p_loc != p_g and p_loc in e_reachable:
                        relevant_floors.add(p_loc)
                
                # אם המעלית בתפוסה - נעה ליעדי הנוסעים או לאיסוף בכיוון הנסיעה
                else:
                    # יעד של נוסע בפנים
                    if p_loc == e_id:
                        if p_g in e_reachable:
                            relevant_floors.add(p_g)
                        else:
                            # קומות טרנספר (מעבר)
                            for other_e in elevators:
                                if other_e[0] != e_id:
                                    common = set(e_reachable).intersection(set(other_e[2]))
                                    relevant_floors.update(common)
                    
                    # איסוף נוסע נוסף בדרך (Directional Picking)
                    elif isinstance(p_loc, int) and p_loc != p_g and p_loc in e_reachable:
                        if e_curr_w + p_w <= e_max_w:
                            person_dir = 1 if p_g > p_loc else -1
                            if person_dir == direction and (p_loc - e_floor) * direction > 0:
                                relevant_floors.add(p_loc)

            # --- 4. יצירת פעולות MOVE ---
            for target_floor in relevant_floors:
                if target_floor == e_floor:
                    continue
                new_elevators = list(elevators)
                new_elevators[e_idx] = (e_id, target_floor, e_reachable, e_max_w, e_curr_w)
                successors.append((f"MOVE{{{e_id},{target_floor}}}", (height, tuple(new_elevators), persons)))

            # --- 5. יצירת פעולות ENTER / EXIT (חוק 5: תיעדוף ומיון) ---
            
            # EXIT תמיד נבדוק קודם (כדי לפנות מקום למשקל חדש)
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

            # ENTER - מיון האנשים בקומה מהכבד לקל (למקסום ניצולת)
            people_at_floor = [p for p in persons if isinstance(p[1], int) and p[1] == e_floor]
            people_at_floor.sort(key=lambda x: x[2], reverse=True)
            
            for p_info in people_at_floor:
                p_id, p_loc, p_w, p_g = p_info
                if p_loc != p_g and e_curr_w + p_w <= e_max_w:
                    # מוצאים אינדקס מקורי
                    orig_idx = next(i for i, p in enumerate(persons) if p[0] == p_id)
                    new_elev_info = (e_id, e_floor, e_reachable, e_max_w, e_curr_w + p_w)
                    new_elevators = list(elevators)
                    new_elevators[e_idx] = new_elev_info
                    new_persons = list(persons)
                    new_persons[orig_idx] = (p_id, e_id, p_w, p_g)
                    successors.append((f"ENTER{{{p_id},{e_id}}}", (height, tuple(new_elevators), tuple(new_persons))))

        return successors

    def goal_test(self, state):
        return all(isinstance(p[1], int) and p[1] == p[3] for p in state[2])

    def h_astar(self, node):
        state = node.state
        elevators = state[1]
        persons = state[2]
        h = 0
        
        for p in persons:
            p_loc, p_goal = p[1], p[3]
            if p_loc == p_goal:
                continue
            
            # עלות בסיסית של פעולות ENTER/EXIT
            if isinstance(p_loc, str): # בתוך מעלית
                e_info = next(e for e in elevators if e[0] == p_loc)
                h += 1 if p_goal in e_info[2] else 3
            else: # מחכה בקומה
                can_go_direct = any(p_loc in e[2] and p_goal in e[2] for e in elevators)
                h += 2 if can_go_direct else 4
            
            # חיזוק: הוספת מרחק קומות מינימלי (חלקי 10 כדי לשמור על קבילות)
            # בבעיה שבה כל תנועה עולה 1, המרחק הוא חסם תחתון לעלות התנועה.
            curr_floor = p_loc if isinstance(p_loc, int) else next(e[1] for e in elevators if e[0] == p_loc)
            h += abs(curr_floor - p_goal) * 0.01 # מקדם קטן מאוד רק כדי לשבור שיוויון לטובת כיוון נכון
            
        return h

def create_elevators_problem(game):
    elev_list = []
    for eid, info in game["Elevators"].items():
        elev_list.append((str(eid), info[0], tuple(sorted(list(info[1]))), info[2], 0))
    pers_list = []
    for pid, info in game["Persons"].items():
        pers_list.append((pid, info[0], info[1], info[2]))
    return ElevatorsProblem((game["height"], tuple(elev_list), tuple(pers_list)))