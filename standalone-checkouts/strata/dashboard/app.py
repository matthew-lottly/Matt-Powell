"""Streamlit dashboard for exploring STRATA benchmark outputs."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    try:
        import pandas as pd
        import plotly.express as px
        import streamlit as st
    except ImportError as exc:
        raise SystemExit(
            "Install dashboard extras first: pip install -e .[dashboard]"
        ) from exc

    st.set_page_config(page_title="STRATA Dashboard", layout="wide")
    st.title("STRATA Benchmark Dashboard")

    outputs_dir = Path(__file__).resolve().parents[1] / "outputs"
    csv_files = sorted(outputs_dir.glob("*.csv"))
    if not csv_files:
        st.warning("No CSV outputs found in outputs/.")
        return

    selected = st.selectbox("Benchmark file", csv_files, format_func=lambda path: path.name)
    frame = pd.read_csv(selected)
    st.dataframe(frame, use_container_width=True)

    numeric_cols = [col for col in frame.columns if frame[col].dtype.kind in "fi"]
    if "method" in frame.columns and numeric_cols:
        metric = st.selectbox("Metric", numeric_cols)
        fig = px.box(frame, x="method", y=metric, points="all", title=f"{metric} by method")
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
