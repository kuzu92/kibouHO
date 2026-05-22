import sys
import random
import yaml
import itertools

def load_config(config_path="config.yaml"):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {config_path} が見つかりません。")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: YAMLファイルの解析に失敗しました: {e}")
        sys.exit(1)

# --- モード1: 第1希望最優先モード (Satisfaction First) ---
def solve_satisfaction_first(preferences, role_counts):
    assignments = {member: None for member in preferences.keys()}
    remaining_roles = role_counts.copy()
    
    all_ranks = [r for prefs in preferences.values() if prefs for r in prefs.values()]
    max_rank = max(all_ranks) if all_ranks else 1

    for rank in range(1, max_rank + 1):
        role_demands = {role: [] for role in role_counts.keys()}
        for member, prefs in preferences.items():
            if assignments[member] is not None:
                continue
            desired_roles = [role for role, r in prefs.items() if r == rank]
            for role in desired_roles:
                if role in role_demands:
                    role_demands[role].append(member)

        active_roles = [r for r, count in remaining_roles.items() if count > 0 and len(role_demands[r]) > 0]
        sorted_roles = sorted(
            active_roles,
            key=lambda r: len(role_demands[r]) / remaining_roles[r],
            reverse=True
        )

        for role in sorted_roles:
            candidates = role_demands[role]
            valid_candidates = [c for c in candidates if assignments[c] is None]
            if not valid_candidates:
                continue
            
            random.shuffle(valid_candidates)
            available_slots = remaining_roles[role]
            chosen_members = valid_candidates[:available_slots]

            for member in chosen_members:
                assignments[member] = (role, rank, False)
                remaining_roles[role] -= 1

    # 希望外分配
    _assign_unfilled(assignments, remaining_roles)
    return assignments

# --- モード2: ワースト回避モード (Fairness First) ---
def solve_fairness_first(preferences, role_counts):
    members = list(preferences.keys())
    
    # 各役職の枠をフラットなリストに展開 (例: {'HO1': 2} -> ['HO1', 'HO1'])
    flat_roles = []
    for role, count in role_counts.items():
        flat_roles.extend([role] * count)
        
    if len(members) != len(flat_roles):
        # 人数と定員が合わない場合は、標準モードにフォールバックして処理
        print("【注意】人数と総定員が一致しないため、第1希望最優先モードで代用します。")
        return solve_satisfaction_first(preferences, role_counts)

    # 全員の一番悪い順位（ワースト度合い）が最も低くなる組み合わせを探す
    best_patterns = []
    min_max_penalty = float('inf')
    min_total_penalty = float('inf')

    # すべての配分パターンを走査（重複のない順列）
    # ※数万人規模の巨大データでなければ一瞬で計算が終わります
    seen_combinations = set()
    for p in itertools.permutations(flat_roles):
        # 役職の重複パターンをスキップして高速化
        if p in seen_combinations:
            continue
        seen_combinations.add(p)
        
        current_max_penalty = 0
        current_total_penalty = 0
        current_pattern = {}

        for member, role in zip(members, p):
            # 希望順位を取得（未記入の場合は重いペナルティ）
            rank = preferences[member].get(role, 99)
            current_pattern[member] = (role, rank, rank == 99)
            
            # ペナルティの計算（下位ほど指数関数的に重くする）
            penalty = rank ** 4 if rank != 99 else 10000
            current_total_penalty += penalty
            if penalty > current_max_penalty:
                current_max_penalty = penalty

        # 条件判定1: 誰か一人の最大不満度（ワースト）が過去のパターンより低いか
        if current_max_penalty < min_max_penalty:
            min_max_penalty = current_max_penalty
            min_total_penalty = current_total_penalty
            best_patterns = [current_pattern]
        # 条件判定2: ワーストが同等なら、全員の不満度合計が最も低いか
        elif current_max_penalty == min_max_penalty:
            if current_total_penalty < min_total_penalty:
                min_total_penalty = current_total_penalty
                best_patterns = [current_pattern]
            elif current_total_penalty == min_total_penalty:
                best_patterns.append(current_pattern)

    # 最適なパターンの中からランダムに1つを決定（不公平性の排除）
    return random.choice(best_patterns)

def _assign_unfilled(assignments, remaining_roles):
    unassigned_members = [m for m, r in assignments.items() if r is None]
    unfilled_roles = [r for r, count in remaining_roles.items() if count > 0]
    for member in unassigned_members:
        if unfilled_roles:
            spare_role = unfilled_roles[0]
            assignments[member] = (spare_role, None, True)
            remaining_roles[spare_role] -= 1
            if remaining_roles[spare_role] == 0:
                unfilled_roles.pop(0)

def main():
    config = load_config()
    mode = config.get("mode", "satisfaction_first")
    roles = config.get("roles", {})
    preferences = config.get("preferences", {})

    total_slots = sum(roles.values())
    total_people = len(preferences)
    if total_slots != total_people:
        print(f"【警告】総定員({total_slots}人)とメンバー数({total_people}人)が一致していません。\n")

    # モードに応じた関数を実行
    if mode == "fairness_first":
        results = solve_fairness_first(preferences, roles)
    else:
        results = solve_satisfaction_first(preferences, roles)

    # 結果の表示
    print(f"=== 役職割り当て結果 ({'ワースト回避モード' if mode == 'fairness_first' else '第1希望最優先モード'}) ===")
    print(f"{'名前':<10} | {'割り当て役職':<15}")
    print("-" * 35)
    for name, (role, rank, is_out_of_bounds) in results.items():
        if is_out_of_bounds:
            display_role = f"{role} (希望外分配)"
        else:
            display_role = f"{role} ({rank}希望)"
        print(f"{name:<10} | {display_role:<15}")

if __name__ == "__main__":
    main()
