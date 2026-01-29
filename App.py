# Self-Service Analytics Dashboard

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.figure_factory as ff
from io import BytesIO
from fpdf import FPDF
import tempfile
import datetime


def save_fig_as_png(fig):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.write_image(tmp.name, engine="kaleido")
    return tmp.name

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(page_title="Self-Service Dashboard", layout="wide", page_icon="📊")

st.markdown("""
<style>
/* App background */
.stApp {
    background: radial-gradient(circle at top left, #0f172a, #020617);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #020617;
    border-right: 1px solid #1e293b;
}

/* Headers */
h1, h2, h3 {
    color: #e5e7eb;
    letter-spacing: 0.3px;
}

/* Cards / containers */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #020617, #020617);
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 16px;
}

/* Buttons */
button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 10px;
}

/* Info / success / warning boxes */
.stAlert {
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


st.title("📊 Self-Service Analytics Dashboard")
st.markdown("Upload → Clean → Build Dashboard → Analyze → Export")

def build_chart(df, config):
    chart_type = config.get("chart_type")
    x = config.get("x_col")
    y = config.get("y_col")
    title = config.get("title", "")

    if chart_type == "Bar":
        fig = px.bar(df, x=x, y=y)

    elif chart_type == "Line":
        fig = px.line(df, x=x, y=y)

    elif chart_type == "Scatter":
        fig = px.scatter(df, x=x, y=y)

    elif chart_type == "Histogram":
        fig = px.histogram(df, x=x)

    elif chart_type == "Box":
        fig = px.box(df, x=x, y=y)

    else:
        return None

    fig.update_layout(title=title)
    return fig



# ============================================
# SESSION STATE
# ============================================
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None
    
if "df" not in st.session_state:
    st.session_state.df = None

if "dashboard_charts" not in st.session_state:
    st.session_state.dashboard_charts = []

if "dashboard_versions" not in st.session_state:
    st.session_state.dashboard_versions = {}

# ============================================
# SIDEBAR NAVIGATION
# ============================================
selected_tab = st.sidebar.radio(
    "📂 Navigation",
    [
        "📤 Upload Data",
        "🧹 Cleaning",
        "📈 Dashboard Builder",
        "🧠 Insights & Analysis",
        "💾 Export",
    ],
)

# ============================================
# TAB 1: UPLOAD DATA
# ============================================


if selected_tab == "📤 Upload Data":
    st.caption(
    "A self-service analytics tool that allows non-technical users to explore data, "
    "build dashboards, analyze patterns, and export insights — without writing code."
    )
    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                st.session_state.df = pd.read_csv(uploaded_file)
            else:
                st.session_state.df = pd.read_excel(uploaded_file)

            st.success("✅ File uploaded successfully")
            st.caption(
                f"Dataset: {len(st.session_state.df):,} rows × {st.session_state.df.shape[1]} columns"
            )
            st.dataframe(st.session_state.df.head(20), use_container_width=True)

        except Exception as e:
            st.error(f"Error reading file: {e}")

# ============================================
# TAB 2: DATA CLEANING
# ============================================
elif selected_tab == "🧹 Cleaning":
    df = st.session_state.df

    if df is None:
        st.warning("Please upload data first.")
        st.stop()

    st.subheader("🧹 Data Cleaning")

    row_limit = st.slider(
        "Rows to preview",
        min_value=10,
        max_value=min(1000, len(df)),
        value=200,
        step=10,
    )
    st.dataframe(df.head(row_limit), use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Remove Duplicates"):
            before = len(df)
            df.drop_duplicates(inplace=True)
            st.success(f"Removed {before - len(df)} duplicate rows")

    with col2:
        if st.button("Fill Missing Values (Forward Fill)"):
            df.fillna(method="ffill", inplace=True)
            st.success("Missing values filled")

    st.divider()

    st.subheader("⬇️ Download Cleaned Dataset")

    csv_bytes = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download Cleaned Data (CSV)",
        data=csv_bytes,
        file_name="cleaned_dataset.csv",
        mime="text/csv",
        )


# ============================================
# TAB 3: DASHBOARD BUILDER (MAIN IMPROVEMENT)
# ============================================
if st.session_state.edit_index is not None:
    if st.session_state.edit_index >= len(st.session_state.dashboard_charts):
        st.session_state.edit_index = None

elif selected_tab == "📈 Dashboard Builder":
    df = st.session_state.df

    if df is None:
        st.warning("Please upload data first.")
        st.stop()

    st.subheader("📈 Self-Service Dashboard Builder")

    # ---------- GLOBAL FILTERS ----------
    with st.expander("🔍 Global Filters", expanded=True):
        with st.container():
            st.markdown("### 🔍 Global Filters")

            filtered_df = df.copy()

            filter_cols = st.multiselect(
                "Select columns to filter",
                df.columns,
            )

            for col in filter_cols:
                if df[col].dtype == "object":
                    selected_vals = st.multiselect(
                        f"Filter {col}",
                        df[col].dropna().unique(),
                    )
                    if selected_vals:
                        filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]

                elif np.issubdtype(df[col].dtype, np.number):
                    min_val, max_val = float(df[col].min()), float(df[col].max())
                    selected_range = st.slider(
                        f"Filter {col}",
                        min_val,
                        max_val,
                        (min_val, max_val),
                    )
                    filtered_df = filtered_df[
                        (filtered_df[col] >= selected_range[0])
                        & (filtered_df[col] <= selected_range[1])
                    ]
            # Save filtered data for export
            st.session_state.filtered_df = filtered_df.copy()


    # ---------- KPI SECTION ----------
    with st.expander("📊 Key Metrics", expanded=True):
        with st.container():
            st.markdown("### 📊 Key Metrics")
        
            st.caption(f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

            numeric_cols = filtered_df.select_dtypes(include=["int64", "float64"]).columns

            if len(numeric_cols) > 0:
                k1, k2, k3 = st.columns(3)
                k1.metric("Total Records", f"{len(filtered_df):,}")
                k2.metric(f"Average {numeric_cols[0]}", f"{filtered_df[numeric_cols[0]].mean():.2f}")
                k3.metric(f"Maximum {numeric_cols[0]}", f"{filtered_df[numeric_cols[0]].max():.2f}")

            st.divider()

    # ---------- CHART BUILDER ----------
    with st.expander("➕ Add Chart", expanded=True):
        with st.container():
            st.markdown("### ➕ Add Chart")

            all_cols = filtered_df.columns.tolist()

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                chart_type = st.selectbox(
                    "Chart Type",
                    ["Bar", "Line", "Scatter", "Histogram", "Box"],
                )

            with c2:
                x_col = st.selectbox("X-axis", all_cols)

            with c3:
                y_col = st.selectbox(
                    "Y-axis (optional)",
                    ["None"] + numeric_cols.tolist(),
                )

            with c4:
                chart_title = st.text_input("Chart Title", value=f"{chart_type} Chart")

            if st.button("➕ Add to Dashboard"):
                fig = None

                if chart_type == "Bar":
                    fig = px.bar(filtered_df, x=x_col, y=None if y_col == "None" else y_col)

                elif chart_type == "Line":
                    fig = px.line(filtered_df, x=x_col, y=None if y_col == "None" else y_col)

                elif chart_type == "Scatter":
                    fig = px.scatter(filtered_df, x=x_col, y=None if y_col == "None" else y_col)

                elif chart_type == "Histogram":
                    fig = px.histogram(filtered_df, x=x_col)

                elif chart_type == "Box":
                    fig = px.box(filtered_df, x=x_col, y=None if y_col == "None" else y_col)

                fig.update_layout(title=chart_title)

                st.session_state.dashboard_charts.append({
                    "chart_type": chart_type,
                    "x_col": x_col,
                    "y_col": None if y_col == "None" else y_col,
                    "title": chart_title
                })

                st.success("Chart added to dashboard")
            
    #------------------EDIT PANEL----------------------------
        
        if (
            st.session_state.edit_index is not None
            and isinstance(st.session_state.edit_index, int)
            and st.session_state.edit_index < len(st.session_state.dashboard_charts)
        ):
            with st.container():
                st.subheader("✏️ Edit Chart")
                cfg = st.session_state.dashboard_charts[st.session_state.edit_index]
                
                Chart_types =["Bar", "Line", "Scatter", "Histogram", "Box"]

                new_type = st.selectbox(
                    "Chart Type",
                    chart_types,
                    index=chart_types.index(cfg["chart_type"])
                )

                new_x = st.selectbox("X-axis", filtered_df.columns, index=filtered_df.columns.get_loc(cfg["x_col"]))
                new_y = st.selectbox("Y-axis", ["None"] + numeric_cols.tolist(),
                                     index=(numeric_cols.tolist().index(cfg["y_col"]) + 1 if cfg["y_col"] else 0))

                new_title = st.text_input("Title", value=cfg["title"])

                if st.button("💾 Save Changes"):
                    st.session_state.dashboard_charts[st.session_state.edit_index] = {
                        "chart_type": new_type,
                        "x_col": new_x,
                        "y_col": None if new_y == "None" else new_y,
                        "title": new_title
                    }
                    st.session_state.edit_index = None
                    st.success("Chart updated")
                    st.rerun()


    # ------------------ DASHBOARD VERSIONS ------------------
    with st.expander("📁 Dashboard Versions"):
        with st.container():
            st.subheader("📚 Dashboard Versions")

            version_name = st.text_input("Version name", placeholder="e.g. Sales v1")

            col_v1, col_v2 = st.columns(2)

            with col_v1:
                if st.button("💾 Save Version"):
                    if not version_name:
                        st.warning("Please enter a version name.")
                    else:
                        st.session_state.dashboard_versions[version_name] = (
                            st.session_state.dashboard_charts.copy()
                        )
                        st.success(f"Version '{version_name}' saved.")

            with col_v2:
                versions = list(st.session_state.dashboard_versions.keys())
                selected_version = st.selectbox(
                    "Load version",
                    ["None"] + versions,
                    key="load_version"
                )

                if selected_version != "None":
                    st.session_state.dashboard_charts = (
                        st.session_state.dashboard_versions[selected_version].copy()
                    )
                    st.success(f"Loaded version: {selected_version}")
                    st.rerun()
#-----------------------------------------------------
    with st.expander("🧹 Dashboard Controls"):
        with st.container():
            st.subheader("🧹 Dashboard Controls")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                if st.button("🗑️ Clear Dashboard"):
                    st.session_state.dashboard_charts = []
                    st.session_state.edit_index = None
                    st.success("Dashboard cleared")
                    st.rerun()

            with col_c2:
                if st.button("🔄 Reset Dashboard"):
                    st.session_state.dashboard_charts = []
                    st.session_state.dashboard_versions = {}
                    st.session_state.edit_index = None
                    st.success("Dashboard fully reset")
                    st.rerun()

            st.divider()
        
    # ---------- DASHBOARD VIEW ----------
    st.info(f"📊 Charts in dashboard: {len(st.session_state.dashboard_charts)}")

    with st.expander("📊 Your Dashboard", expanded=True):
        with st.container():
            st.markdown("### 📊 Your Dashboard")

            if st.session_state.dashboard_charts:
                for i, chart_cfg in enumerate(st.session_state.dashboard_charts):
                    with st.container():
                        fig = build_chart(filtered_df, chart_cfg)
                        fig.update_layout(
                            template="plotly_dark",
                            margin=dict(l=20, r=20, t=50, b=20),
                            title_x=0.02
                        )

                        if fig:
                            st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}")

                            # 🔍 DRILL-DOWN DATA
                            with st.expander("🔍 View underlying data"):
                                cols = [chart_cfg["x_col"]]
                                if chart_cfg["y_col"]:
                                    cols.append(chart_cfg["y_col"])

                                st.dataframe(
                                    filtered_df[cols].head(200),
                                    use_container_width=True
                                )
                            # ✏️ Edit / 🗑 Delete buttons
                            c1, c2, c3 = st.columns([6, 1, 1])

                            with c2:
                                if st.button("✏️ Edit", key=f"edit_{i}"):
                                    st.session_state.edit_index = i
                                    st.rerun()

                            with c3:
                                if st.button("🗑 Delete", key=f"del_{i}"):
                                    st.session_state.dashboard_charts.pop(i)
                                    st.rerun()

                            st.divider()

            else:
                st.info("No charts added yet")



# ============================================
# TAB 4: INSIGHTS
# ============================================
elif selected_tab == "🧠 Insights & Analysis":
    
    df = st.session_state.df

    if df is None:
        st.warning("Upload data first.")
        st.stop()

    st.subheader("🧠 Data Insights & Observations")

    # ---------------------------
    # 1. DATASET OVERVIEW
    # ---------------------------
    st.markdown("### 📊 Dataset Overview")

    rows, cols = df.shape
    st.write(f"- The dataset contains **{rows:,} rows** and **{cols} columns**.")

    numeric_cols = df.select_dtypes(include=["int64", "float64"])
    categorical_cols = df.select_dtypes(include=["object", "category"])

    st.write(f"- **{len(numeric_cols.columns)} numeric columns**")
    st.write(f"- **{len(categorical_cols.columns)} categorical columns**")

    # ---------------------------
    # 2. DATA QUALITY CHECKS
    # ---------------------------
    st.markdown("### ⚠️ Data Quality Checks")

    missing_counts = df.isnull().sum()
    high_missing = missing_counts[missing_counts > 0]

    if not high_missing.empty:
        for col, cnt in high_missing.items():
            pct = (cnt / len(df)) * 100
            st.warning(f"Column **{col}** has {pct:.1f}% missing values.")
    else:
        st.success("No missing values detected.")

    # Duplicate rows
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        st.warning(f"{dup_count} duplicate rows detected.")
    else:
        st.success("No duplicate rows detected.")

    # ---------------------------
    # 3. STATISTICAL INSIGHTS
    # ---------------------------
    st.markdown("### 📈 Statistical Highlights")

    if not numeric_cols.empty:
        for col in numeric_cols.columns:
            mean = numeric_cols[col].mean()
            std = numeric_cols[col].std()

            if std > mean:
                st.info(
                    f"Column **{col}** shows high variability "
                    f"(std {std:.2f} > mean {mean:.2f})."
                )

    # ---------------------------
    # 4. CORRELATION INSIGHTS
    # ---------------------------
    st.markdown("### 🔗 Correlation Analysis")

    if numeric_cols.shape[1] > 1:
        corr = numeric_cols.corr()

        # Show heatmap
        fig = ff.create_annotated_heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.columns.tolist(),
            colorscale="Viridis",
            showscale=True,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Text-based correlation insight
        corr_pairs = (
            corr.abs()
            .unstack()
            .reset_index()
            .rename(columns={0: "correlation"})
        )

        corr_pairs = corr_pairs[
            (corr_pairs["correlation"] < 1) &
            (corr_pairs["correlation"] >= 0.7)
        ]

        if not corr_pairs.empty:
            top = corr_pairs.sort_values("correlation", ascending=False).iloc[0]
            st.success(
                f"Strong relationship detected between **{top['level_0']}** "
                f"and **{top['level_1']}** "
                f"(correlation ≈ {top['correlation']:.2f})."
            )
        else:
            st.info("No strong correlations (≥ 0.7) detected.")
    else:
        st.info("Not enough numeric columns for correlation analysis.")

    # ---------------------------
    # 5. WHAT TO LOOK AT NEXT
    # ---------------------------
    st.markdown("### 👉 Suggested Next Steps")

    suggestions = []

    if not high_missing.empty:
        suggestions.append("Consider handling missing values before deeper analysis.")

    if numeric_cols.shape[1] > 1 and corr_pairs.empty:
        suggestions.append("Try segmenting data using filters to uncover hidden patterns.")

    if dup_count > 0:
        suggestions.append("Remove duplicate rows for cleaner insights.")

    if not suggestions:
        suggestions.append("Use global filters and dashboard charts to explore trends.")

    for s in suggestions:
        st.write(f"- {s}")


# ============================================
# TAB 5: EXPORT
# ============================================
elif selected_tab == "💾 Export":
    df = st.session_state.df

    if df is None:
        st.warning("Upload data first.")
        st.stop()

    st.subheader("💾 Export Dashboard Report")

    # Metadata
    export_title = st.text_input("Dashboard Title", value="Analytics Dashboard Report")
    author = st.text_input("Created by", value="Data Analyst")
    export_time = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")

    st.divider()

    if st.button("📄 Export Dashboard as PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", "B", 16)

        # --------------------
        # HEADER
        # --------------------
        pdf.cell(0, 10, export_title, ln=True, align="C")
        pdf.ln(2)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 8, f"Created by: {author}", ln=True)
        pdf.cell(0, 8, f"Exported on: {export_time}", ln=True)
        pdf.ln(5)

        # --------------------
        # DATASET SUMMARY
        # --------------------
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Dataset Summary", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(
            0,
            8,
            f"Rows: {len(df):,}\nColumns: {df.shape[1]}"
        )
        pdf.ln(3)

        # --------------------
        # KPI SECTION
        # --------------------
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns

        if len(numeric_cols) > 0:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Key Metrics", ln=True)
            pdf.set_font("Arial", size=10)

            for col in numeric_cols[:3]:
                pdf.multi_cell(
                    0,
                    8,
                    f"{col}: Mean = {df[col].mean():.2f}, Max = {df[col].max():.2f}"
                )

            pdf.ln(3)

        # --------------------
        # APPLIED FILTERS
        # --------------------
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Applied Filters", ln=True)
        pdf.set_font("Arial", size=10)

        filters = st.session_state.get("active_filters", {})

        if not filters:
            pdf.cell(0, 8, "No filters applied", ln=True)
        else:
            for col, val in filters.items():
                pdf.multi_cell(0, 8, f"{col}: {val}")

        pdf.ln(3)

        # --------------------
        # KPI SUMMARY (FILTERED)
        # --------------------
        pdf.ln(3)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Key Metrics", ln=True)
        pdf.cell(0, 10, "Key Metrics (Filtered Data)", ln=True)
        pdf.set_font("Arial", size=10)

        export_df = st.session_state.get("filtered_df", df)
        numeric_cols = export_df.select_dtypes(include=["int64", "float64"]).columns

        if len(numeric_cols) == 0:
            pdf.cell(0, 8, "No numeric columns available.", ln=True)
        else:
            for col in numeric_cols[:3]:
                pdf.multi_cell(
                    0,
                    8,
                    f"{col}: Mean={export_df[col].mean():.2f}, "
                    f"Max={export_df[col].max():.2f}, "
                    f"Min={export_df[col].min():.2f}, "
                    f"Total={export_df[col].sum():.2f}"


                )
        pdf.ln(3)


        st.session_state.active_filters = {}

        # --------------------
        # DASHBOARD CHARTS
        # --------------------
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Dashboard Visualizations", ln=True)
        pdf.ln(3)

        export_df = st.session_state.get("filtered_df", df)

        for chart_cfg in st.session_state.dashboard_charts:
            fig = build_chart(export_df, chart_cfg)
            if fig is None:
                continue
            
            img_path = save_fig_as_png(fig)
            pdf.image(img_path, w=170)
            pdf.ln(5)

        # --------------------
        # FINALIZE
        # --------------------
        pdf_bytes = pdf.output(dest="S").encode("latin-1")

        st.download_button(
            "⬇️ Download PDF",
            data=pdf_bytes,
            file_name="dashboard_report.pdf",
            mime="application/pdf",
        )


        st.success("Dashboard exported successfully!")

