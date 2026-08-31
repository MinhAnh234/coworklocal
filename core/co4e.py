"""Co4E — node-graph workflow engine (ported from nova-platform's Flow feature).

A Co4E *workflow* is a graph of step nodes joined by edges. Steps run in
topological **waves** (all nodes at the same depth run together); a *parallel*
node fans out into one stage per sub-agent plus an optional join stage the wave
after. Each node names an agent persona (built-in or custom), optional attached
skills, a model, a permission preset and instructions; at run time these compile
into per-stage prompts fed to the agent, with each wave's outputs threaded into
the next wave's prompts.

This module is PURE PYTHON (no Qt) so the model, store, wave computation and
stage compilation are all unit-testable. UI lives in ``ui/co4e_*`` and the
runner that actually calls the provider lives in ``core/co4e_runner.py``.

Persistence: one JSON file per workflow under ``~/.cowork_local/co4e/workflows``
and one per custom agent under ``~/.cowork_local/co4e/agents``. Skills reuse the
existing ``core/skills.py`` registry.
"""
from __future__ import annotations

from ..infrastructure.persistence.json.atomic_json_file import AtomicJsonFile

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ..config import CONFIG_DIR

CO4E_DIR = CONFIG_DIR / "co4e"
WORKFLOWS_DIR = CO4E_DIR / "workflows"
AGENTS_DIR = CO4E_DIR / "agents"

# ---- enums ---------------------------------------------------------------
STEP_IDLE, STEP_PENDING, STEP_RUNNING, STEP_DONE, STEP_ERROR, STEP_PLANNED = (
    "idle", "pending", "running", "done", "error", "planned")

PERMISSION_PRESETS = ("inherit", "read-only", "standard", "full")
# preset -> allowed tool names (None = all tools; enforced by run_cowork's
# allowed_tools filter — update_plan is always allowed on top of these since it
# only drives the plan panel and touches nothing). "save_file" is Cowork's way
# of writing a deliverable, so it belongs to "standard" (write) but NOT "read-only".
PRESET_SCOPES: Dict[str, Optional[List[str]]] = {
    "inherit": None,
    "read-only": ["read_file", "list_dir", "fetch_url"],
    "standard": ["read_file", "list_dir", "write_file", "edit_file", "save_file", "fetch_url"],
    "full": None,
}

# auto   — each step's agent plans then executes automatically (default)
# plan   — read-only: each step only drafts a plan, nothing is written
# manual — step-by-step: run one step at a time, review, then advance ("Next step")
RUN_MODES = ("auto", "plan", "manual")


def slugify(value: str) -> str:
    """Chuyển một chuỗi thành slug an toàn cho tên file: chỉ chữ/số/gạch, gộp gạch
    liên tiếp. Rỗng thì trả về 'step' để không bao giờ sinh ra tên file trống.
    """
    s = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (value or "").strip().lower())
    return "-".join(filter(None, s.split("-"))) or "step"


# ---- data model ----------------------------------------------------------
@dataclass
class SubAgent:
    """One concurrent worker inside a parallel node."""
    agent: str = ""          # palette agent NAME (built-in or custom)
    instructions: str = ""   # per-sub-agent extra instructions


@dataclass
class Step:
    """A node's persona/config (mirrors nova StepNodeData)."""
    variant: str = "step"            # "step" | "parallel"
    label: str = "New Step"
    agent_slug: str = "custom-step"
    role: str = "AGENT"              # UPPERCASE badge
    icon: str = ""                   # line-icon name ("" = role default)
    instructions: str = ""
    context: str = ""                # extra background/info injected into the prompt
    model: str = ""                  # "" = active provider's default model
    # Auto self-check each step before advancing (Claude-CLI-style quality gate) —
    # ON by default so a flow verifies (and fixes) each step's work automatically.
    self_verify: bool = True
    max_verify_rounds: int = 1
    permission_preset: str = "full"  # steps default to full workspace access
    skills: List[str] = field(default_factory=list)      # registry skill NAMES
    attachments: List[str] = field(default_factory=list)  # local file paths fed to the step
    sub_agents: List[SubAgent] = field(default_factory=list)  # parallel only

    @property
    def is_parallel(self) -> bool:
        """Bước này có chạy nhiều sub-agent song song hay không."""
        return self.variant == "parallel"


