"""Error Detection UI component.

Demonstrates parity, checksum, and CRC error detection over a payload,
with optional error injection.
"""
from __future__ import annotations

import streamlit as st

from network_lab.modules.errors.engine import detect_error, compare_methods


def render_error_detection(scenario) -> None:
    st.header("Error Detection")

    st.subheader("Configure test payload")
    payload_hex = st.text_input("Payload (hex)", value="48656C6C6F", key="ed_payload_hex")
    try:
        payload = bytes.fromhex(payload_hex)
    except ValueError:
        st.error("Invalid hex payload.")
        return

    method = st.selectbox("Detection method", ["parity", "checksum", "crc", "compare all"], key="ed_method")
    inject = st.checkbox("Inject an error", value=False, key="ed_inject")
    error_bit = st.number_input("Error bit position (0-7)", min_value=0, max_value=7, value=0, key="ed_bit")

    if st.button("Run detection", key="ed_run"):
        try:
            if method == "compare all":
                results = compare_methods(payload, inject_error=inject, error_location=error_bit)
                for r in results:
                    _render_detection_result(r)
            else:
                result = detect_error(payload, method=method, inject_error=inject, error_location=error_bit)
                _render_detection_result(result)
        except ValueError as e:
            st.error(str(e))

    st.divider()
    st.subheader("About")
    st.markdown(
        """- **Parity:** Even-parity bit over the byte; detects any odd number of bit flips.
- **Checksum:** 8-bit one's complement sum; simple integrity check for teaching.
- **CRC:** CRC-8 over the payload; stronger detection than parity/checksum for common errors.

When *Inject an error* is enabled, a single bit is flipped in the transmitted
data to demonstrate detection."""
    )


def _render_detection_result(result: dict) -> None:
    st.markdown(f"### {result['method'].upper()}")
    st.metric("Error injected", "Yes" if result["error_injected"] else "No")
    st.metric("Error detected", "Yes" if result["error_detected"] else "No")

    if result["details"]:
        with st.expander("Details"):
            st.json(result["details"])

    if result["error_detected"]:
        st.success("Transmission error was detected.")
    else:
        st.info("No error detected (either no error was injected, or the method missed it).")
