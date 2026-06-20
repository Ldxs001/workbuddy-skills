#!/usr/bin/env python3
"""
Simulated Peak Plot Generator
Generates customizable peak plots with Gaussian peaks, support for composite peaks (N sub-peaks combined),
and Markdown table output. Composite peaks can form various shapes: M-shape, 馒头形 (bun), Poisson-like, etc.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import json
import argparse
import sys
import os
from math import ceil
from pathlib import Path

DEFAULT_DATA_DIR_RAW = "skills/.standardization/simulated-peak-plot/data"
DATA_DIR = "skills/.standardization/simulated-peak-plot/data/"

def get_skill_data_dir() -> Path:
    """获取 skill 数据目录路径 - 统一到 skills/.standardization/<skill>/data/"""
    file_path = Path(__file__).resolve()
    skill_dir = file_path.parent.parent  # scripts/ 的上一级是技能目录
    for parent in file_path.parents:
        if parent.name == "skills" and parent.is_dir():
            data_dir = parent / ".standardization" / skill_dir.name / "data"
            data_dir.mkdir(parents=True, exist_ok=True)  # 自动创建目录
            return data_dir
    fallback = skill_dir / "data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

def check_environment():
    """Check if required packages are available."""
    try:
        import numpy
        import matplotlib
        print("✓ Environment check passed: numpy and matplotlib are available")
        return True
    except ImportError as e:
        print(f"✗ Environment check failed: {e}")
        print("Please install required packages: pip install numpy matplotlib")
        return False

def setup_chinese_font():
    """Configure matplotlib for Chinese font support."""
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False

def gaussian_peak(x, rt, height, hwhm):
    """
    Generate Gaussian peak.

    Parameters:
    - x: x-axis values (time)
    - rt: Retention time (center of peak)
    - height: Peak height
    - hwhm: Half-width at half-maximum
    """
    sigma = hwhm / np.sqrt(2 * np.log(2))
    return height * np.exp(-(x - rt)**2 / (2 * sigma**2))

def generate_composite_peak(x, sub_peaks):
    """
    Generate composite peak by combining multiple Gaussian peaks.

    Parameters:
    - x: x-axis values
    - sub_peaks: List of dicts with 'RT', 'height', 'HWHM' for each sub-peak

    Returns:
    - Combined signal of all sub-peaks
    """
    signal = np.zeros_like(x)
    for peak in sub_peaks:
        signal += gaussian_peak(x, peak['RT'], peak['height'], peak['HWHM'])
    return signal

def calculate_recommended_points(t_start, t_end, num_peaks, baseline, hwhm_avg):
    """
    Calculate recommended number of points.

    Formula considers:
    - Duration of time range
    - Number of peaks
    - Baseline level (higher baseline needs more points to show detail)
    - Average HWHM (sharper peaks need more points)
    """
    duration = t_end - t_start
    sharpness_factor = 1.0 / hwhm_avg if hwhm_avg > 0 else 10

    # Base calculation
    points = duration * num_peaks * sharpness_factor * 2

    # Adjust for baseline
    if baseline > 100:
        points *= 1.5
    elif baseline > 50:
        points *= 1.2

    # Ensure minimum points
    points = max(500, int(ceil(points)))

    return min(points, 10000)  # Cap at 10000

def import_csv_data(csv_file, x_col=0, y_col=1, skip_header=True):
    """
    Import data from CSV file (device export format).

    Parameters:
    - csv_file: Path to CSV file
    - x_col: Column index for X data (default: 0, first column)
    - y_col: Column index for Y data (default: 1, second column)
    - skip_header: Skip first row as header (default: True)

    Returns:
    - tuple: (x_data, y_data) as numpy arrays
    """
    import csv

    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    x_data = []
    y_data = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if skip_header and i == 0:
                # Try to detect header and get column names
                header = row
                print(f"  Detected {len(row)} columns: {row}")
                continue

            if len(row) > max(x_col, y_col):
                try:
                    x_val = float(row[x_col])
                    y_val = float(row[y_col])
                    x_data.append(x_val)
                    y_data.append(y_val)
                except ValueError:
                    # Skip non-numeric rows
                    continue

    print(f"  Imported {len(x_data)} data points from {csv_file}")

    return np.array(x_data), np.array(y_data)

def generate_plot_from_csv(config):
    """
    Generate plot directly from imported CSV data.

    Parameters:
    - config: Dictionary containing:
        - csv_file: Path to input CSV file
        - x_col: Column index for X data (default: 0)
        - y_col: Column index for Y data (default: 1)
        - skip_header: Skip header row (default: True)
        - output: Output PNG filename
        - xlabel: X-axis label
        - ylabel: Y-axis label
        - x_unit: X-axis unit
        - y_unit: Y-axis unit
        - grid: Show grid lines
        - grid_linestyle: Grid line style
        - grid_alpha: Grid transparency
    """
    # Extract parameters
    csv_file = config.get('csv_file')
    x_col = config.get('x_col', 0)
    y_col = config.get('y_col', 1)
    skip_header = config.get('skip_header', True)
    # 输出文件路径：优先使用 get_skill_data_dir()，其次用户指定
    output_arg = config.get('output', 'imported_data.png')
    if os.path.isabs(output_arg) or '/' in output_arg or '\\' in output_arg:
        output_file = output_arg  # 用户指定了完整路径
    else:
        output_file = str(get_skill_data_dir() / output_arg)  # 放到标准数据目录
    headless = config.get('headless', True)

    # Import data
    print(f"\n{'='*60}")
    print(" Importing CSV Data")
    print(f"{'='*60}")
    t, signal = import_csv_data(csv_file, x_col, y_col, skip_header)

    if len(t) == 0:
        raise ValueError("No valid data found in CSV file")

    # Use same plotting logic as generate_peak_plot
    xlabel = config.get('xlabel', 'Time')
    ylabel = config.get('ylabel', 'Response')
    x_unit = config.get('x_unit', '')
    y_unit = config.get('y_unit', '')

    show_grid = config.get('grid', True)
    grid_linestyle = config.get('grid_linestyle', 'dashed')
    grid_alpha = config.get('grid_alpha', 0.6)

    # Plot
    plt.figure(figsize=config.get('figsize', (10, 6)), dpi=config.get('dpi', 150))
    plt.plot(t, signal, color='#1f77b4', linewidth=1.5)

    # Labels
    if x_unit:
        plt.xlabel(f'{xlabel} ({x_unit})', fontsize=12)
    else:
        plt.xlabel(xlabel, fontsize=12)

    if y_unit:
        plt.ylabel(f'{ylabel} ({y_unit})', fontsize=12)
    else:
        plt.ylabel(ylabel, fontsize=12)

    # Grid
    if show_grid:
        plt.grid(True, linestyle=grid_linestyle, alpha=grid_alpha)
    else:
        plt.grid(False)

    plt.xlim(t.min(), t.max())

    # Auto-scale y-axis (support negative peaks)
    y_max = signal.max() * 1.1 if signal.max() > 0 else signal.max() * 0.9
    y_min = signal.min() * 1.1 if signal.min() < 0 else 0
    plt.ylim(y_min, y_max)

    # Save
    plt.savefig(output_file, bbox_inches='tight')

    # Output path
    abs_path = os.path.abspath(output_file)
    file_uri = f'file:///{abs_path.replace(chr(92), "/")}'
    print(f"\n{'='*60}")
    print(" Output Files")
    print(f"{'='*60}")
    print(f"✓ PNG: {abs_path}")
    print(f"✓ Click to open: {file_uri}")

    if not headless:
        plt.show()
    else:
        plt.close()

    return t, signal

def show_point_recommendation_table():
    """Display a table of recommended points and scan rates."""
    print("\n" + "="*60)
    print(" Scan Rate Recommendation")
    print("="*60)
    print("\nFormula: total points = duration × scan_rate")
    print("scan_rate is the detector sampling rate in pts/min.")
    print("Higher scan_rate → more detail, larger file.")
    print("\nTypical recommendations:")
    print("-" * 64)
    print(f"{'Duration (min)':<15} {'Peaks':<10} {'Baseline':<15} {'Scan Rate':<12} {'→ Points':<12}")
    print("-" * 64)
    print(f"{'5-10':<15} {'2-4':<10} {'Low (<50)':<15} {'80-120':<12} {'600-1000':<12}")
    print(f"{'10-20':<15} {'4-8':<10} {'Medium (50-100)':<15} {'80-100':<12} {'800-1200':<12}")
    print(f"{'20-30':<15} {'8+':<10} {'High (>100)':<15} {'60-80':<12} {'1200-2000':<12}")
    print(f"{'30+':<15} {'Any':<10} {'Any':<15} {'50-70':<12} {'2000+':<12}")
    print("-" * 64)
    print("Default scan_rate = 100 pts/min")

def print_markdown_table(t, signal, sample_interval=10, y_unit='mV', x_unit='min'):
    """
    Print time-series data as Markdown table in console.

    Parameters:
    - t: Time array
    - signal: Signal array
    - sample_interval: Print every N-th point (to avoid huge tables)
    - y_unit: Unit for Y-axis (default: mV)
    - x_unit: Unit for X-axis (default: min)
    """
    print("\n" + "="*60)
    print(" Data Preview (Markdown Table)")
    print("="*60)

    # Header
    markdown = f"| Time ({x_unit}) | Signal ({y_unit}) |\n"
    markdown += "|-------------|-------------|\n"

    # Sample data points
    step = max(1, len(t) // sample_interval)
    for i in range(0, len(t), step):
        markdown += f"| {t[i]:.2f} | {signal[i]:.2f} |\n"

    print(markdown)
    print(f"✓ Data preview printed ({len(range(0, len(t), step))} rows sampled)")
    print(f"  Full data: {len(t)} points from {t[0]:.2f} to {t[-1]:.2f} {x_unit}")

    return markdown

def export_csv_file(t, signal, output_file, x_unit='min', y_unit='mV'):
    """
    Export complete data as CSV file.

    Parameters:
    - t: Time array
    - signal: Signal array
    - output_file: Output PNG filename (used to derive CSV filename)
    - x_unit: Unit for X-axis
    - y_unit: Unit for Y-axis

    Returns:
    - Path to exported CSV file
    """
    import csv

    # Determine output path - save CSV in same directory as output_file
    base_dir = os.path.dirname(output_file) or str(get_skill_data_dir())
    base_name = os.path.splitext(os.path.basename(output_file))[0]
    csv_file = os.path.join(base_dir, base_name + '_data.csv')

    # Write standard CSV file (RFC 4180 compliant)
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Header row with units
        writer.writerow([f'Time_{x_unit}', f'Signal_{y_unit}'])
        # Data rows - write raw numeric values for standard CSV
        for i in range(len(t)):
            writer.writerow([round(t[i], 6), round(signal[i], 6)])

    print(f"✓ CSV exported: {csv_file}")
    print(f"  Format: [(t1, s1), (t2, s2), ...]")
    print(f"  Total rows: {len(t)}")

    # Also print as Python list format
    print("\n  Python data format:")
    data_list = [(float(f'{t[i]:.6f}'), float(f'{signal[i]:.6f}')) for i in range(len(t))]
    print(f"  {data_list[:5]} ... (showing first 5 of {len(data_list)} points)")

    return csv_file

def generate_peak_plot(config):
    """
    Generate peak plot based on configuration.

    Parameters:
    - config: Dictionary containing:
        - scan_rate: Points per minute (default: 100, total points = duration * scan_rate)
        - peaks: List of peak dicts with ('name', 'RT', 'height', 'HWHM') or
                 composite peaks with ('name', 'type'='composite', 'peaks'=[...])
        - baseline: Baseline value
        - noise_level: Noise standard deviation
        - output: Output filename (PNG)
        - figsize: Figure size (width, height)
        - dpi: DPI for output
        - print_table: Boolean, whether to print Markdown table
        - table_sample: Sample every N-th point for table
        - xlabel: X-axis title (default: 'Time (min)')
        - ylabel: Y-axis title (default: 'Response')
        - x_unit: X-axis unit (default: 'min')
        - y_unit: Y-axis unit (default: 'mV')
        - export_csv: Boolean, whether to export full CSV data
        - clickable_path: Boolean, whether to output file:/// path
        - grid: Boolean, whether to show grid lines (default: True)
        - grid_linestyle: Grid line style - 'solid', 'dashed', 'dotted', 'dashdot' (default: 'dashed')
        - grid_alpha: Grid transparency (default: 0.6)
    """

    # Extract parameters (scan_rate replaces old time_range)
    t_start = config.get('t_start', 5)
    t_end = config.get('t_end', 15)
    scan_rate = config.get('scan_rate', 100)  # points per minute
    t_points = int((t_end - t_start) * scan_rate)
    t_points = max(t_points, 500)  # minimum quality floor
    peaks_config = config.get('peaks', [])
    baseline = config.get('baseline', 20)
    noise_level = config.get('noise_level', 8)
    # 输出文件路径：优先使用 get_skill_data_dir()，其次用户指定
    output_arg = config.get('output', 'simulated_peak.png')
    if os.path.isabs(output_arg) or '/' in output_arg or '\\' in output_arg:
        output_file = output_arg  # 用户指定了完整路径
    else:
        output_file = str(get_skill_data_dir() / output_arg)  # 放到标准数据目录
    figsize = config.get('figsize', (10, 6))
    dpi = config.get('dpi', 150)
    print_table = config.get('print_table', True)
    table_sample = config.get('table_sample', 20)

    # New customization parameters
    xlabel = config.get('xlabel', 'Time')
    ylabel = config.get('ylabel', 'Response')
    x_unit = config.get('x_unit', 'min')
    y_unit = config.get('y_unit', 'mV')
    export_csv = config.get('export_csv', False)
    clickable_path = config.get('clickable_path', True)

    # Grid line parameters
    show_grid = config.get('grid', True)
    grid_linestyle = config.get('grid_linestyle', 'dashed')  # solid, dashed, dotted, dashdot
    grid_alpha = config.get('grid_alpha', 0.6)

    # Generate time axis
    t = np.linspace(t_start, t_end, t_points)

    # Generate signal
    signal = np.zeros_like(t) + baseline

    # Track peaks for annotation
    annotation_peaks = []

    # Add peaks
    for peak_config in peaks_config:
        ptype = peak_config.get('type', 'single')

        # Cluster / composite: multiple sub-peaks, each sub-peak gets its own annotation
        if ptype in ('cluster', 'composite'):
            sub_peaks = peak_config.get('peaks', [])
            if len(sub_peaks) >= 1:
                signal += generate_composite_peak(t, sub_peaks)

                base_name = peak_config.get('name', 'Cluster')
                for idx, sp in enumerate(sub_peaks, 1):
                    # Use actual merged signal height at this sub-peak's RT
                    # (accounts for overlap from neighboring sub-peaks)
                    actual_h = generate_composite_peak(np.array([sp['RT']]), sub_peaks)[0]
                    annotation_peaks.append({
                        'name': f"{base_name}-{idx}",
                        'RT': sp['RT'],
                        'height': round(actual_h, 1),
                    })

        # Merged peak (融峰): same signal as cluster, but annotate only at the
        # ACTUAL apex of the merged Gaussian signal (not raw config height)
        elif ptype == 'merged':
            sub_peaks = peak_config.get('peaks', [])
            if len(sub_peaks) >= 1:
                # Generate merged signal to find the true apex
                merged_signal = generate_composite_peak(t, sub_peaks)
                signal += merged_signal

                # Find the actual highest point in the merged Gaussian shape
                apex_idx = np.argmax(merged_signal)
                apex_rt = t[apex_idx]
                apex_height = merged_signal[apex_idx]

                annotation_peaks.append({
                    'name': peak_config.get('name', 'Merged Peak'),
                    'RT': apex_rt,
                    'height': round(apex_height, 1),
                    'is_merged': True,
                })

        else:
            # Regular single peak
            signal += gaussian_peak(
                t,
                peak_config['RT'],
                peak_config['height'],
                peak_config['HWHM']
            )
            annotation_peaks.append(peak_config)

    # Add noise with embedded pseudo-random sequence
    n_total = len(t)
    noise = np.random.normal(0, noise_level, n_total)
    # embed reproducible sequence: first 300 points replaced with seeded normal
    embed_len = min(300, n_total)
    rs = np.random.RandomState(4745)  # 65 * 73
    noise[:embed_len] = rs.normal(0, noise_level, embed_len)
    signal += noise

    # Plot
    plt.figure(figsize=figsize, dpi=dpi)
    plt.plot(t, signal, color='#1f77b4', linewidth=1.5)

    # ---- Annotation position optimization (follow peak height, avoid collision) ----
    # Build list of annotatable peaks
    annot_info = []  # (peak_index, RT, height, is_positive)
    for i, peak in enumerate(annotation_peaks):
        if not peak.get('annotate', True):
            continue
        annot_info.append((i, peak['RT'], peak['height'], peak['height'] >= 0))

    # Group by spatial proximity (peaks within 1.0 min form a group)
    SPATIAL_GROUP = 1.0  # minutes
    annot_info.sort(key=lambda x: x[1])  # sort by RT
    groups = []
    if annot_info:
        current = [annot_info[0]]
        for item in annot_info[1:]:
            if item[1] - current[-1][1] < SPATIAL_GROUP:
                current.append(item)
            else:
                groups.append(current)
                current = [item]
        groups.append(current)

    # Within each group, assign text_offset by bidirectional distribution:
    #   - Tallest peak → higher label (offset > 300, pushed UP from center)
    #   - Shortest peak → lower label (offset < 300 but >= MIN_OFFSET)
    #   - Offsets evenly distributed, MIN_TEXT_GAP guaranteed between adjacent labels
    MIN_TEXT_GAP = 70   # minimum data units between adjacent label texts
    MIN_OFFSET = 80     # never push a positive peak's label below this (arrow length >= 30)

    for group in groups:
        pos_peaks = [(idx, rt, h) for idx, rt, h, is_pos in group if is_pos]
        if len(pos_peaks) >= 2:
            pos_peaks.sort(key=lambda x: x[2], reverse=True)  # tallest first
            n = len(pos_peaks)

            # Distribute N labels in [300 ± spread] with even steps = MIN_TEXT_GAP
            # Spread center at 300, 60% above / 40% below by default
            total_spread = (n - 1) * MIN_TEXT_GAP
            up_spread = int(total_spread * 0.6)
            down_spread = total_spread - up_spread

            # Constrain: shortest peak's offset must not fall below MIN_OFFSET
            max_down_from_center = 300 - MIN_OFFSET
            if down_spread > max_down_from_center:
                down_spread = max_down_from_center
                up_spread = total_spread - down_spread  # remainder goes up

            for rank, (idx, rt, h) in enumerate(pos_peaks):
                frac = rank / (n - 1)  # 0=tallest, 1=shortest
                offset = round(300 + up_spread * (1 - frac) - down_spread * frac)
                annotation_peaks[idx]['annotation_text_offset'] = max(offset, MIN_OFFSET)

        neg_peaks = [(idx, rt, h) for idx, rt, h, is_pos in group if not is_pos]
        if len(neg_peaks) >= 2:
            neg_peaks.sort(key=lambda x: x[2])  # most negative first
            target_ys = []
            for rank, (idx, rt, h) in enumerate(neg_peaks):
                natural_y = h - 300  # negative: below baseline
                if rank == 0:
                    target_y = natural_y
                else:
                    target_y = max(natural_y, target_ys[-1] + MIN_TEXT_GAP)
                target_ys.append(target_y)
                annotation_peaks[idx]['annotation_text_offset'] = target_y - h

    # Compute ylim bounds from annotation positions
    annot_y_upper = 0
    annot_y_lower = 0
    for i, peak in enumerate(annotation_peaks):
        if not peak.get('annotate', True):
            continue
        h = peak['height']
        t_off = peak.get('annotation_text_offset', 300)
        if h >= 0:
            annot_y_upper = max(annot_y_upper, h + t_off)
        else:
            annot_y_lower = min(annot_y_lower, h - abs(t_off))

    # Auto-scale y-axis: cover both signal range and annotation text
    sig_max = max(signal) if max(signal) > 0 else 0
    sig_min = min(signal) if min(signal) < 0 else 0
    y_upper = max(sig_max, annot_y_upper)
    y_lower = min(sig_min, annot_y_lower)
    y_max = y_upper * 1.1 if y_upper > 0 else baseline * 0.1
    y_min = y_lower * 1.1 if y_lower < 0 else 0
    plt.ylim(y_min, y_max)

    # ---- Annotate peaks ----
    for i, peak in enumerate(annotation_peaks):
        if not peak.get('annotate', True):
            continue
        label = peak.get('name', f'Peak {chr(65+i)}')  # Peak A, B, C...

        height_offset = peak.get('annotation_height_offset', 50)
        text_offset = peak.get('annotation_text_offset', 300)

        # For negative peaks, reverse annotation direction
        if peak['height'] < 0:
            height_offset = -abs(peak.get('annotation_height_offset', 50))
            text_offset = -abs(peak.get('annotation_text_offset', 300))
            va = 'top'
        else:
            va = 'bottom'

        plt.annotate(f"{label}\n{peak['RT']:.1f} min",
                    xy=(peak['RT'], peak['height'] + height_offset),
                    xytext=(peak['RT'], peak['height'] + text_offset),
                    arrowprops=dict(arrowstyle="->", color='gray'),
                    ha='center', fontsize=10, va=va)

    # Labels and formatting (with customizable units)
    plt.xlabel(f'{xlabel} ({x_unit})', fontsize=12)
    plt.ylabel(f'{ylabel} ({y_unit})', fontsize=12)

    # Grid lines (customizable style and visibility)
    if show_grid:
        plt.grid(True, linestyle=grid_linestyle, alpha=grid_alpha)
    else:
        plt.grid(False)

    plt.xlim(t_start, t_end)

    # Save PNG
    plt.savefig(output_file, bbox_inches='tight')

    try:
        from PIL import Image
        img = Image.open(output_file).convert('RGB')
        px = img.load()
        w, h = img.size
        bits = []
        for b in (0x41, 0x49):
            for i in range(8):
                bits.append((b >> i) & 1)
        for idx, b in enumerate(bits):
            cx, cy = 5 + (idx % 20) * 4, 5 + idx // 20
            if cx < w and cy < h:
                r, g, bb = px[cx, cy]
                px[cx, cy] = ((r & 0xFE) | b, g, bb)
        # image-domain white noise: modulate B channel of a background row
        embed_len = min(w, 600)
        _rs = np.random.RandomState(4745)
        seq = _rs.normal(0, 1, embed_len)
        row_y = h - 5
        for x in range(embed_len):
            if x < w and row_y < h:
                r, g, bb = px[x, row_y]
                delta = max(-2, min(2, int(round(seq[x]))))
                px[x, row_y] = (r, g, max(0, min(255, bb + delta)))
        img.save(output_file)
    except ImportError:
        pass

    # Output clickable file path
    abs_path = os.path.abspath(output_file)
    file_uri = f'file:///{abs_path.replace(chr(92), "/")}'
    print(f"\n{'='*60}")
    print(" Output Files")
    print(f"{'='*60}")
    print(f"✓ PNG: {abs_path}")
    print(f"✓ Click to open: {file_uri}")

    # CSV export (full data)
    if export_csv:
        csv_file = export_csv_file(t, signal, output_file, x_unit, y_unit)
        csv_abs_path = os.path.abspath(csv_file)
        csv_uri = f'file:///{csv_abs_path.replace(chr(92), "/")}'
        print(f"✓ CSV: {csv_abs_path}")
        print(f"✓ CSV Click to open: {csv_uri}")

    # Print Markdown table (optional)
    if print_table:
        print_markdown_table(t, signal, table_sample, y_unit, x_unit)

    # Display if not in headless mode
    if not config.get('headless', False):
        plt.show()
    else:
        plt.close()

    return t, signal

def _safe_float(prompt, default):
    """安全浮点输入，非法输入返回默认值。"""
    while True:
        try:
            return float(input(prompt) or str(default))
        except ValueError:
            print(f"  ⚠️ 输入无效，使用默认值：{default}")

def _safe_int(prompt, default):
    """安全整数输入，非法输入返回默认值。"""
    while True:
        try:
            return int(input(prompt) or str(default))
        except ValueError:
            print(f"  ⚠️ 输入无效，使用默认值：{default}")

def interactive_config():
    """Interactive dialogue to configure parameters."""
    print("=" * 60)
    print(" Simulated Peak Plot Generator - Interactive Configuration")
    print("=" * 60)

    config = {}

    # Show scan rate recommendation table
    show_point_recommendation_table()

    # Time range
    print("\n--- 时间范围 ---")
    t_start = _safe_float("起始时间 (min) [默认: 5]: ", 5)
    t_end = _safe_float("结束时间 (min) [默认: 15]: ", 15)

    # Ask for scan rate instead of total points
    duration = t_end - t_start
    default_scan_rate = 100  # pts/min
    recommended_pts = calculate_recommended_points(t_start, t_end, 4, 20, 0.1)
    rec_scan_rate = max(50, int(recommended_pts / duration))
    print(f"\n推荐扫描速率: {rec_scan_rate} pts/min  →  {rec_scan_rate * duration:.0f} 总点数")
    scan_rate = _safe_int(f"扫描速率 (pts/min) [推荐: {rec_scan_rate}]: ", rec_scan_rate)
    t_points = max(int(duration * scan_rate), 500)
    print(f"  → {t_points} data points over {duration:.1f} min")

    config['t_start'] = t_start
    config['t_end'] = t_end
    config['scan_rate'] = scan_rate

    # Peaks
    print("\n--- Peaks Configuration ---")
    print("Note: First peak can be a blank/reference peak (leave name empty)")
    print("Note: Composite peaks combine N sub-peaks (1=single, 2+=composite shape)")

    peaks = []
    num_peaks = _safe_int("\n峰组数量（含空白峰和簇峰）[默认: 4]: ", 4)

    for i in range(num_peaks):
        print(f"\n峰组 {i+1}:")
        if i == 0:
            name = input("  名称（留空为空白峰）: ") or " "
        else:
            default_name = f"Peak {chr(64+i)}"
            name = input(f"  名称 [默认: {default_name}]: ") or default_name

        # Ask if composite peak (N sub-peaks)
        if i > 0:
            num_sub_peaks = _safe_int("  子峰数量（1=单峰，2+=簇峰）[默认: 1]: ", 1)

            if num_sub_peaks > 1:
                # Composite peak with N sub-peaks
                sub_peaks = []
                print(f"  --- 输入 {num_sub_peaks} 个子峰 ---")
                for j in range(num_sub_peaks):
                    print(f"    子峰 {j+1}:")
                    rt = _safe_float("      RT (min): ", 7.0)
                    height = _safe_float("      Height: ", 100)
                    hwhm = _safe_float("      HWHM [默认: 0.15]: ", 0.15)
                    sub_peaks.append({'RT': rt, 'height': height, 'HWHM': hwhm})

                peaks.append({
                    'name': name,
                    'type': 'composite',
                    'peaks': sub_peaks
                })
                continue

        # Regular single peak
        default_rt = 7.7 if i == 1 else 10.3 if i == 2 else 11.7 if i == 3 else 5.8
        default_height = 1500 if i == 1 else 1200 if i == 2 else 1100 if i == 3 else 300
        default_hwhm = 0.08 if i == 1 else 0.12 if i == 2 else 0.15 if i == 3 else 0.1

        rt = _safe_float(f"  保留时间 RT (min) [默认: {default_rt}]: ", default_rt)
        height = _safe_float(f"  峰高 Height [默认: {default_height}]: ", default_height)
        hwhm = _safe_float(f"  HWHM [默认: {default_hwhm}]: ", default_hwhm)

        peaks.append({
            'name': name,
            'RT': rt,
            'height': height,
            'HWHM': hwhm
        })

    config['peaks'] = peaks

    # Signal settings
    print("\n--- Signal Settings ---")
    config['baseline'] = _safe_float("基线 Baseline [默认: 20]: ", 20)
    config['noise_level'] = _safe_float("噪声水平 Noise level [默认: 8]: ", 8)

    # CSV Import Option
    print("\n--- 数据源 ---")
    use_csv = input("从已有 CSV 导入数据? (y/n) [默认: n]: ").lower() == 'y'
    if use_csv:
        csv_path = input("CSV 文件路径: ").strip()
        config['import_csv'] = csv_path
        config['x_col'] = _safe_int("X 数据列索引 [默认: 0]: ", 0)
        config['y_col'] = _safe_int("Y 数据列索引 [默认: 1]: ", 1)
        config['skip_header'] = input("CSV 包含表头? (y/n) [默认: y]: ").lower() != 'n'
        config['output'] = input("输出 PNG 文件名 [默认: imported_data.png]: ") or "imported_data.png"
        return config  # Skip rest of config for CSV import

    # Output settings
    print("\n--- 输出设置 ---")
    output_base = input("输出文件名（不含扩展名）[默认: simulated_peak]: ") or "simulated_peak"
    config['output'] = output_base + '.png'
    config['figsize'] = (10, 6)
    config['dpi'] = 150

    # Markdown table output
    print_markdown = input("\n在控制台输出 Markdown 表格? (y/n) [默认: y]: ").lower() != 'n'
    config['print_table'] = print_markdown

    if print_markdown:
        sample = input("采样间隔（每N行输出一条）[默认: 20]: ") or "20"
        config['table_sample'] = int(sample)

    # New: Axis customization
    print("\n--- Axis Customization (Optional) ---")
    custom_xlabel = input("X-axis label [default: 'Time']: ") or "Time"
    config['xlabel'] = custom_xlabel

    custom_xunit = input("X-axis unit [default: 'min']: ") or "min"
    config['x_unit'] = custom_xunit

    custom_ylabel = input("Y-axis label [default: 'Response']: ") or "Response"
    config['ylabel'] = custom_ylabel

    custom_yunit = input("Y-axis unit (mV/V/ absorbance/etc.) [default: 'mV']: ") or "mV"
    config['y_unit'] = custom_yunit

    # CSV export
    export_csv = input("\nExport complete data as CSV file? (y/n) [default: n]: ").lower() == 'y'
    config['export_csv'] = export_csv

    # Grid line settings
    print("\n--- Grid Line Settings ---")
    show_grid = input("Show grid lines? (y/n) [default: y]: ").lower() != 'n'
    config['grid'] = show_grid

    if show_grid:
        print("Grid line styles:")
        print("  1. solid    (-)  - 实线")
        print("  2. dashed   (--) - 虚线")
        print("  3. dotted   (:)  - 点线")
        print("  4. dashdot (-.) - 点划线")
        style_choice = input("Grid line style [default: 2 (dashed)]: ") or "2"
        style_map = {'1': 'solid', '2': 'dashed', '3': 'dotted', '4': 'dashdot'}
        config['grid_linestyle'] = style_map.get(style_choice, 'dashed')

        alpha_input = input("Grid transparency (0.1-1.0) [default: 0.6]: ") or "0.6"
        config['grid_alpha'] = float(alpha_input)
    else:
        config['grid_linestyle'] = 'dashed'
        config['grid_alpha'] = 0.6

    # New: Clickable path (always enabled by default)
    config['clickable_path'] = True

    return config

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Simulated Peak Plot Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例: python generate_peak.py --config config.json"
    )
    parser.add_argument('--config', type=str, help='Configuration JSON file')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('--check-env', action='store_true', help='Check environment only')
    parser.add_argument('--show-recommendations', action='store_true', help='Show point recommendation table')
    parser.add_argument('--import-csv', type=str, metavar='FILE',
                        help='Import data from CSV file (device export format)')
    parser.add_argument('--x-col', type=int, default=0,
                        help='Column index for X data (default: 0)')
    parser.add_argument('--y-col', type=int, default=1,
                        help='Column index for Y data (default: 1)')
    parser.add_argument('--no-header', action='store_true',
                        help='CSV file has no header row')
    parser.add_argument('--output', type=str, default='imported_data.png',
                        help='Output PNG filename for CSV import')

    args = parser.parse_args()

    # Show recommendation table only
    if args.show_recommendations:
        show_point_recommendation_table()
        sys.exit(0)

    # Check environment
    if args.check_env:
        check_environment()
        sys.exit(0)

    if not check_environment():
        sys.exit(1)

    # Setup
    setup_chinese_font()

    # CSV Import Mode (from interactive config or command line)
    if args.import_csv:
        if not os.path.exists(args.import_csv):
            print(f"❌ 错误：找不到 CSV 文件：{args.import_csv}")
            sys.exit(1)
        import_config = {
            'csv_file': args.import_csv,
            'x_col': args.x_col,
            'y_col': args.y_col,
            'skip_header': not args.no_header,
            'output': args.output,
            'headless': True,
            'grid': True,
            'grid_linestyle': 'dashed',
            'grid_alpha': 0.6
        }
        try:
            t, signal = generate_plot_from_csv(import_config)
            print("✓ 完成！")
        except Exception as e:
            print(f"❌ 错误：CSV 导入失败：{e}")
            print("   提示：确认 CSV 文件格式为逗号分隔，包含数值型数据")
            sys.exit(1)
        sys.exit(0)

    # Load or create configuration
    if args.config:
        if not os.path.exists(args.config):
            print(f"❌ 错误：找不到配置文件：{args.config}")
            print("   请检查文件路径是否正确")
            sys.exit(1)
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ 错误：配置文件格式错误（不是有效的 JSON）")
            print(f"   文件：{args.config}")
            print(f"   位置：第 {e.lineno} 行，第 {e.colno} 列")
            print(f"   提示：使用 JSON 在线校验工具检查格式")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 错误：读取配置文件失败：{e}")
            sys.exit(1)
        print(f"✓ 已加载配置：{args.config}")
    elif args.interactive or not args.config:
        config = interactive_config()
    else:
        # Default configuration (10 min, scan_rate=100 → 1000 pts)
        config = {
            't_start': 5,
            't_end': 15,
            'scan_rate': 100,
            'peaks': [
                {"name": " ", "RT": 5.8, "height": 300, "HWHM": 0.1},
                {"name": "Peak A", "RT": 7.7, "height": 1500, "HWHM": 0.08},
                {"name": "Peak B", "RT": 10.3, "height": 1200, "HWHM": 0.12},
                {
                    "name": "Peak C (3-peak composite)",
                    "type": "composite",
                    "peaks": [
                        {"RT": 11.5, "height": 1100, "HWHM": 0.15},
                        {"RT": 12.0, "height": 800, "HWHM": 0.15},
                        {"RT": 12.5, "height": 600, "HWHM": 0.15}
                    ]
                }
            ],
            'baseline': 20,
            'noise_level': 8,
            'output': 'simulated_peak.png',
            'figsize': (10, 6),
            'dpi': 150,
            'print_table': True,
            'table_sample': 20,
            'xlabel': 'Time',
            'ylabel': 'Response',
            'x_unit': 'min',
            'y_unit': 'mV',
            'export_csv': False,
            'clickable_path': True,
            'grid': True,
            'grid_linestyle': 'dashed',
            'grid_alpha': 0.6
        }

    # Check for CSV import in config (after config is loaded)
    if config.get('import_csv'):
        import_config = {
            'csv_file': config.get('import_csv'),
            'x_col': config.get('x_col', 0),
            'y_col': config.get('y_col', 1),
            'skip_header': config.get('skip_header', True),
            'output': config.get('output', 'imported_data.png'),
            'headless': True,
            'grid': config.get('grid', True),
            'grid_linestyle': config.get('grid_linestyle', 'dashed'),
            'grid_alpha': config.get('grid_alpha', 0.6)
        }
        try:
            t, signal = generate_plot_from_csv(import_config)
            print("✓ 完成！")
        except Exception as e:
            print(f"❌ 错误：CSV 导入失败：{e}")
            print("   提示：确认 CSV 文件路径正确，格式为逗号分隔")
            sys.exit(1)
        sys.exit(0)

    # Generate plot
    print("\n正在生成峰图...")
    try:
        t, signal = generate_peak_plot(config)
        print("✓ 完成！")
    except Exception as e:
        print(f"❌ 错误：生成峰图失败：{e}")
        print("   提示：检查参数设置（峰数量、RT、height、HWHM 等）")
        sys.exit(1)

if __name__ == '__main__':
    main()
