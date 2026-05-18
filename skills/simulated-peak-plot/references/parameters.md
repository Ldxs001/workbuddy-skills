# Simulated Peak Plot - Parameters Reference

## Overview

This document provides detailed information about all parameters used in the simulated peak plot generation.

## Time Range Parameters

### t_start (Start Time)
- **Description**: Start of time axis
- **Default**: 5 minutes
- **Typical range**: 0-30 minutes
- **Notes**: Should be less than t_end

### t_end (End Time)
- **Description**: End of time axis
- **Default**: 15 minutes
- **Typical range**: 5-60 minutes
- **Notes**: Should be greater than t_start

### t_points (Number of Points)
- **Description**: Number of data points in the simulation
- **Default**: 1000 (or calculated based on recommendation)
- **Typical range**: 500-10000
- **Notes**: Higher values give smoother curves but increase computation time

#### Point Recommendation Formula

```
points = max(500, ceil(duration * num_peaks * sharpness_factor * 2))

Where:
- duration = t_end - t_start
- sharpness_factor = 1.0 / hwhm_avg (average HWHM of all peaks)
- Adjustment for baseline: multiply by 1.2 if baseline > 50, 1.5 if > 100
```

#### Recommendation Table

| Duration (min) | Peaks | Baseline | Suggested Points |
|----------------|-------|----------|-------------------|
| 5-10 | 2-4 | Low (<50) | 500-800 |
| 10-20 | 4-8 | Medium (50-100) | 800-1200 |
| 20-30 | 8+ | High (>100) | 1200-2000 |
| 30+ | Any | Any | 2000+ |

## Peak Parameters

### Single Peak

Each regular peak is defined by three parameters:

#### RT (Retention Time)
- **Description**: The time at which the peak maximum occurs
- **Unit**: minutes
- **Default values**:
  - Blank peak: 5.8 min
  - Peak A: 7.7 min
  - Peak B: 10.3 min
- **Typical range**: Within [t_start, t_end]
- **Notes**: Represents the time at peak center

#### Height
- **Description**: The peak height (intensity at RT)
- **Unit**: arbitrary units (e.g., mV)
- **Default values**:
  - Blank peak: 300
  - Peak A: 1500
  - Peak B: 1200
- **Typical range**: 100-10000
- **Notes**: Represents signal intensity

#### HWHM (Half-Width at Half-Maximum)
- **Description**: The half-width of the peak at half of its maximum height
- **Unit**: minutes
- **Default values**:
  - Blank peak: 0.1
  - Peak A: 0.08
  - Peak B: 0.12
- **Typical range**: 0.01-0.5 minutes
- **Notes**: Smaller values indicate sharper (more resolved) peaks

### Composite Peak (N Sub-Peaks)

Composite peaks are created by combining **any number** of Gaussian sub-peaks. This allows for various complex peak shapes:
- **Doublet (2 peaks)**: M-shaped or shoulder peaks
- **Triplet (3 peaks)**: W-shaped or triple-peak patterns
- **Multiple (4+ peaks)**:馒头形 (bun shape), Poisson-like, or irregular shapes

#### Configuration

```json
{
  "name": "Peak C (3-peak composite)",
  "type": "composite",
  "peaks": [
    {"RT": 11.5, "height": 1100, "HWHM": 0.15},
    {"RT": 12.0, "height": 800, "HWHM": 0.15},
    {"RT": 12.5, "height": 600, "HWHM": 0.15}
  ]
}
```

#### Parameters for Composite Peaks

##### Sub-peak Count
- **Description**: Number of sub-peaks to combine
- **Value**: 1 (single peak), 2+ (composite)
- **Notes**: 2=肩膀峰/M峰, 3+=W峰/馒头峰/泊松峰等

##### RT1, RT2, ... RTn
- **Description**: Retention times of each sub-peak
- **Recommended spread**: 0.2-0.5 min apart for partial resolution, 0.1-0.2 for tight clustering
- **Notes**: Spacing determines resulting shape character

##### Height1, Height2, ... Heightn
- **Description**: Heights of each sub-peak
- **Recommended variation**: Can be equal (馒头形) or decreasing/increasing (M/W形)
- **Notes**: Height variation creates asymmetry and complexity

##### HWHM1, HWHM2, ... HWHMn
- **Description**: Half-widths of each sub-peak
- **Recommended**: Can be same (uniform broadening) or varied (mixed sharpness)
- **Typical value**: 0.1-0.2

## Signal Parameters

### Baseline
- **Description**: The baseline signal level (noise floor)
- **Unit**: same as height (e.g., mV)
- **Default**: 20
- **Typical range**: 0-100
- **Notes**: Represents background signal

### Noise Level
- **Description**: Standard deviation of Gaussian noise added to the signal
- **Unit**: same as height
- **Default**: 8
- **Typical range**: 0-50
- **Notes**: Higher values create more realistic but noisier spectra

## Output Parameters

### Output Filename (PNG)
- **Description**: Name of the output PNG file
- **Default**: `simulated_peak.png`
- **Notes**: Markdown table is printed to console (not saved to file)

### Print Markdown Table
- **Description**: Whether to print time-series data as Markdown table in console
- **Default**: True
- **Notes**: Table is sampled (every N-th point) to avoid huge output

### Table Sample Interval
- **Description**: Print every N-th point in Markdown table
- **Default**: 20
- **Typical range**: 10-100
- **Notes**: Smaller values give more detail but larger table

### Figure Size
- **Description**: Size of the output figure in inches
- **Default**: (10, 6) width × height
- **Notes**: Can be adjusted for different display requirements

### DPI
- **Description**: Dots per inch (resolution) of output image
- **Default**: 150
- **Typical range**: 72-300
- **Notes**: Higher DPI gives better quality but larger file size

## Peak Naming Convention

For universality, compounds are named generically:
- First peak (index 0): Can be blank (empty name) or "Peak 0"
- Subsequent peaks: "Peak A", "Peak B", "Peak C", etc.
- Composite peaks: "Peak X (N-peak composite)" or keep generic name

This avoids language-specific compound names and makes the skill universally applicable.

## Configuration File Format (JSON)

```json
{
  "time_range": [5, 15, 1000],
  "peaks": [
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
  "baseline": 20,
  "noise_level": 8,
  "output": "simulated_peak.png",
  "figsize": [10, 6],
  "dpi": 150,
  "print_table": true,
  "table_sample": 20
}
```

## Tips for Realistic Simulation

1. **Peak spacing**: Ensure RT values are separated by at least 3×HWHM for clear resolution
2. **Composite peaks**: Use 2-3 sub-peaks with 0.2-0.5 min spacing for M/W shapes; use same RT with varied heights for馒头形
3. **Noise level**: Set noise_level to ~5-10% of smallest peak height for realistic appearance
4. **Baseline**: Keep baseline low (10-50) relative to peak heights
5. **HWHM values**: Smaller values (<0.1) for sharp peaks, larger values (0.1-0.3) for broad peaks
6. **Points selection**: Use recommendation table or formula; more points for sharper peaks (small HWHM)
7. **Markdown table**: Use print_table=true for data output in console; adjust table_sample for detail level
