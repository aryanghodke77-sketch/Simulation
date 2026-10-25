"""Evaluation UI component.

Provides auto-graded tasks (subnetting, packet analysis) and records
completion time and scores in SQLite.
"""
from __future__ import annotations

import random
import time
from typing import Any, Dict, Optional, Tuple

import streamlit as st

from network_lab.storage.database import (
    save_experiment,
    list_experiments,
    init_db,
)


# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------

_TASK_KEY = "eval_current_task"
_ANSWER_KEY = "eval_user_answer"
_RESULT_KEY = "eval_last_score"


def _start_task(task_name: str) -> None:
    st.session_state[_TASK_KEY] = task_name
    st.session_state[_ANSWER_KEY] = ""
    st.session_state[_RESULT_KEY] = None
    if "eval_start_time" not in st.session_state or st.session_state["eval_start_time"] is None:
        st.session_state["eval_start_time"] = time.time()


def _clear_result() -> None:
    st.session_state[_RESULT_KEY] = None
    st.session_state["eval_start_time"] = time.time()


@st.cache_data
def _pick_subnet_task(seed: int) -> Dict[str, Any]:
    """Pick a random CIDR subnetting question with a deterministic seed."""
    random.seed(seed)
    candidates = [
        ("10.0.0.0/8", 16),
            ("172.16.0.0/12", 20),
        ("192.168.0.0/16", 24),
            ("10.10.0.0/16", 20),
        ("172.31.0.0/16", 22),
            ("192.168.10.0/24", 27),
        ("10.20.30.0/24", 26),
            ("172.16.5.0/24", 28),
    ]
    cidr, new_prefix = random.choice(candidates)
    import ipaddress as _ip
    net = _ip.ip_network(cidr, strict=False)
    new_net = _ip.ip_network(f"0.0.0.0/{new_prefix}", strict=False)
    mask = new_net.netmask
    return {
        "question": f"Given the network {cidr}, what is the subnet mask (dotted decimal) when the prefix length is /{new_prefix}?",
        "answer": str(mask),
        "cidr": cidr,
        "new_prefix": new_prefix,
        "mask": str(mask),
    }


def _pick_packet_task(seed: int) -> Dict[str, Any]:
    """Pick a random packet-analysis question over a generated packet."""
    random.seed(seed)
    from network_lab.core.models import NetworkScenario
    from network_lab.simulation.traffic import TrafficFlow
    from network_lab.simulation.network import generate_packet

    sc = NetworkScenario("eval-packet")
    sc.add_device("PC_A")
    sc.add_device("PC_B")
    sc.connect("PC_A", "PC_B")
    sc.assign_ip("PC_A", "eth0", "10.0.0.1")
    sc.assign_ip("PC_B", "eth0", "10.0.0.2")

    proto = random.choice(["tcp", "udp"])
    src_port = random.choice([80, 443, 53, 1234])
    dst_port = random.choice([80, 443, 53, 8080])
    size = random.choice([64, 512, 1024, 1500])

    flow = TrafficFlow(
        source="PC_A",
        destination="PC_B",
        protocol=proto,
        size_bytes=size,
        src_port=src_port,
        dst_port=dst_port,
        count=1,
    )
    pkt = generate_packet(sc, flow, packet_index=0)

    question_type = random.choice(["protocol", "dst_port"])
    if question_type == "protocol":
        question = f"A packet travels from {pkt.source} to {pkt.destination}. What transport-layer protocol does it use?"
        answer = pkt.protocol.upper()
    else:
        question = f"A packet travels from {pkt.source} to {pkt.destination}. What is the destination port number?"
        answer = str(pkt.dst_port)

    return {
        "question": question,
        "answer": answer,
        "packet_id": pkt.id,
    }


def _grade_subnet_task(task: Dict[str, Any], user_input: str) -> Tuple[bool, str]:
    """Grade a subnetting answer. Accepts dotted decimal or hex or /n notation."""
    if not user_input.strip():
        return False, "No answer provided."
    raw = user_input.strip().lower()
    expected = task["answer"].lower()
    # Accept exact, dotted decimal, hex with 0x, or /n prefix
    if raw == expected:
        return True, "Correct."
    try:
        import ipaddress
        net = ipaddress.ip_network(f"0.0.0.0/{task['new_prefix']}", strict=False)
        mask_str = str(net.netmask)
        if raw == mask_str.lower():
            return True, "Correct."
    except ValueError:
        pass
    return False, f"Expected subnet mask for /{task['new_prefix']}, got '{user_input}'."


