import math
import pandas as pd

from multi_node import kmeans_nodes
from geo.road_utils import road_distance


def classify_density(lat, lon, center_lat, center_lon):
    '''
    Very simple proxy:
    closer to city center => more urban => more expensive trenching
    '''
    dist = math.sqrt((lat - center_lat) ** 2 + (lon - center_lon) ** 2)

    if dist < 0.03:
        return 'urban'
    elif dist < 0.08:
        return 'suburban'
    return 'rural'


def density_cost_multiplier(density_type):
    multipliers = {
        'urban': 1.35,
        'suburban': 1.0,
        'rural': 0.75
    }
    return multipliers.get(density_type, 1.0)


def deployment_multiplier(deployment_type):
    mapping = {
        'Trenching': 1.0,
        'Aerial': 0.65,
        'Microtrenching': 0.82
    }
    return mapping.get(deployment_type, 1.0)


def evaluate_node_config(
    G,
    real_df,
    nodes,
    take_rate,
    arpu,
    base_cost_per_meter,
    subsidy_pct,
    deployment_type,
    center_lat,
    center_lon,
    max_connection_distance_m=500
):
    total_length_m = 0
    covered_indices = set()
    detailed_rows = []

    dep_multi = deployment_multiplier(deployment_type)

    for idx, row in real_df.iterrows():
        best_dist = None
        best_node = None

        for node_idx, node in enumerate(nodes):
            dist = road_distance(G, node['lat'], node['lon'], row['lat'], row['lon'])

            if dist is not None:
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_node = node_idx

        if best_dist is None:
            continue

        density_type = classify_density(row['lat'], row['lon'], center_lat, center_lon)
        density_multi = density_cost_multiplier(density_type)

        effective_cost_per_meter = base_cost_per_meter * dep_multi * density_multi
        connection_cost = best_dist * effective_cost_per_meter

        total_length_m += best_dist

        is_covered = best_dist <= max_connection_distance_m
        if is_covered:
            covered_indices.add(idx)

        detailed_rows.append({
            'building_index': idx,
            'best_node': best_node,
            'road_distance_m': round(best_dist, 1),
            'density_type': density_type,
            'effective_cost_per_meter': round(effective_cost_per_meter, 2),
            'connection_cost_eur': round(connection_cost, 2),
            'covered': is_covered
        })

    covered = len(covered_indices)
    total_buildings = len(real_df)

    detailed_df = pd.DataFrame(detailed_rows)

    gross_cost = detailed_df['connection_cost_eur'].sum() if not detailed_df.empty else 0
    subsidy_amount = gross_cost * (subsidy_pct / 100)
    net_cost = gross_cost - subsidy_amount

    potential_subscribers = covered * (take_rate / 100)
    annual_revenue = potential_subscribers * arpu * 12
    monthly_revenue = potential_subscribers * arpu

    roi_annual = annual_revenue / net_cost if net_cost > 0 else 0
    payback_years = net_cost / annual_revenue if annual_revenue > 0 else None
    coverage_pct = (covered / total_buildings * 100) if total_buildings > 0 else 0
    avg_connection_distance = (
        detailed_df[detailed_df['covered']]['road_distance_m'].mean()
        if not detailed_df.empty and covered > 0 else None
    )

    return {
        'nodes': nodes,
        'covered': covered,
        'total_buildings': total_buildings,
        'coverage_pct': coverage_pct,
        'gross_cost': gross_cost,
        'subsidy_amount': subsidy_amount,
        'net_cost': net_cost,
        'annual_revenue': annual_revenue,
        'monthly_revenue': monthly_revenue,
        'potential_subscribers': potential_subscribers,
        'roi_annual': roi_annual,
        'payback_years': payback_years,
        'total_length_m': total_length_m,
        'avg_connection_distance_m': avg_connection_distance,
        'detail_df': detailed_df
    }


def optimize_ftth_plan(
    G,
    real_df,
    take_rate,
    arpu,
    base_cost_per_meter,
    subsidy_pct,
    deployment_type,
    center_lat,
    center_lon,
    node_options=(2, 3, 4, 5),
    max_connection_distance_m=500
):
    if real_df.empty:
        return None

    best_result = None

    for k in node_options:
        if len(real_df) < k:
            continue

        nodes = kmeans_nodes(real_df, k=k)

        result = evaluate_node_config(
            G=G,
            real_df=real_df,
            nodes=nodes,
            take_rate=take_rate,
            arpu=arpu,
            base_cost_per_meter=base_cost_per_meter,
            subsidy_pct=subsidy_pct,
            deployment_type=deployment_type,
            center_lat=center_lat,
            center_lon=center_lon,
            max_connection_distance_m=max_connection_distance_m
        )

        result['k_nodes'] = k

        if best_result is None or result['roi_annual'] > best_result['roi_annual']:
            best_result = result

    return best_result