"""Plotly interactive plots for benchmark results"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from .base import BasePlotter


class PlotlyPlotter(BasePlotter):
    """Plotly interactive plotter"""

    def generate(self) -> None:
        """Generate all plots based on config"""
        plot_types = self.config.get("plot_types", ["bar", "scatter", "radar"])

        for plot_type in plot_types:
            if plot_type == "bar":
                self._generate_bar_charts()
            elif plot_type == "scatter":
                self._generate_scatter_plots()
            elif plot_type == "radar":
                self._generate_radar_chart()
            elif plot_type == "line":
                self._generate_line_trends()

    def _generate_bar_charts(self) -> None:
        """Generate bar charts for IOPS, bandwidth, latency"""
        df = pd.DataFrame(self.results)

        if df.empty:
            return

        fig_iops = self._create_bar_chart(df, "IOPS Comparison")
        self._save_html(fig_iops, "bar_iops.html")

        fig_bw = self._create_bar_chart(df, "Bandwidth Comparison", use_bandwidth=True)
        self._save_html(fig_bw, "bar_bandwidth.html")

        fig_lat = self._create_latency_bar_chart(df)
        self._save_html(fig_lat, "bar_latency.html")

    def _create_bar_chart(
        self, df: pd.DataFrame, title: str, use_bandwidth: bool = False
    ) -> go.Figure:
        """Create grouped bar chart"""
        if use_bandwidth:
            df = df.copy()
            df["Read MB/s"] = df["read_bw"] / 1024 / 1024
            df["Write MB/s"] = df["write_bw"] / 1024 / 1024

        fig = go.Figure()

        test_types = df["test_type"].unique()

        colors = px.colors.qualitative.Set1

        for i, test_type in enumerate(test_types):
            test_data = df[df["test_type"] == test_type]

            if use_bandwidth:
                fig.add_trace(
                    go.Bar(
                        name=f"{test_type} Read",
                        x=test_data["block_size"],
                        y=test_data["Read MB/s"],
                        marker_color=colors[i % len(colors)],
                    )
                )
                fig.add_trace(
                    go.Bar(
                        name=f"{test_type} Write",
                        x=test_data["block_size"],
                        y=test_data["Write MB/s"],
                        marker_color=colors[(i + 1) % len(colors)],
                    )
                )
            else:
                fig.add_trace(
                    go.Bar(
                        name=f"{test_type} Read",
                        x=test_data["block_size"],
                        y=test_data["read_iops"],
                        marker_color=colors[i % len(colors)],
                    )
                )
                fig.add_trace(
                    go.Bar(
                        name=f"{test_type} Write",
                        x=test_data["block_size"],
                        y=test_data["write_iops"],
                        marker_color=colors[(i + 1) % len(colors)],
                    )
                )

        fig.update_layout(
            title=title,
            xaxis_title="Block Size",
            yaxis_title="IOPS" if not use_bandwidth else "MB/s",
            barmode="group",
            hovermode="x unified",
        )

        return fig

    def _create_latency_bar_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create latency comparison bar chart"""
        fig = go.Figure()

        test_types = df["test_type"].unique()
        colors = px.colors.qualitative.Set1

        for i, test_type in enumerate(test_types):
            test_data = df[df["test_type"] == test_type]

            fig.add_trace(
                go.Bar(
                    name=f"{test_type} Read",
                    x=test_data["block_size"],
                    y=test_data["read_latency_us"],
                    marker_color=colors[i % len(colors)],
                )
            )
            fig.add_trace(
                go.Bar(
                    name=f"{test_type} Write",
                    x=test_data["block_size"],
                    y=test_data["write_latency_us"],
                    marker_color=colors[(i + 1) % len(colors)],
                )
            )

        fig.update_layout(
            title="Latency Comparison",
            xaxis_title="Block Size",
            yaxis_title="Latency (µs)",
            barmode="group",
            hovermode="x unified",
        )

        return fig

    def _generate_scatter_plots(self) -> None:
        """Generate scatter plots for correlation analysis"""
        df = pd.DataFrame(self.results)

        if df.empty:
            return

        fig_iops = self._create_scatter_chart(df, "IOPS vs Latency", "read_iops", "read_latency_us")
        self._save_html(fig_iops, "scatter_iops_latency.html")

        fig_bw = self._create_scatter_chart(
            df, "Bandwidth vs Latency", "read_bw", "read_latency_us", use_bandwidth=True
        )
        self._save_html(fig_bw, "scatter_bw_latency.html")

    def _create_scatter_chart(
        self,
        df: pd.DataFrame,
        title: str,
        x_col: str,
        y_col: str,
        use_bandwidth: bool = False,
    ) -> go.Figure:
        """Create scatter plot"""
        if use_bandwidth:
            df = df.copy()
            df["Read MB/s"] = df["read_bw"] / 1024 / 1024
            x_col = "Read MB/s"

        fig = go.Figure()

        for test_type in df["test_type"].unique():
            test_data = df[df["test_type"] == test_type]
            fig.add_trace(
                go.Scatter(
                    x=test_data[x_col],
                    y=test_data[y_col],
                    mode="markers",
                    name=test_type,
                    text=test_data["block_size"],
                    marker=dict(size=10, opacity=0.7),
                )
            )

        x_label = "IOPS" if not use_bandwidth else "Bandwidth (MB/s)"

        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title="Latency (µs)",
            hovermode="closest",
        )

        return fig

    def _generate_radar_chart(self) -> None:
        """Generate radar chart for performance profile"""
        df = pd.DataFrame(self.results)

        if df.empty:
            return

        fig = self._create_radar_chart(df)
        self._save_html(fig, "radar_performance.html")

    def _create_radar_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create radar chart"""
        test_types_to_include = ["randread", "randwrite", "read", "write", "randrw"]
        available_test_types = [t for t in test_types_to_include if t in df["test_type"].values]

        if not available_test_types:
            return go.Figure()

        block_sizes = df["block_size"].unique()

        fig = go.Figure()

        for i, block_size in enumerate(block_sizes):
            block_data = df[df["block_size"] == block_size]

            values = []
            for test_type in available_test_types:
                test_data = block_data[block_data["test_type"] == test_type]
                if not test_data.empty:
                    avg_iops = test_data["read_iops"].mean()
                else:
                    avg_iops = 0
                values.append(avg_iops)

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=available_test_types,
                    fill="toself",
                    name=f"{block_size}",
                )
            )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max(values) * 1.2] if values else [0, 1])
            ),
            showlegend=True,
            title="Performance Profile (IOPS)",
        )

        return fig

    def _generate_line_trends(self) -> None:
        """Generate line chart for performance trends"""
        pass

    def _save_html(self, fig: go.Figure, filename: str) -> None:
        """Save figure as HTML file"""
        filepath = self.output_dir / filename
        fig.write_html(str(filepath))
        print(f"Plot saved to {filepath}")

    def save(self, filename: str) -> None:
        """Save plot (placeholder - individual plots saved during generate)"""
        pass
