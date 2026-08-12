# QICAS Active Space Benchmark Pipeline

Automated pipeline for running QICAS active space selection on transition
metal complexes and comparing against AutoCAS.

## Quick Start

```bash
# Clone on Noctua2
git clone <repo_url> && cd qicas_pipeline

# Activate environment (auto-detected, but do this first)
source ~/.block2_fix/block2_env.sh

# Option 1: Validate pipeline with benchmark systems
python run_qicas.py --test

# Option 2: New system from JSON file
python run_qicas.py --from_json docs/new_system_template.json

# Option 3: Interactive setup
python run_qicas.py --new

# Submit and monitor
sbatch submit_<system>.slurm
squeue -u $USER

# See all results
python run_qicas.py --list
```

## For a New System — Workflow

1. **Copy template**: `cp docs/new_system_template.json my_system.json`
2. **Fill in**: metal, ligand, charge, spin_2s, geometry, dist_ang
3. **Run**: `python run_qicas.py --from_json my_system.json`
4. **Submit**: `sbatch submit_<system>.slurm`
5. **Result**: JSON file appears in `results/` when done

## JSON Input (minimum required)

```json
{
  "metal": "Fe",
  "ligand": "Cl",
  "charge": -1,
  "spin_2s": 4,
  "geometry": "tet"
}
```

Everything else (bond distance, DMRG parameters, SLURM settings)
is auto-filled based on spin category.

## New Chat Session with Claude

Upload `CONTEXT.md` and say:
> "I am running QICAS. Read CONTEXT.md. Here is my new system JSON: [paste JSON]"

Claude immediately generates the correct script — no background explanation needed.

## Repository Structure

```
qicas_pipeline/
├── run_qicas.py          # Main launcher
├── CONTEXT.md            # Upload to new Claude chat sessions
├── README.md
├── benchmarks/           # 3 verified reference systems for testing
│   ├── MnCl4_chg-2_spin5_reference.json
│   ├── VBr6_chg-3_spin2_reference.json
│   ├── MnBr4_chg-1_spin0_reference.json
│   └── README.md
├── configs/
│   └── autocas_reference_database.json
├── docs/
│   └── new_system_template.json
├── scripts/              # Copy qicas_casscf_benchmark.py here
└── results/              # Output JSONs go here
```

## Spin Category Auto-Selection

| 2S | Category | Time limit | Memory | DMRG M |
|----|----------|-----------|--------|--------|
| ≥4 | HIGH | 8h | 48G | 100 |
| 2-3 | MEDIUM | 6h | 32G | 100 |
| 0-1 | LOW | 6h | 32G | 100 |

## HPC Environment

- Cluster: Noctua2, PC2 Paderborn
- Account: hpc-prf-qehpc (auto-detected)
- Environment: `~/.block2_fix/block2_env.sh` (auto-detected)
- No manual node/partition configuration needed
