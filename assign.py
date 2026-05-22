import sys
import random
import yaml


def load_config(config_path="config.yaml"):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {config_path} が見つかりません。")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: YAMLファイルの解析に失敗しました: {e}")
        sys.exit(1)


def optimize_assignment(preferences, role_counts):
    assignments = {member: None for member in preferences.keys()}
    remaining_roles = role_counts.copy()

    # 最大順位の取得
    all_ranks = [
        r for prefs in preferences.values() if prefs for r in prefs.values()
    ]
    if not all_ranks:
        return assignments
    max_rank = max(all_ranks)

    # 1位、2位、3位... と順番に処理
    for rank in range(1, max_rank + 1):
        role_demands = {role: [] for role in role_counts.keys()}
        for member, prefs in preferences.items():
            if assignments[member] is not None:
                continue

            desired_roles = [
                role for role, r in prefs.items() if r == rank
            ]
            for role in desired_roles:
                if role in role_demands:
                    role_demands[role].append(member)

        # 希望倍率が高い（残枠に対して希望者が多い）役職から優先して処理
        sorted_roles = sorted(
            [r for r in role_counts.keys() if remaining_roles[r] > 0],
            key=lambda r: (
                len(role_demands[r]) / remaining_roles[r]
                if remaining_roles[r] > 0
                else 0
            ),
            reverse=True,
        )

        for role in sorted_roles:
            candidates = role_demands[role]
            valid_candidates = [
                c for c in candidates if assignments[c] is None
            ]

            # 同率順位内の不公平をなくすため、割り振る前に候補者をランダムシャッフル
            random.shuffle(valid_candidates)

            available_slots = remaining_roles[role]
            chosen_members = valid_candidates[:available_slots]

            for member in chosen_members:
                assignments[member] = f"{role} ({rank}希望)"
                remaining_roles[role] -= 1

    # 希望外分配
    unassigned_members = [m for m, r in assignments.items() if r is None]
    unfilled_roles = [r for r, count in remaining_roles.items() if count > 0]

    for member in unassigned_members:
        if unfilled_roles:
            spare_role = unfilled_roles[0]
            assignments[member] = f"{spare_role} (希望外分配)"
            remaining_roles[spare_role] -= 1
            if remaining_roles[spare_role] == 0:
                unfilled_roles.pop(0)

    return assignments


def main():
    config = load_config()
    roles = config.get("roles", {})
    preferences = config.get("preferences", {})

    # バリデーション: 総定員と総人数のチェック
    total_slots = sum(roles.values())
    total_people = len(preferences)
    if total_slots != total_people:
        print(
            f"【警告】総定員({total_slots}人)とメンバー数({total_people}人)が一致していません。"
        )

    # 割り当て実行
    results = optimize_assignment(preferences, roles)

    # 結果の表示
    print("\n=== 役職割り当て結果 ===")
    print(f"{'名前':<10} | {'割り当て役職':<15}")
    print("-" * 35)
    for name, role in results.items():
        print(f"{name:<10} | {role:<15}")


if __name__ == "__main__":
    main()
