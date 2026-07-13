/**
 * Bundled synthetic demo diagnostic for the Overview page.
 *
 * Generated from reports/diagnostic_demo/diagnostic.json — a SYNTHETIC recording
 * with no real neural data. Embedded so the Overview works on Vercel with no
 * GitHub round-trip and before any token is configured. Do not edit by hand;
 * regenerate from the source JSON if the demo changes.
 *
 * Artifact values are root-relative static URLs; the PNG/SVG files are bundled
 * into the frontend build under public/reports/diagnostic_demo/.
 */

export const DEMO_DIAGNOSTIC = {
  "status": "ok",
  "config_name": "nexus-neuromirror",
  "unit_assumption": "volts (MNE-internal); EDF physical dimension expected uV",
  "recording": {
    "path": "/tmp/nnm_demo.edf",
    "n_channels": 5,
    "channel_names": [
      "EEG Fz-A1A2",
      "EEG FCz-A1A2",
      "EEG Pz-A1A2",
      "EEG Oz-A1A2",
      "Status"
    ],
    "sfreq_hz": 256,
    "n_samples": 15360,
    "duration_s": 60,
    "n_annotations": 6,
    "highpass_hz": 0,
    "lowpass_hz": 128,
    "meas_date": "1985-01-01T00:00:00+00:00"
  },
  "expected_channels": [
    {
      "canonical": "Fz",
      "matched_name": "EEG Fz-A1A2",
      "found": true,
      "metrics": {
        "rms_uv": 8.8169,
        "ptp_uv": 62.5632,
        "max_abs_uv": 33.1234,
        "mean_uv": -0.1411
      }
    },
    {
      "canonical": "FCz",
      "matched_name": "EEG FCz-A1A2",
      "found": true,
      "metrics": {
        "rms_uv": 8.8903,
        "ptp_uv": 64.812,
        "max_abs_uv": 32.7731,
        "mean_uv": -0.027
      }
    },
    {
      "canonical": "Pz",
      "matched_name": "EEG Pz-A1A2",
      "found": true,
      "metrics": {
        "rms_uv": 8.7069,
        "ptp_uv": 60.4832,
        "max_abs_uv": 31.0357,
        "mean_uv": -0.3118
      }
    },
    {
      "canonical": "Oz",
      "matched_name": "EEG Oz-A1A2",
      "found": true,
      "metrics": {
        "rms_uv": 13.0605,
        "ptp_uv": 83.7815,
        "max_abs_uv": 42.0316,
        "mean_uv": 0.1541
      }
    }
  ],
  "other_channels": [],
  "markers": {
    "n_events": 12,
    "n_annotation_events": 6,
    "n_channel_events": 6,
    "candidate_marker_channels": [
      "Status"
    ],
    "distinct_labels": [
      "code:1",
      "code:2",
      "cue/block-A",
      "cue/block-B"
    ],
    "events": [
      {
        "onset_s": 5,
        "label": "cue/block-A",
        "source": "annotation"
      },
      {
        "onset_s": 5,
        "label": "code:1",
        "source": "Status"
      },
      {
        "onset_s": 15,
        "label": "cue/block-B",
        "source": "annotation"
      },
      {
        "onset_s": 15,
        "label": "code:2",
        "source": "Status"
      },
      {
        "onset_s": 25,
        "label": "cue/block-A",
        "source": "annotation"
      },
      {
        "onset_s": 25,
        "label": "code:1",
        "source": "Status"
      },
      {
        "onset_s": 35,
        "label": "cue/block-B",
        "source": "annotation"
      },
      {
        "onset_s": 35,
        "label": "code:2",
        "source": "Status"
      },
      {
        "onset_s": 45,
        "label": "cue/block-A",
        "source": "annotation"
      },
      {
        "onset_s": 45,
        "label": "code:1",
        "source": "Status"
      },
      {
        "onset_s": 55,
        "label": "cue/block-B",
        "source": "annotation"
      },
      {
        "onset_s": 55,
        "label": "code:2",
        "source": "Status"
      }
    ]
  },
  "hard_failures": [],
  "warnings": [],
  "artifacts": [
    "reports/diagnostic_demo/trace.png",
    "reports/diagnostic_demo/trace.svg",
    "reports/diagnostic_demo/psd.png",
    "reports/diagnostic_demo/psd.svg",
    "reports/diagnostic_demo/markers.png",
    "reports/diagnostic_demo/markers.svg"
  ]
} as const;

export const DEMO_ARTIFACTS: Record<string, string> = {
  "trace_png": "/reports/diagnostic_demo/trace.png",
  "trace_svg": "/reports/diagnostic_demo/trace.svg",
  "psd_png": "/reports/diagnostic_demo/psd.png",
  "psd_svg": "/reports/diagnostic_demo/psd.svg",
  "markers_png": "/reports/diagnostic_demo/markers.png",
  "markers_svg": "/reports/diagnostic_demo/markers.svg"
};
