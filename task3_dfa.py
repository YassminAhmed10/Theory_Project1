from dataclasses import dataclass, field
from task1_parser import RegexNode, parse_regex
from task2_followpos import annotate_tree


@dataclass
class DFAResult:
    states:       list[frozenset]
    start:        frozenset
    accept:       set[frozenset]
    dead:         frozenset | None
    alphabet:     list[str]
    transitions:  dict[frozenset, dict[str, frozenset]]
    state_names:  dict[frozenset, str] = field(default_factory=dict)
    pos_map:      dict = field(default_factory=dict)
    followpos:    dict = field(default_factory=dict)
    end_pos:      int  = 0
    minimized:    bool = False

    def name(self, state: frozenset) -> str:
        return self.state_names.get(state, str(set(state)))

    def is_accept(self, state: frozenset) -> bool:
        return state in self.accept

    def is_dead(self, state: frozenset) -> bool:
        return state == self.dead

    def summary(self) -> str:
        lines = [
            f"States     : {len(self.states)} (raw: {len(self.states)})",
            f"Alphabet   : {{ {', '.join(self.alphabet)} }}",
            f"Start      : {self.name(self.start)}  = {sorted(self.start)}",
            f"Accepting  : {', '.join(self.name(s) for s in self.accept)}",
        ]
        if self.dead is not None:
            lines.append(f"Dead state : {self.name(self.dead)}")
        lines.append(f"End-marker pos: {self.end_pos}")
        return "\n".join(lines)


def build_dfa(pattern: str) -> DFAResult:
    root    = parse_regex(pattern)
    pos_map, followpos = annotate_tree(root)

    end_pos = max(pos_map)

    alphabet = sorted({
        node.value
        for node in pos_map.values()
        if node.ntype == RegexNode.CHAR
    })

    start_state = frozenset(root.firstpos)
    unmarked:   list[frozenset]                      = [start_state]
    all_states: set[frozenset]                       = {start_state}
    transitions: dict[frozenset, dict[str, frozenset]] = {}

    while unmarked:
        S = unmarked.pop()
        transitions[S] = {}
        for a in alphabet:
            U = frozenset(
                pos
                for p in S
                if pos_map[p].value == a
                for pos in followpos[p]
            )
            if U:
                transitions[S][a] = U
                if U not in all_states:
                    all_states.add(U)
                    unmarked.append(U)

    accept = {s for s in all_states if end_pos in s}

    dead: frozenset | None = None
    needs_dead = False
    for S in list(all_states):
        for a in alphabet:
            if a not in transitions.get(S, {}):
                needs_dead = True
                break

    if needs_dead:
        dead = frozenset()
        all_states.add(dead)
        transitions[dead] = {a: dead for a in alphabet}
        for S in list(all_states):
            if S == dead:
                continue
            for a in alphabet:
                if a not in transitions[S]:
                    transitions[S][a] = dead

    ordered = [start_state] + sorted(
        (s for s in all_states if s != start_state),
        key=lambda s: (s == dead, sorted(s))
    )
    state_names = {s: f"S{i}" for i, s in enumerate(ordered)}

    return DFAResult(
        states      = ordered,
        start       = start_state,
        accept      = accept,
        dead        = dead,
        alphabet    = alphabet,
        transitions = transitions,
        state_names = state_names,
        pos_map     = pos_map,
        followpos   = followpos,
        end_pos     = end_pos,
        minimized   = False,
    )


def minimize_dfa(dfa: DFAResult) -> DFAResult:
    alphabet = dfa.alphabet

    accepting     = frozenset(dfa.accept)
    non_accepting = frozenset(s for s in dfa.states if s not in accepting)

    partition: list[frozenset] = []
    if accepting:
        partition.append(accepting)
    if non_accepting:
        partition.append(non_accepting)

    rev: dict[str, dict[frozenset, set[frozenset]]] = {
        a: {s: set() for s in dfa.states} for a in alphabet
    }
    for s, trans in dfa.transitions.items():
        for a, t in trans.items():
            rev[a][t].add(s)

    worklist = list(partition)

    while worklist:
        splitter = worklist.pop()
        for a in alphabet:
            X = frozenset(s for t in splitter for s in rev[a].get(t, set()))
            new_partition = []
            for group in partition:
                inter = group & X
                diff  = group - X
                if inter and diff:
                    new_partition.extend([inter, diff])
                    if group in worklist:
                        worklist.remove(group)
                        worklist.extend([inter, diff])
                    else:
                        worklist.append(inter if len(inter) <= len(diff) else diff)
                else:
                    new_partition.append(group)
            partition = new_partition

    rep: dict[frozenset, frozenset] = {}
    for group in partition:
        r = min(group, key=lambda s: sorted(s))
        for s in group:
            rep[s] = r

    min_states: set[frozenset] = set(rep.values())
    min_start   = rep[dfa.start]
    min_accept  = {rep[s] for s in dfa.accept}
    min_dead    = rep[dfa.dead] if dfa.dead is not None else None

    min_transitions: dict[frozenset, dict[str, frozenset]] = {}
    for group in partition:
        r = rep[next(iter(group))]
        orig = next(iter(group))
        min_transitions[r] = {
            a: rep[dfa.transitions[orig][a]]
            for a in alphabet
            if orig in dfa.transitions and a in dfa.transitions[orig]
        }

    ordered = [min_start] + sorted(
        (s for s in min_states if s != min_start),
        key=lambda s: (s == min_dead, sorted(s))
    )
    state_names = {s: f"S{i}" for i, s in enumerate(ordered)}

    return DFAResult(
        states      = ordered,
        start       = min_start,
        accept      = min_accept,
        dead        = min_dead,
        alphabet    = alphabet,
        transitions = min_transitions,
        state_names = state_names,
        pos_map     = dfa.pos_map,
        followpos   = dfa.followpos,
        end_pos     = dfa.end_pos,
        minimized   = True,
    )


def get_transition_table(dfa: DFAResult) -> list[list[str]]:
    header = ["State"] + dfa.alphabet
    rows   = [header]
    for s in dfa.states:
        row = [dfa.name(s)]
        for a in dfa.alphabet:
            t = dfa.transitions.get(s, {}).get(a)
            row.append(dfa.name(t) if t is not None else "—")
        rows.append(row)
    return rows


if __name__ == "__main__":
    pattern = "(aa|b)*a"
    dfa     = build_dfa(pattern)

    print("=== DFA Summary ===")
    print(dfa.summary())
    print()

    print("=== Transition Table ===")
    for row in get_transition_table(dfa):
        print("  ", "  ".join(f"{c:8s}" for c in row))

    print()
    print("=== After Minimization ===")
    mdfa = minimize_dfa(dfa)
    print(mdfa.summary())