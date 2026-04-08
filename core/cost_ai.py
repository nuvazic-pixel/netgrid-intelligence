from road_utils import road_distance


def evaluate_nodes(G, real_df, nodes, take_rate, arpu, cost_per_meter):
    total_length = 0
    covered_set = set()

    for i, r in real_df.iterrows():
        best_dist = None

        for node in nodes:
            dist = road_distance(G, node['lat'], node['lon'], r['lat'], r['lon'])

            if dist is not None:
                if best_dist is None or dist < best_dist:
                    best_dist = dist

        if best_dist is not None:
            total_length += best_dist

            # consider covered dacă < 500m
            if best_dist <= 500:
                covered_set.add(i)

    covered = len(covered_set)

    # 💰 COST
    total_cost = total_length * cost_per_meter

    # 💸 REVENUE
    potential_subs = covered * (take_rate / 100)
    annual_revenue = potential_subs * arpu * 12

    # 📊 ROI
    roi = annual_revenue / total_cost if total_cost > 0 else 0

    return {
        'covered': covered,
        'total': len(real_df),
        'cost': total_cost,
        'revenue': annual_revenue,
        'roi': roi,
        'length_m': total_length
    }