def _grade_packet_task(task: Dict[str, Any], user_input: str) -> Tuple[bool, str]:
    if not user_input.strip():
        return False, "No answer provided."
    raw = user_input.strip().lower()
    expected = task["answer"].lower()
    if raw == expected:
        return True, "Correct."
    return False, f"Expected '{task['answer']}', got '{user_input}'."


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

_TASK_MAP: Dict[str, Tuple[str, Any]] = {
    "Subnetting task": ("subnet", _pick_subnet_task),
    "Packet analysis task": ("packet", _pick_packet_task),
}


def render_evaluation(scenario) -> None:
    st.header("Evaluation")

    init_db()

    task_label = st.selectbox(
        "Select a task",
        list(_TASK_MAP.keys()) + ["Protocol task", "Error detection task"],
        key="eval_task",
    )

    st.caption("Complete the task below and submit your answer for auto-grading.")

    if task_label in _TASK_MAP:
        task_type, picker = _TASK_MAP[task_label]
        _present_auto_task(task_label, task_type, picker)
    else:
        _present_manual_task(task_label)

    st.divider()
    st.subheader("Saved experiments")
    _render_experiments()


def _present_auto_task(task_label: str, task_type: str, picker) -> None:
    seed = int(time.time()) % 1_000_000
    task = picker(seed)
    st.session_state[_TASK_KEY] = task_label
    st.session_state["_eval_task_data"] = task

    st.subheader("Question")
    st.write(task["question"])

    if "_eval_task_data" not in st.session_state:
        st.session_state["_eval_task_data"] = task

    task_data = st.session_state["_eval_task_data"]

    col1, col2 = st.columns([3, 1])
    with col1:
        answer = st.text_input(
            "Your answer",
            key="_eval_answer",
            value=st.session_state.get(_ANSWER_KEY, ""),
            placeholder="Type your answer here",
        )
        st.session_state[_ANSWER_KEY] = answer
        graded, msg = _grade_now(task_type, task_data, answer)
        if graded is not None:
            st.info(msg)
    with col2:
        st.write(" ")
        if st.button("Submit answer", key="_eval_submit"):
            ok, msg = _grade_now(task_type, task_data, answer)
            score = 100 if ok else 0
            st.session_state[_RESULT_KEY] = (ok, score, msg)
            _record_result(task_label, score)
            st.session_state["eval_start_time"] = None
            st.rerun()

    last = st.session_state.get(_RESULT_KEY)
    if last is not None:
        ok, score, msg = last
        st.subheader("Result")
        if ok:
            st.success(f"Correct! Score: {score}%")
        else:
            st.error(f"Incorrect. {msg}")
        if st.button("Try another question", key="_eval_again"):
            _clear_result()
            st.rerun()

    if st.button("Start task timer", key="_eval_start_timer"):
        st.session_state["eval_start_time"] = time.time()
        st.info("Timer started.")
        st.rerun()


def _grade_now(task_type: str, task: Dict[str, Any], answer: str) -> Tuple[bool, str]:
    if task_type == "subnet":
        ok, msg = _grade_subnet_task(task, answer)
        return ok, msg
    if task_type == "packet":
        ok, msg = _grade_packet_task(task, answer)
        return ok, msg
    return False, "Unknown task type."


def _record_result(task_label: str, score: int) -> None:
    participant = st.session_state.get("eval_participant", "anonymous")
    session_id = st.session_state.get("eval_session_id", "session-001")
    start = st.session_state.get("eval_start_time")
    elapsed = round(time.time() - start, 2) if start else 0.0
    try:
        save_experiment(
            participant=participant,
            session_id=session_id,
            task=task_label,
            completion_time=elapsed,
            score=score,
            attempts=1,
            feedback="Auto-graded." if score == 100 else "Not yet correct.",
        )
    except Exception as e:
        st.error(f"Could not record result: {e}")


def _present_manual_task(task_label: str) -> None:
    st.caption("This task is completed outside the auto-grader. Enter your result below.")

    col1, col2 = st.columns([3, 1])
    with col1:
        score = st.number_input("Your score (0-100)", min_value=0, max_value=100, value=0, key="eval_score")
        attempts = st.number_input("Attempts", min_value=1, value=1, key="eval_attempts")
        feedback = st.text_area("Feedback (optional)", key="eval_feedback")
    with col2:
        st.write(" ")
        if st.button("Save result", key="eval_save"):
            _save_result(task_label, score, attempts, feedback)


