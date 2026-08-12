#!/usr/bin/env python3
"""
run_qicas.py — QICAS Pipeline Launcher
=======================================
Group-friendly launcher. Three modes:

  --new          Interactive setup for a new system
  --from_json    Load system from JSON file and generate SLURM script
  --test         Run benchmark test cases to verify pipeline works

Usage:
    python run_qicas.py --new
    python run_qicas.py --from_json my_system.json
    python run_qicas.py --test
    python run_qicas.py --list
"""

import os
import sys
import json
import math
import argparse
import subprocess
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.resolve()
CONFIGS_DIR  = REPO_ROOT / "configs"
RESULTS_DIR  = REPO_ROOT / "results"
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
TESTS_DIR    = REPO_ROOT / "tests"

RESULTS_DIR.mkdir(exist_ok=True)

# ── Auto-detect HPC environment ───────────────────────────────────────────
def detect_env():
    hostname = subprocess.getoutput("hostname")
    on_hpc   = any(x in hostname.lower() for x in ["noctua","n2cn","n2login"])

    # Find block2 env
    candidates = [
        os.path.expanduser("~/.block2_fix/block2_env.sh"),
        os.path.expanduser("~/envs/block2env/bin/activate"),
    ]
    block2_env = next((c for c in candidates if os.path.exists(c)), None)

    # Find benchmark script
    script_candidates = [
        REPO_ROOT / "scripts" / "qicas_casscf_benchmark.py",
        Path.home() / "activeml/qio/QIO-master/examples_benchmark/pilot/benchmark_geom/qicas_casscf_benchmark.py",
    ]
    benchmark_script = next((str(p) for p in script_candidates if p.exists()), None)

    # HPC account
    account = "hpc-prf-qehpc"
    if on_hpc:
        acct = subprocess.getoutput(
            "sacctmgr show user $(whoami) -n -p 2>/dev/null | cut -d'|' -f2 | head -1"
        ).strip()
        if acct:
            account = acct

    return dict(
        hostname=hostname, on_hpc=on_hpc,
        block2_env=block2_env,
        benchmark_script=benchmark_script,
        account=account,
    )


# ── Bond distance database ────────────────────────────────────────────────
BOND_DB = {
    ("Ti","F","oct"):2.02, ("Ti","Cl","oct"):2.35, ("Ti","Br","oct"):2.259,
    ("V", "Cl","oct"):2.28,("V", "Br","oct"):2.318,("V", "Br","tet"):2.318,
    ("Cr","Cl","tet"):2.24,("Cr","Cl","oct"):2.34, ("Cr","Br","oct"):2.48,
    ("Mn","Cl","tet"):2.35,("Mn","Cl","oct"):2.48, ("Mn","Br","tet"):2.50,
    ("Mn","Br","oct"):2.63,("Mn","F","oct"):1.98,
    ("Fe","Cl","tet"):2.19,("Fe","Cl","oct"):2.38, ("Fe","Br","oct"):2.50,
    ("Co","Cl","oct"):2.44,("Co","Br","tet"):2.35,
    ("Ni","Cl","oct"):2.40,("Ni","Cl","sq_pl"):2.20,("Ni","Br","oct"):2.53,
    ("Cu","Br","oct"):2.46,
    ("Mo","Cl","oct"):2.42,("Mo","Br","tet"):2.451,
    ("Ru","Br","tet"):2.375,
    ("Rh","Br","tet"):2.356,("Rh","Br","oct"):2.356,
    ("Pd","Br","sq_pl"):2.337,("Pd","Br","oct"):2.337,
    ("Ir","Br","oct"):2.384,
    ("Pt","Br","sq_pl"):2.328,
}

def get_dist(metal, ligand, geom):
    key = (metal, ligand, geom)
    if key in BOND_DB:
        return BOND_DB[key]
    # Generic fallback
    defaults = {"F":2.00,"Cl":2.35,"Br":2.45,"I":2.65,"O":2.00,"N":2.15}
    return defaults.get(ligand, 2.40)