@dataclass
class Node:
    """Một node trên khung vẽ: id, toạ độ, và bước (:class:`Step`) mà nó đại diện."""
    id: str
    x: float = 0.0
    y: float = 0.0
    data: Step = field(default_factory=Step)


@dataclass
class Edge:
    """Một cạnh nối hai node, quy định thứ tự chạy giữa chúng."""
    id: str
    source: str
    target: str


@dataclass
class Workflow:
    """Một luồng Co4E: danh sách node, cạnh, và cờ đánh dấu đây có phải mẫu không."""
    id: str
    name: str = "Untitled flow"
    is_template: bool = False
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)


@dataclass
class CustomAgent:
    """A persisted custom Co4E agent persona (mirrors nova CustomFlowAgent)."""
    id: str
    name: str = ""
    role: str = "AGENT"
    instructions: str = ""
    context: str = ""                # extra background/info injected into the prompt
    model: str = ""
    permission_preset: str = "full"
    icon: str = ""
    skills: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)  # local file paths fed to the agent


# ---- (de)serialization ---------------------------------------------------
def step_from_dict(d: dict) -> Step:
    """Dựng :class:`Step` từ dict đọc trên đĩa.

    Lọc bỏ khoá lạ để file luồng của phiên bản mới hơn không làm vỡ bản cũ.
    """
    d = dict(d or {})
    subs = d.pop("sub_agents", None) or []
    known = Step().__dict__.keys()
    step = Step(**{k: v for k, v in d.items() if k in known})
    step.sub_agents = [
        SubAgent(agent=s.get("agent", ""), instructions=s.get("instructions", ""))
        if isinstance(s, dict) else SubAgent(agent=str(s))
        for s in subs
    ]
    return step


def node_from_dict(d: dict) -> Node:
    """Dựng :class:`Node` từ dict đọc trên đĩa."""
    return Node(id=str(d.get("id", "")), x=float(d.get("x", 0) or 0),
                y=float(d.get("y", 0) or 0), data=step_from_dict(d.get("data", {})))


def workflow_from_dict(d: dict) -> Workflow:
    """Dựng :class:`Workflow` từ dict đọc trên đĩa."""
    return Workflow(
        id=str(d.get("id", "")),
        name=d.get("name", "Untitled flow"),
        is_template=bool(d.get("is_template", False)),
        nodes=[node_from_dict(n) for n in d.get("nodes", [])],
        edges=[Edge(id=str(e.get("id", "")), source=str(e.get("source", "")),
                    target=str(e.get("target", ""))) for e in d.get("edges", [])],
    )


def workflow_to_dict(wf: Workflow) -> dict:
    """Chuyển một luồng thành dict để ghi JSON."""
    return {
        "id": wf.id, "name": wf.name, "is_template": wf.is_template,
        "nodes": [{"id": n.id, "x": n.x, "y": n.y, "data": _step_dict(n.data)} for n in wf.nodes],
        "edges": [asdict(e) for e in wf.edges],
    }


def _step_dict(step: Step) -> dict:
    """Chuyển một bước thành dict; ``asdict`` đã tự chuyển ``sub_agents`` thành list dict."""
    d = asdict(step)
    # asdict already turns sub_agents into list[dict]
    return d


def agent_to_dict(a: CustomAgent) -> dict:
    """Chuyển một agent tự tạo thành dict để ghi JSON."""
    return asdict(a)


def agent_from_dict(d: dict) -> CustomAgent:
    """Dựng :class:`CustomAgent` từ dict, lọc bỏ khoá lạ."""
    known = CustomAgent(id="").__dict__.keys()
    d = {k: v for k, v in (d or {}).items() if k in known}
    d.setdefault("id", "")
    a = CustomAgent(**d)
    a.skills = list(a.skills or [])
    a.attachments = list(a.attachments or [])
    return a


# ---- id minting (no time/random — deterministic counter per process) -----
_counter = {"n": 0}


def _mint_id(prefix: str) -> str:
    """Sinh id tăng dần dạng ``<prefix>_000001``."""
    _counter["n"] += 1
    return f"{prefix}_{_counter['n']:06d}"


def new_node_id() -> str:
    """Id mới cho một node."""
    return _mint_id("node")