def _save_result(task: str, score: int, attempts: int, feedback: str) -> None:
    import network_lab.core.models as models
    from network_lab.core.state import default_scenario

    scenario = st.session_state.get("scenario")
    if scenario is None:
        scenario = default_scenario()

    participant = st.session_state.get("eval_participant", "anonymous")
    session_id = st.session_state.get("eval_session_id", "session-001")

    start = st.session_state.get("eval_start_time")
    if start is None:
        st.session_state["eval_start_time"] = time.time()
        st.info("Task started. Use 'Save result' when done.")
        return

    elapsed = time.time() - start
    st.session_state["eval_start_time"] = None

    try:
        save_experiment(
            participant=participant,
            session_id=session_id,
            task=task,
            completion_time=round(elapsed, 2),
            score=score,
            attempts=attempts,
            feedback=feedback,
        )
        st.success(f"Result saved: {task} ({score}%, {elapsed:.1f}s, {attempts} attempt(s)).")
        st.rerun()
    except Exception as e:
        st.error(f"Could not save: {e}")


def _render_experiments() -> None:
    rows = list_experiments()
    if not rows:
        st.info("No experiments recorded yet.")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _prototype_pick_subnet_task(seed: int) -> Dict[str, Any]:
    """Prototype: pick a random CIDR subnetting question with a deterministic seed.

    This is a temporary evaluator prototype used to validate question generation
    and grading before it is wired into the Streamlit UI.
    """
    random.seed(seed)
    candidates = [
        ("10.0.0.0/8", 16),
        ("172.16.0.0/12", 20),
        ("192.168.0.0/16", 24),
        ("10.10.0.0/16", 20),
        ("172.31.0.0/16", 22),
        ("192.168.10.0/24", 27),
        ("10.20.30.0/24", 26),
        ("172.16.5.0/24", 28),
    ]
    cidr, new_prefix = random.choice(candidates)
    import ipaddress as _ip
    net = _ip.ip_network(cidr, strict=False)
    new_net = _ip.ip_network(f"0.0.0.0/{new_prefix}", strict=False)
    mask = new_net.netmask
    return {
        "question": f"Given the network {cidr}, what is the subnet mask (dotted decimal) when the prefix length is /{new_prefix}?",
        "answer": str(mask),
        "cidr": cidr,
        "new_prefix": new_prefix,
        "mask": str(mask),
    }


def _prototype_pick_packet_task(seed: int) -> Dict[str, Any]:
    """Prototype: pick a random packet-analysis question over a generated packet."""
    random.seed(seed)
    from network_lab.core.models import NetworkScenario
    from network_lab.simulation.traffic import TrafficFlow
    from network_lab.simulation.network import generate_packet

    sc = NetworkScenario("eval-packet")
    sc.add_device("PC_A")
    sc.add_device("PC_B")
    sc.connect("PC_A", "PC_B")
    sc.assign_ip("PC_A", "eth0", "10.0.0.1")
    sc.assign_ip("PC_B", "eth0", "10.0.0.2")

    proto = random.choice(["tcp", "udp"])
    src_port = random.choice([80, 443, 53, 1234])
    dst_port = random.choice([80, 443, 53, 8080])
    size = random.choice([64, 512, 1024, 1500])

    flow = TrafficFlow(
        source="PC_A",
        destination="PC_B",
        protocol=proto,
        size_bytes=size,
        src_port=src_port,
        dst_port=dst_port,
        count=1,
    )
    pkt = generate_packet(sc, flow, packet_index=0)

    question_type = random.choice(["protocol", "dst_port"])
    if question_type == "protocol":
        question = f"A packet travels from {pkt.source} to {pkt.destination}. What transport-layer protocol does it use?"
        answer = pkt.protocol.upper()
    else:
        question = f"A packet travels from {pkt.source} to {pkt.destination}. What is the destination port number?"
        answer = str(pkt.dst_port)

    return {
        "question": question,
        "answer": answer,
        "packet_id": pkt.id,
    }


def _prototype_grade_subnet_task(task: Dict[str, Any], user_input: str) -> Tuple[bool, str]:
    """Prototype: grade a subnetting answer."""
    if not user_input.strip():
        return False, "No answer provided."
    raw = user_input.strip().lower()
    expected = task["answer"].lower()
    if raw == expected:
        return True, "Correct."
    try:
        import ipaddress
        net = ipaddress.ip_network(f"0.0.0.0/{task['new_prefix']}", strict=False)
        mask_str = str(net.netmask)
        if raw == mask_str.lower():
            return True, "Correct."
    except ValueError:
        pass
    return False, f"Expected subnet mask for /{task['new_prefix']}, got '{user_input}'."


def _prototype_grade_packet_task(task: Dict[str, Any], user_input: str) -> Tuple[bool, str]:
    if not user_input.strip():
        return False, "No answer provided."
    raw = user_input.strip().lower()
    expected = task["answer"].lower()
    if raw == expected:
        return True, "Correct."
    return False, f"Expected '{task['answer']}', got '{user_input}'."