# ── DMRG parameters by spin ───────────────────────────────────────────────
def dmrg_params(spin_2s):
    if spin_2s >= 4:
        return dict(M=100, sweeps=30, window_size=26, spin_cat="high",
                    time="08:00:00", mem="48G")
    elif spin_2s >= 2:
        return dict(M=100, sweeps=30, window_size=24, spin_cat="medium",
                    time="06:00:00", mem="32G")
    else:
        return dict(M=100, sweeps=35, window_size=22, spin_cat="low",
                    time="06:00:00", mem="32G")


# ── Validate and complete a system config ─────────────────────────────────
def complete_config(cfg):
    """Fill in all optional fields with sensible defaults."""
    required = ["metal","ligand","charge","spin_2s","geometry"]
    missing  = [r for r in required if r not in cfg or cfg[r] is None]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    metal  = cfg["metal"]
    ligand = cfg["ligand"]
    geom   = cfg["geometry"]
    spin   = int(cfg["spin_2s"])

    # Auto-fill bond distance
    if not cfg.get("dist_ang") and not cfg.get("xyz_file"):
        cfg["dist_ang"] = get_dist(metal, ligand, geom)
        print(f"  Bond distance: {cfg['dist_ang']} Å (auto)")

    # Auto-fill n_ligands
    if not cfg.get("n_ligands"):
        defaults = {"tet":4,"oct":6,"sq_pl":4}
        cfg["n_ligands"] = defaults.get(geom, 6)
        print(f"  n_ligands: {cfg['n_ligands']} (auto from geometry)")

    # Auto-fill DMRG params
    p = dmrg_params(spin)
    cfg.setdefault("M",           p["M"])
    cfg.setdefault("sweeps",      p["sweeps"])
    cfg.setdefault("window_size", p["window_size"])
    cfg["spin_cat"] = p["spin_cat"]
    cfg["_time"]    = p["time"]
    cfg["_mem"]     = p["mem"]
    print(f"  Spin category: {p['spin_cat'].upper()}")
    print(f"  DMRG: M={cfg['M']}, sweeps={cfg['sweeps']}, window={cfg['window_size']}")

    # Auto-fill name
    if not cfg.get("name"):
        chg = cfg["charge"]
        cfg["name"] = f"{metal}_{ligand}{cfg['n_ligands']}_chg{chg:+d}_spin{spin}_{geom}"
        print(f"  Name: {cfg['name']} (auto)")

    return cfg


# ── Generate SLURM script ─────────────────────────────────────────────────
def generate_slurm(cfg, env):
    name   = cfg["name"]
    script = env.get("benchmark_script",
             str(REPO_ROOT / "scripts" / "qicas_casscf_benchmark.py"))

    # block2 env activation
    b2 = env.get("block2_env","")
    if b2.endswith(".sh"):
        env_cmd = f"source {b2}"
    elif b2:
        env_cmd = f"conda activate {Path(b2).name}"
    else:
        env_cmd = "# WARNING: activate block2 env manually before running"

    # Python args
    args = [
        f"--system_name '{name}'",
        f"--metal {cfg['metal']}",
        f"--ligand {cfg['ligand']}",
        f"--n_ligands {cfg['n_ligands']}",
        f"--charge {cfg['charge']}",
        f"--spin_2s {cfg['spin_2s']}",
        f"--geometry {cfg['geometry']}",
        f"--M {cfg['M']}",
        f"--sweeps {cfg['sweeps']}",
        f"--window_size {cfg['window_size']}",
        f"--out_dir results",
        f"--save_mo",
    ]
    if cfg.get("xyz_file"):
        args.append(f"--xyz '{cfg['xyz_file']}'")
    elif cfg.get("dist_ang"):
        args.append(f"--dist_ang {cfg['dist_ang']}")

    ac = cfg.get("autocas_reference")
    if ac and ac.get("ne"):
        args.append(f"--autocas_ne {ac['ne']}")
        args.append(f"--autocas_no {ac['no']}")

    args_str = " \\\n    ".join(args)

    return f"""#!/bin/bash
#SBATCH --job-name=qicas_{name[:15]}
#SBATCH --account={env['account']}
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem={cfg['_mem']}
#SBATCH --time={cfg['_time']}
#SBATCH --output=logs/qicas_{name}_%j.out
#SBATCH --error=logs/qicas_{name}_%j.err

{env_cmd}

BENCH_DIR=$(dirname $(realpath $0))
mkdir -p "$BENCH_DIR/logs" "$BENCH_DIR/results"
cd "$BENCH_DIR"

echo "=== QICAS: {name} ==="
echo "Host: $(hostname)  Date: $(date)"
echo "Spin: {cfg['spin_cat'].upper()} (2S={cfg['spin_2s']})"
echo "DMRG: M={cfg['M']} sweeps={cfg['sweeps']} window={cfg['window_size']}"

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK

python {script} \\
    {args_str}

echo "=== Finished {name} at $(date) ==="
"""


