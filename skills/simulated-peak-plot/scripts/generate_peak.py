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
from math import ceil

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
    import os

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
    output_file = config.get('output', 'imported_data.png')
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

    # Auto-scale y-axis
    y_max = signal.max() * 1.1
    plt.ylim(0, y_max)

    # Save
    plt.savefig(output_file, bbox_inches='tight')

    # Output path
    import os
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
    """Display a table of recommended points."""
    print("\n" + "="*60)
    print(" Point Recommendation Table")
    print("="*60)
    print("\nFormula: points = max(500, duration * peaks * sharpness_factor)")
    print("\nTypical recommendations:")
    print("-" * 60)
    print(f"{'Duration (min)':<15} {'Peaks':<10} {'Baseline':<15} {'Suggested Points':<20}")
    print("-" * 60)
    print(f"{'5-10':<15} {'2-4':<10} {'Low (<50)':<15} {'500-800':<20}")
    print(f"{'10-20':<15} {'4-8':<10} {'Medium (50-100)':<15} {'800-1200':<20}")
    print(f"{'20-30':<15} {'8+':<10} {'High (>100)':<15} {'1200-2000':<20}")
    print(f"{'30+':<15} {'Any':<10} {'Any':<15} {'2000+':<20}")
    print("-" * 60)

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
    import os

    # Determine output path - replace or append _data.csv
    base_name = os.path.splitext(output_file)[0]
    csv_file = base_name + '_data.csv'

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
        - time_range: [start, end, points]
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

    # Extract parameters
    t_start, t_end, t_points = config.get('time_range', [5, 15, 1000])
    peaks_config = config.get('peaks', [])
    baseline = config.get('baseline', 20)
    noise_level = config.get('noise_level', 8)
    output_file = config.get('output', 'simulated_peak.png')
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
        # Check if composite peak (N sub-peaks)
        if peak_config.get('type') == 'composite':
            # Composite peak: combine multiple Gaussian peaks
            sub_peaks = peak_config.get('peaks', [])
            if len(sub_peaks) >= 1:
                signal += generate_composite_peak(t, sub_peaks)

                # For annotation, use the combined peak info
                rts = [p['RT'] for p in sub_peaks]
                heights = [p['height'] for p in sub_peaks]
                mid_rt = sum(rts) / len(rts)
                max_height = max(heights)

                annotation_peaks.append({
                    'name': peak_config.get('name', f'Composite ({len(sub_peaks)} peaks)'),
                    'RT': mid_rt,
                    'height': max_height,
                    'is_composite': True,
                    'num_sub_peaks': len(sub_peaks)
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

    # Add noise
    signal += np.random.normal(0, noise_level, len(t))

    # Plot
    plt.figure(figsize=figsize, dpi=dpi)
    plt.plot(t, signal, color='#1f77b4', linewidth=1.5)

    # Annotate peaks
    for i, peak in enumerate(annotation_peaks):
        if peak.get('name', '').strip() or peak.get('annotate', True):
            label = peak.get('name', f'Peak {chr(65+i)}')  # Peak A, B, C...

            # For composite peaks, add note about sub-peak count
            if peak.get('is_composite', False):
                label += f" ({peak.get('num_sub_peaks', '?')}-peak composite)"

            height_offset = peak.get('annotation_height_offset', 50)
            text_offset = peak.get('annotation_text_offset', 300)

            plt.annotate(f"{label}\n{peak['RT']:.1f} min",
                        xy=(peak['RT'], peak['height'] + height_offset),
                        xytext=(peak['RT'], peak['height'] + text_offset),
                        arrowprops=dict(arrowstyle="->", color='gray'),
                        ha='center', fontsize=10, va='bottom')

    # Labels and formatting (with customizable units)
    plt.xlabel(f'{xlabel} ({x_unit})', fontsize=12)
    plt.ylabel(f'{ylabel} ({y_unit})', fontsize=12)

    # Grid lines (customizable style and visibility)
    if show_grid:
        plt.grid(True, linestyle=grid_linestyle, alpha=grid_alpha)
    else:
        plt.grid(False)

    plt.xlim(t_start, t_end)

    # Auto-scale y-axis with some padding
    y_max = max(signal) * 1.1
    plt.ylim(0, y_max)

    # Save PNG
    plt.savefig(output_file, bbox_inches='tight')

    # Output clickable file path
    import os
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

def interactive_config():
    """Interactive dialogue to configure parameters."""
    print("=" * 60)
    print(" Simulated Peak Plot Generator - Interactive Configuration")
    print("=" * 60)

    config = {}

    # Show point recommendation table
    show_point_recommendation_table()

    # Time range
    print("\n--- Time Range ---")
    t_start = float(input("Start time (min) [default: 5]: ") or "5")
    t_end = float(input("End time (min) [default: 15]: ") or "15")

    # Calculate and show recommended points
    default_points = calculate_recommended_points(t_start, t_end, 4, 20, 0.1)
    print(f"\nRecommended points: {default_points}")
    t_points = int(input(f"Number of points [recommended: {default_points}]: ") or default_points)

    config['time_range'] = [t_start, t_end, t_points]

    # Peaks
    print("\n--- Peaks Configuration ---")
    print("Note: First peak can be a blank/reference peak (leave name empty)")
    print("Note: Composite peaks combine N sub-peaks (1=single, 2+=composite shape)")

    peaks = []
    num_peaks = int(input("\nNumber of peak groups (including blank and composite) [default: 4]: ") or "4")

    for i in range(num_peaks):
        print(f"\nPeak Group {i+1}:")
        if i == 0:
            name = input(f"  Name (leave empty for blank peak): ") or " "
        else:
            default_name = f"Peak {chr(64+i)}"  # Peak A, B, C...
            name = input(f"  Name [default: {default_name}]: ") or default_name

        # Ask if composite peak (N sub-peaks)
        if i > 0:  # Not for first blank peak
            num_sub_peaks = int(input("  Number of sub-peaks in this group (1=single, 2+=composite) [default: 1]: ") or 1)

            if num_sub_peaks > 1:
                # Composite peak with N sub-peaks
                sub_peaks = []
                print(f"  --- Enter {num_sub_peaks} sub-peaks ---")
                for j in range(num_sub_peaks):
                    print(f"    Sub-peak {j+1}:")
                    rt = float(input(f"      RT (min): "))
                    height = float(input(f"      Height: "))
                    hwhm = float(input(f"      HWHM [default: 0.15]: ") or "0.15")
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

        rt = float(input(f"  Retention Time (RT) in min [default: {default_rt}]: ") or default_rt)
        height = float(input(f"  Height [default: {default_height}]: ") or default_height)
        hwhm = float(input(f"  HWHM [default: {default_hwhm}]: ") or default_hwhm)

        peaks.append({
            'name': name,
            'RT': rt,
            'height': height,
            'HWHM': hwhm
        })

    config['peaks'] = peaks

    # Signal settings
    print("\n--- Signal Settings ---")
    config['baseline'] = float(input("Baseline [default: 20]: ") or "20")
    config['noise_level'] = float(input("Noise level (std dev) [default: 8]: ") or "8")

    # CSV Import Option
    print("\n--- Data Source ---")
    use_csv = input("Import data from existing CSV file? (y/n) [default: n]: ").lower() == 'y'
    if use_csv:
        csv_path = input("CSV file path: ").strip()
        config['import_csv'] = csv_path
        config['x_col'] = int(input("X column index [default: 0]: ") or "0")
        config['y_col'] = int(input("Y column index [default: 1]: ") or "1")
        config['skip_header'] = input("CSV has header row? (y/n) [default: y]: ").lower() != 'n'
        config['output'] = input("Output PNG filename [default: imported_data.png]: ") or "imported_data.png"
        return config  # Skip rest of config for CSV import

    # Output settings
    print("\n--- Output Settings ---")
    output_base = input("Output filename base (without extension) [default: simulated_peak]: ") or "simulated_peak"
    config['output'] = output_base + '.png'
    config['figsize'] = (10, 6)
    config['dpi'] = 150

    # Markdown table output
    print_markdown = input("\nPrint data as Markdown table in console? (y/n) [default: y]: ").lower() != 'n'
    config['print_table'] = print_markdown

    if print_markdown:
        sample = input("Sample interval (print every N-th point) [default: 20]: ") or "20"
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
    parser = argparse.ArgumentParser(description='Simulated Peak Plot Generator')
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
        t, signal = generate_plot_from_csv(import_config)
        print("✓ Done!")
        sys.exit(0)

    # Check for CSV import in config
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
        t, signal = generate_plot_from_csv(import_config)
        print("✓ Done!")
        sys.exit(0)

    # Load or create configuration
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
        print(f"✓ Loaded configuration from: {args.config}")
    elif args.interactive or not args.config:
        config = interactive_config()
    else:
        # Default configuration (including composite peak with 3 sub-peaks)
        config = {
            'time_range': [5, 15, 1000],
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

    # Generate plot
    print("\nGenerating peak plot...")
    t, signal = generate_peak_plot(config)

    print("✓ Done!")

if __name__ == '__main__':
    main()
