def select_guaranteed_and_fill(sub_questions, per_sq_hits, all_merged, cap=10):
    guaranteed = {}
    
    # 1. Guarantee top 2 for each sub-question
    for idx in range(len(sub_questions)):
        sq_list = per_sq_hits.get(idx, {}).get("sq", [])
        rc_list = per_sq_hits.get(idx, {}).get("rc", [])
        
        sq_picks = []
        # If both sq and rc exist, take top from sq and top from rc
        if sq_list:
            sq_picks.append(sq_list[0])
        if rc_list:
            for h in rc_list:
                if h["verse_id"] not in [p["verse_id"] for p in sq_picks]:
                    sq_picks.append(h)
                    break
        # If still less than 2, fill from sq_list then rc_list
        for h in sq_list + rc_list:
            if len(sq_picks) >= 2:
                break
            if h["verse_id"] not in [p["verse_id"] for p in sq_picks]:
                sq_picks.append(h)
                
        for h in sq_picks[:2]:
            vid = h["verse_id"]
            if vid not in guaranteed:
                guaranteed[vid] = dict(all_merged[vid])
                
    # 2. Fill remaining slots up to cap by best score
    remaining = [v for vid, v in all_merged.items() if vid not in guaranteed]
    remaining.sort(key=lambda x: -x["score"])
    
    slots_left = cap - len(guaranteed)
    filled = list(guaranteed.values()) + remaining[:slots_left]
    filled.sort(key=lambda x: -x["score"])
    return filled