# ── Interactive new system ────────────────────────────────────────────────
def new_system(env):
    print("\n" + "="*55)
    print("  QICAS — New System")
    print("="*55 + "\n")

    cfg = {}
    cfg["metal"]    = input("Metal (e.g. Mn, Fe, V, Ni): ").strip().capitalize()
    cfg["ligand"]   = input("Ligand (e.g. Cl, Br, F, O): ").strip()
    cfg["charge"]   = int(input("Total charge (e.g. -2): ").strip())
    cfg["spin_2s"]  = int(input("Spin 2S (5=sextet, 4=quintet, 2=triplet, 0=singlet): ").strip())

    geom_hint = "oct" if cfg["ligand"] in ["F","O","N"] else "tet"
    geom = input(f"Geometry [tet/oct/sq_pl] (default={geom_hint}): ").strip()
    cfg["geometry"] = geom if geom else geom_hint

    # XYZ or ideal geometry?
    src = input("\nGeometry source:\n  1. Ideal parametric (auto bond distance)\n  2. DFT-optimized XYZ file\nChoice [1/2]: ").strip()
    if src == "2":
        cfg["xyz_file"] = input("XYZ file path: ").strip()
    else:
        auto_dist = get_dist(cfg["metal"], cfg["ligand"], cfg["geometry"])
        d = input(f"Bond distance Å (default={auto_dist}): ").strip()
        cfg["dist_ang"] = float(d) if d else auto_dist

    # AutoCAS reference
    has_ac = input("\nDo you have AutoCAS reference? [y/N]: ").strip().lower()
    if has_ac == "y":
        ne = int(input("  AutoCAS n_active_e: ").strip())
        no = int(input("  AutoCAS n_active_o: ").strip())
        cfg["autocas_reference"] = {"ne": ne, "no": no}

    return cfg


# ── Benchmark test runner ─────────────────────────────────────────────────
def run_tests(env):
    """
    Check 3 benchmark reference systems.
    Compares existing result JSONs against known reference values.
    Does NOT rerun calculations — just validates stored results.
    """
    print("\n" + "="*55)
    print("  QICAS — Benchmark Validation")
    print("="*55)

    # Reference values from completed benchmark
    references = [
        {
            "name": "MnCl4 sextet",
            "file": BENCHMARKS_DIR / "MnCl4_chg-2_spin5_reference.json",
            "checks": {
                "qicas.n_active": 14,
                "qicas.n_active_e": 21,
                "spin_cat": "high",
            }
        },
        {
            "name": "VBr6 triplet",
            "file": BENCHMARKS_DIR / "VBr6_chg-3_spin2_reference.json",
            "checks": {
                "qicas.n_active": 10,
                "qicas.n_active_e": 18,
                "spin_cat": "medium",
            }
        },
        {
            "name": "MnBr4 singlet",
            "file": BENCHMARKS_DIR / "MnBr4_chg-1_spin0_reference.json",
            "checks": {
                "qicas.n_active": 14,
                "qicas.n_active_e": 24,
                "spin_cat": "low",
            }
        },
    ]

    all_pass = True
    for ref in references:
        print(f"\n  Checking: {ref['name']}")
        if not ref["file"].exists():
            print(f"    ⚠️  Reference file not found: {ref['file'].name}")
            print(f"       Run this system first, then copy JSON to benchmarks/")
            all_pass = False
            continue

        d = json.loads(ref["file"].read_text())
        for key, expected in ref["checks"].items():
            # Support dotted keys like "qicas.n_active"
            parts = key.split(".")
            val = d
            for p in parts:
                val = val.get(p, None)
                if val is None:
                    break

            if val == expected:
                print(f"    ✅ {key} = {val}")
            else:
                print(f"    ❌ {key}: expected {expected}, got {val}")
                all_pass = False

    print()
    if all_pass:
        print("  All benchmark checks passed — pipeline is ready.")
    else:
        print("  Some checks failed or reference files missing.")
        print("  See benchmarks/README.md to set up reference files.")
    return all_pass


