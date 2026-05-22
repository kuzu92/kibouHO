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
    # 各メンバーの最終割り当て (None は未割り当て)
    assignments = {member: None for member in preferences.keys()}
    # 各役職の残り空き枠数
    remaining_roles = role_counts.copy()

    # 全員が提出した希望順位の最大値を取得（例: 3位まであれば 3）
    all_ranks = [
        r for prefs in preferences.values() if prefs for r in prefs.values()
    ]
    if not all_ranks:
        return assignments
    max_rank = max(all_ranks)

    # 【重要】第1希望、第2希望、第3希望... と「順位の階層」ごとに完全に区切って処理
    for rank in range(1, max_rank + 1):
        
        # この順位階層の中で、まだ未確定の人が希望している役職をリストアップ
        role_demands = {role: [] for role in role_counts.keys()}
        for member, prefs in preferences.items():
            if assignments[member] is not None:
                continue  # すでに上の順位で確定している人はスキップ

            # この順位に該当する役職を取得（同率順位に対応）
            desired_roles = [role for role, r in prefs.items() if r == rank]
            for role in desired_roles:
                if role in role_demands:
                    role_demands[role].append(member)

        # 希望者がいる役職に絞り、倍率（希望者数 ÷ 残り枠数）が高い順にソート
        active_roles = [r for r, count in remaining_roles.items() if count > 0 and len(role_demands[r]) > 0]
        sorted_roles = sorted(
            active_roles,
            key=lambda r: len(role_demands[r]) / remaining_roles[r],
            reverse=True
        )

        # 倍率の高い役職から順番に、この順位での割り当てを確定させていく
        for role in sorted_roles:
            candidates = role_demands[role]
            # 別の役職でこの順位（同率）がすでに確定した人を弾く
            valid_candidates = [c for c in candidates if assignments[c] is None]
            
            if not valid_candidates:
                continue

            # 同一条件内の不公平をなくすためランダムシャッフル
            random.shuffle(valid_candidates)

            # 空き枠の分だけ当選させる
            available_slots = remaining_roles[role]
            chosen_members = valid_candidates[:available_slots]

            for member in chosen_members:
                assignments[member] = f"{role} ({rank}希望)"
                remaining_roles[role] -= 1

    # 希望外分配（どこにも引っかからなかった人の救済）
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

    # バリデーション
    total_slots = sum(roles.values())
    total_people = len(preferences)
    if total_slots != total_people:
        print(f"【警告】総定員({total_slots}人)とメンバー数({total_people}人)が一致していません。\n")

    # 割り当て実行
    results = optimize_assignment(preferences, roles)

    # 結果の表示
    print("=== 役職割り当て結果 ===")
    print(f"{'名前':<10} | {'割り当て役職':<15}")
    print("-" * 35)
    for name, role in results.items():
        print(f"{name:<10} | {role:<15}")


if __name__ == "__main__":
    main()