def new_edge_id(source: str, target: str) -> str:
    """Id cạnh suy ra TỪ cặp nguồn/đích.

    Cố ý không ngẫu nhiên: nhờ vậy nối lại đúng cặp node đó luôn cho ra cùng
    một id, và không thể sinh ra hai cạnh trùng nhau.
    """
    return f"e_{source}__{target}"


def new_workflow(name: str = "Untitled flow") -> Workflow:
    """Tạo một luồng rỗng với id mới."""
    return Workflow(id=_mint_id("wf"), name=name)


def new_custom_agent(name: str = "") -> CustomAgent:
    """Tạo một agent tự tạo rỗng với id mới."""
    return CustomAgent(id=_mint_id("agent"), name=name)


# ---- workflow store ------------------------------------------------------
def workflows_dir() -> Path:
    """Thư mục chứa file luồng."""
    return WORKFLOWS_DIR


def list_workflows(directory: Optional[Path] = None) -> List[Workflow]:
    """Liệt kê mọi luồng đã lưu; thư mục chưa có thì trả list rỗng."""
    directory = directory or WORKFLOWS_DIR
    if not directory.exists():
        return []
    out: List[Workflow] = []
    for path in sorted(directory.glob("*.json")):
        try:
            out.append(workflow_from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return out


def save_workflow(wf: Workflow, directory: Optional[Path] = None) -> Path:
    """Ghi một luồng ra ``<id>.json``, tự tạo thư mục nếu chưa có."""
    directory = directory or WORKFLOWS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{wf.id}.json"
    # Tiêu chí nghiệm thu A: mọi thao tác ghi tệp đi qua AtomicJsonFile. Trước
    # đây ghi thẳng, nên tắt máy giữa lúc lưu là mất luôn workflow.
    AtomicJsonFile(path).write(workflow_to_dict(wf))
    return path


def get_workflow(wf_id: str, directory: Optional[Path] = None) -> Optional[Workflow]:
    """Đọc một luồng theo id; ``None`` nếu không có."""
    directory = directory or WORKFLOWS_DIR
    path = directory / f"{wf_id}.json"
    if not path.exists():
        return None
    try:
        return workflow_from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def duplicate_workflow(wf: Workflow, directory: Optional[Path] = None) -> Workflow:
    """Save a deep copy of ``wf`` under a fresh id and a "… (copy)" name, so it can
    be run in parallel with (or diverge from) the original. Node/edge ids are kept
    — they're only unique *within* a workflow, and each run gets its own id."""
    import copy as _copy

    dup = Workflow(
        id=_mint_id("wf"),
        name=f"{wf.name} ({tr_copy_suffix()})",
        nodes=[_copy.deepcopy(n) for n in wf.nodes],
        edges=[_copy.deepcopy(e) for e in wf.edges],
        is_template=False,
    )
    save_workflow(dup, directory)
    return dup


def tr_copy_suffix() -> str:
    """Localised 'copy' suffix — kept tiny + import-safe (no hard i18n dependency
    at module import time)."""
    try:
        from ..i18n import tr
        return tr("co4e.copy_suffix")
    except Exception:  # noqa: BLE001
        return "copy"


def delete_workflow(wf_id: str, directory: Optional[Path] = None) -> None:
    """Xoá file luồng theo id; không có thì bỏ qua."""
    directory = directory or WORKFLOWS_DIR
    path = directory / f"{wf_id}.json"
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


# ---- custom-agent store --------------------------------------------------
def agents_dir() -> Path:
    """Thư mục chứa file agent tự tạo."""
    return AGENTS_DIR


def list_custom_agents(directory: Optional[Path] = None) -> List[CustomAgent]:
    """Liệt kê mọi agent tự tạo; thư mục chưa có thì trả list rỗng."""
    directory = directory or AGENTS_DIR
    if not directory.exists():
        return []
    out: List[CustomAgent] = []
    for path in sorted(directory.glob("*.json")):
        try:
            out.append(agent_from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return out


def save_custom_agent(agent: CustomAgent, directory: Optional[Path] = None) -> Path:
    """Ghi một agent tự tạo ra ``<id>.json``."""
    directory = directory or AGENTS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{agent.id}.json"
    AtomicJsonFile(path).write(agent_to_dict(agent))
    return path


def delete_custom_agent(agent_id: str, directory: Optional[Path] = None) -> None:
    """Xoá file agent tự tạo theo id; không có thì bỏ qua."""
    directory = directory or AGENTS_DIR
    path = directory / f"{agent_id}.json"
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


# ---- wave computation ----------------------------------------------------
def compute_waves(nodes: List[Node], edges: List[Edge]) -> Dict[str, int]:
    """node id -> wave index (longest path from a root). Ignores edges that
    reference unknown nodes; cycles are broken defensively (a node never waits
    on itself transitively past the node count)."""
    ids = {n.id for n in nodes}
    preds: Dict[str, List[str]] = {n.id: [] for n in nodes}
    for e in edges:
        if e.source in ids and e.target in ids:
            preds[e.target].append(e.source)

    wave: Dict[str, int] = {}
    limit = len(nodes) + 1

    def depth(nid: str, seen: frozenset) -> int:
        """Độ sâu của một node = lớp chạy của nó.

        Có nhớ kết quả và chặn theo ``limit``: đồ thị có vòng sẽ khiến đệ quy chạy
        mãi, nên gặp node đã thấy trong nhánh hiện tại thì dừng.
        """
        if nid in wave:
            return wave[nid]
        if nid in seen or len(seen) > limit:
            return 0
        ps = preds.get(nid, [])
        w = 0 if not ps else 1 + max(depth(p, seen | {nid}) for p in ps)
        wave[nid] = w
        return w

    for n in nodes:
        depth(n.id, frozenset())
    return wave


def connected_component_count(nodes: List[Node], edges: List[Edge]) -> int:
    """Weakly-connected component count — >1 warns a flow is accidentally split."""
    ids = {n.id for n in nodes}
    parent = {n.id: n.id for n in nodes}

    def find(x):
        """Tìm gốc của một phần tử, kèm nén đường đi (union-find)."""
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        """Gộp hai tập hợp lại làm một (union-find)."""
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for e in edges:
        if e.source in ids and e.target in ids:
            union(e.source, e.target)
    return len({find(n.id) for n in nodes})


# ---- run-stage compilation ----------------------------------------------
@dataclass
class RunStage:
    """Một chặng chạy: ứng với một node, hoặc một nhánh song song / bước gộp của nó."""
    id: str              # node id, or "<node>__p<i>" / "<node>__pjoin"
    node_id: str         # which canvas node this stage maps back onto
    wave: int
    prompt: str
    model: str = ""
    scope: Optional[List[str]] = None
    self_verify: bool = False
    max_verify_rounds: int = 1


PLAN_MODE_PREAMBLE = (
    "PLAN MODE — do NOT execute anything or change any files. Produce a concise, "
    "numbered plan of what you WOULD do for this step, then stop.\n\n")


def build_skills_block(skills: List[str], skill_map: Dict[str, str]) -> str:
    """Ghép nội dung các skill được chọn thành một khối chèn vào prompt."""
    parts = []
    for name in skills or []:
        content = (skill_map.get(name) or "").strip()
        if content:
            parts.append(f'--- Skill "{name}" ---\n{content}')
    if not parts:
        return ""
    return ("\nThis agent carries the following attached skills (reusable "
            "instruction packs):\n" + "\n\n".join(parts) + "\n")


def _shared_prompt_parts(step: Step, skill_map: Dict[str, str], extra_context: str) -> str:
    """Phần prompt dùng chung cho cả ba loại chặng: chỉ dẫn của bước, khối skill,
    và ngữ cảnh thêm từ các bước trước.
    """
    parts = []
    if step.instructions.strip():
        parts.append(step.instructions.strip())
    # Extra step/agent context (free-text background the user added in config) —
    # injected so the agent has more information to carry out its task.
    if getattr(step, "context", "").strip():
        parts.append("Additional context:\n" + step.context.strip())
    block = build_skills_block(step.skills, skill_map)
    if block:
        parts.append(block)
    if extra_context:
        parts.append(extra_context)
    return "\n\n".join(parts)


def build_step_prompt(step: Step, skill_map: Dict[str, str], extra_context: str = "") -> str:
    """Prompt cho một bước chạy tuần tự bình thường."""
    head = f'You are the {step.role} agent for the workflow step "{step.label}".'
    body = _shared_prompt_parts(step, skill_map, extra_context)
    return f"{head}\n{body}".strip()


def build_subagent_prompt(step: Step, sub: SubAgent, peers: List[str],
                          skill_map: Dict[str, str], extra_context: str = "") -> str:
    """Prompt cho một sub-agent chạy song song.

    Nói rõ nó đang chạy CÙNG LÚC với những ai và phải ở trong phạm vi của mình —
    không có câu đó, các sub-agent hay làm chồng việc của nhau.
    """
    peer_txt = ", ".join(p for p in peers if p) or "peers"
    head = (f'You are the "{sub.agent}" agent working concurrently (in parallel with '
            f'{peer_txt}) on the workflow step "{step.label}". Stay within your own scope.')
    parts = [head]
    if sub.instructions.strip():
        parts.append(sub.instructions.strip())
    shared = _shared_prompt_parts(step, skill_map, extra_context)
    if shared:
        parts.append(shared)
    return "\n\n".join(parts).strip()


def build_join_prompt(step: Step, skill_map: Dict[str, str], extra_context: str = "") -> str:
    """Prompt cho bước gộp: hợp nhất đầu ra của các sub-agent thành một kết quả."""
    head = (f'You are the coordinator for the parallel step "{step.label}". Consolidate the '
            f"outputs of the sub-agents (provided above as prior outputs) into one coherent result.")
    body = _shared_prompt_parts(step, skill_map, extra_context)
    return f"{head}\n{body}".strip()


def compile_run_stages(nodes: List[Node], edges: List[Edge],
                       extra_context: Dict[str, str] = None,
                       plan_mode: bool = False,
                       skill_map: Dict[str, str] = None) -> List[RunStage]:
    """Compile canvas nodes into ordered RunStages. ``extra_context`` maps a
    node id to text (upstream outputs) to append to that node's prompt."""
    extra_context = extra_context or {}
    skill_map = skill_map or {}
    waves = compute_waves(nodes, edges)
    stages: List[RunStage] = []

    def finalize(prompt: str, preset: str) -> tuple:
        """Chốt prompt của một chặng: áp phạm vi theo preset, và thêm lời mở đầu chế
        độ lập kế hoạch nếu đang chạy ở chế độ đó.
        """
        scope = PRESET_SCOPES.get(preset)
        if plan_mode:
            prompt = PLAN_MODE_PREAMBLE + prompt
            scope = PRESET_SCOPES["read-only"]
        return prompt, scope

    for node in nodes:
        step = node.data
        w = waves.get(node.id, 0)
        ctx = extra_context.get(node.id, "")
        if step.is_parallel and step.sub_agents:
            peers = [s.agent for s in step.sub_agents]
            for i, sub in enumerate(step.sub_agents):
                prompt = build_subagent_prompt(step, sub, peers, skill_map, ctx)
                prompt, scope = finalize(prompt, step.permission_preset)
                stages.append(RunStage(
                    id=f"{node.id}__p{i}", node_id=node.id, wave=w, prompt=prompt,
                    model=step.model, scope=scope))
            if step.instructions.strip():
                prompt, scope = finalize(build_join_prompt(step, skill_map), step.permission_preset)
                stages.append(RunStage(
                    id=f"{node.id}__pjoin", node_id=node.id, wave=w + 1, prompt=prompt,
                    model=step.model, scope=scope,
                    self_verify=step.self_verify, max_verify_rounds=max(1, step.max_verify_rounds)))
        else:
            prompt, scope = finalize(build_step_prompt(step, skill_map, ctx), step.permission_preset)
            stages.append(RunStage(
                id=node.id, node_id=node.id, wave=w, prompt=prompt, model=step.model, scope=scope,
                self_verify=step.self_verify, max_verify_rounds=max(1, step.max_verify_rounds)))
    stages.sort(key=lambda s: s.wave)
    return stages


def stage_node_id(stage_id: str) -> str:
    """Map a stage id back onto its canvas node ('<node>__p2' -> '<node>')."""
    for sep in ("__pjoin", "__p"):
        if sep in stage_id:
            return stage_id.split(sep, 1)[0]
    return stage_id