# ── List results ──────────────────────────────────────────────────────────
def list_results():
    jsons = sorted(RESULTS_DIR.glob("*.json"))
    if not jsons:
        print("\nNo results yet in results/")
        return
    print(f"\n{'System':<38} {'Cat':>7} {'2S':>4} {'AutoCAS':>10} {'QICAS':>10} {'ΔCASCI':>10}")
    print("-"*85)
    for jf in jsons:
        try:
            d = json.loads(jf.read_text())
            if d.get("status") != "OK":
                continue
            name = d.get("name","?")[:36]
            cat  = d.get("spin_cat","?")
            spin = d.get("spin_2s","?")
            ac   = d.get("autocas_reference",{})
            ac_s = f"({ac.get('ne','?')}e,{ac.get('no','?')}o)" if ac else "N/A"
            qi   = d.get("qicas",{})
            qi_s = f"({qi.get('n_active_e','?')}e,{qi.get('n_active','?')}o)"
            dlt  = d.get("goal1_casci",{}).get("delta_mha","?")
            dlt_s= f"{dlt:+.1f}" if isinstance(dlt,float) else str(dlt)
            print(f"{name:<38} {cat:>7} {spin:>4} {ac_s:>10} {qi_s:>10} {dlt_s:>10} mHa")
        except Exception:
            pass


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="QICAS Pipeline Launcher")
    p.add_argument("--new",       action="store_true",
                   help="Interactive: set up new system")
    p.add_argument("--from_json", metavar="FILE",
                   help="Load system config from JSON file")
    p.add_argument("--test",      action="store_true",
                   help="Validate against benchmark reference systems")
    p.add_argument("--list",      action="store_true",
                   help="List all completed results")
    p.add_argument("--submit",    action="store_true",
                   help="Auto-submit to SLURM after generating script")
    args = p.parse_args()

    env = detect_env()
    print(f"\nEnvironment: {'Noctua2 HPC' if env['on_hpc'] else 'local'}")
    if not env["block2_env"]:
        print("WARNING: block2 env not found — activate manually before submitting")
    if not env["benchmark_script"]:
        print("WARNING: qicas_casscf_benchmark.py not found")
        print("         Copy it to scripts/ or set path in detect_env()")

    if args.list:
        list_results()
        return

    if args.test:
        run_tests(env)
        return

    # Get system config
    if args.from_json:
        path = Path(args.from_json)
        if not path.exists():
            print(f"ERROR: File not found: {path}")
            sys.exit(1)
        print(f"\nLoading: {path}")
        cfg = json.loads(path.read_text())
    elif args.new:
        cfg = new_system(env)
    else:
        p.print_help()
        return

    # Complete config
    print("\nValidating and completing config...")
    cfg = complete_config(cfg)

    # Save config
    cfg_out = RESULTS_DIR / f"{cfg['name']}_config.json"
    cfg_out.write_text(json.dumps(cfg, indent=2))
    print(f"\nConfig saved: {cfg_out.name}")

    # Generate SLURM
    slurm = generate_slurm(cfg, env)
    slurm_path = REPO_ROOT / f"submit_{cfg['name']}.slurm"
    slurm_path.write_text(slurm)
    print(f"SLURM script: {slurm_path.name}")

    print(f"""
{'='*55}
  READY
{'='*55}
  System : {cfg['name']}
  Spin   : {cfg['spin_cat'].upper()} (2S={cfg['spin_2s']})
  DMRG   : M={cfg['M']}, sweeps={cfg['sweeps']}, window={cfg['window_size']}

  Submit : sbatch {slurm_path.name}
  Monitor: squeue -u $USER
  Results: python run_qicas.py --list
""")

    if args.submit and env["on_hpc"]:
        r = subprocess.run(["sbatch", str(slurm_path)],
                           capture_output=True, text=True)
        print(r.stdout)
        if r.returncode != 0:
            print("ERROR:", r.stderr)


if __name__ == "__main__":
    main()
