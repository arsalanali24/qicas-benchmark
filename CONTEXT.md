# QICAS Pipeline — Context File
## Upload this file at the start of every new chat session

---

## What This Pipeline Does

Runs **QICAS** (Quantum Information-based Active Space selection) on transition
metal complexes and compares against **AutoCAS** (entropy plateau method).

One pipeline run produces:
- QICAS active space (n_active_e, n_active_o)
- Entropies before and after F_QI orbital rotation
- CASCI energy comparison (QICAS vs HF orbitals)
- CASSCF warm-start comparison
- Full JSON result file

---

## HPC Environment (Noctua2, PC2 Paderborn)

```
Login:    hpcmual@fe.noctua2.pc2.uni-paderborn.de
Account:  hpc-prf-qehpc
Env:      source ~/.block2_fix/block2_env.sh
Repo:     ~/qicas_pipeline/
Script:   ~/qicas_pipeline/scripts/qicas_casscf_benchmark.py
```

**Upload files from Windows:**
```powershell
scp <file> hpcmual@fe.noctua2.pc2.uni-paderborn.de:~/qicas_pipeline/<file>
```

---

## ⚠️ CRITICAL — DMRG Parameters (NEVER CHANGE THESE)

| Spin (2S) | Category | M | sweeps | window_size | time | mem |
|---|---|---|---|---|---|---|
| ≥ 4 | HIGH | **100** | **30** | **26** | 8h | 48G |
| 2–3 | MEDIUM | **100** | **30** | **24** | 6h | 32G |
| 0–1 | LOW | **100** | **35** | **22** | 6h | 32G |

- **M=100 always** — never 250, never 500. M=500 is only for separate Metric A validation.
- **window_size is never 4** — minimum is 22, maximum 26.
- These are auto-selected by `run_qicas.py` — do not override.

---

## ⚠️ CRITICAL — Working Directory and Script Usage

```
Login node only:  python run_qicas.py --from_json system.json
                  → generates SLURM script, does NOT run calculations

SLURM job calls:  scripts/qicas_casscf_benchmark.py   (the real pipeline)
                  → never call run_qicas.py inside a SLURM job
```

All files live in `~/qicas_pipeline/` — never in `~/activeml/qio/.../benchmark_geom/`

---

## How to Start a New Calculation

**Step 1 — Create input JSON** (5 fields required):
```json
{
  "metal": "Fe",
  "ligand": "Cl",
  "charge": -1,
  "spin_2s": 4,
  "geometry": "tet"
}
```
Optional: `dist_ang`, `xyz_file`, `n_ligands`, `autocas_reference`

**Step 2 — On login node, generate SLURM script:**
```bash
cd ~/qicas_pipeline
source ~/.block2_fix/block2_env.sh
python run_qicas.py --from_json my_system.json
```

**Step 3 — Submit:**
```bash
sbatch submit_<system_name>.slurm
squeue -u hpcmual
```

**Step 4 — Check results:**
```bash
python run_qicas.py --list
```

---

## Benchmark Reference Systems (verified results)

| System | 2S | Category | QICAS active space |
|---|---|---|---|
| MnCl4 (sextet) | 5 | HIGH | (21e,14o) |
| VBr6 (triplet) | 2 | MEDIUM | (18e,10o) |
| MnBr4 (singlet) | 0 | LOW | (24e,14o) |

Run `python run_qicas.py --test` to verify these before new calculations.

---

## Bond Distance Defaults (auto-filled if not specified)

| Metal | Ligand | Geometry | Distance (Å) |
|---|---|---|---|
| Mn | Cl | tet | 2.35 |
| Mn | Br | tet | 2.50 |
| Mn | Br | oct | 2.63 |
| Fe | Cl | tet | 2.19 |
| Fe | Br | oct | 2.50 |
| V | Br | oct | 2.318 |
| Ni | Br | oct | 2.53 |
| Cr | Cl | tet | 2.24 |

---

## What run_qicas.py Generates (example for FeCl4 quintet)

```bash
# Input JSON (5 required fields):
{
  "metal": "Fe",
  "ligand": "Cl",
  "charge": -1,
  "spin_2s": 4,
  "geometry": "tet"
}

# Auto-filled values:
# dist_ang = 2.19 (from database)
# n_ligands = 4 (from tet geometry)
# M = 100, sweeps = 30, window_size = 26 (from spin_2s=4, HIGH spin)
# time = 8h, mem = 48G

# Generated SLURM script calls:
python scripts/qicas_casscf_benchmark.py \
    --system_name 'Fe_Cl4_chg-1_spin4_tet' \
    --metal Fe --ligand Cl --n_ligands 4 \
    --charge -1 --spin_2s 4 --geometry tet \
    --M 100 --sweeps 30 --window_size 26 \
    --dist_ang 2.19 --out_dir results --save_mo
```

---

## GitHub Repository

```
https://github.com/arsalanali24/qicas-benchmark
git clone https://github.com/arsalanali24/qicas-benchmark.git
```

---

## In a New Chat Session

Upload `CONTEXT.md` and say:
> "I am running QICAS. Read CONTEXT.md carefully especially the CRITICAL sections.
>  Generate input JSON and SLURM script for: [metal, ligand, charge, 2S, geometry]"

Claude will generate correct parameters. If Claude suggests M≠100 or window_size<22,
that is wrong — refer it back to the CRITICAL sections above.

---

## Common Chemistry Mistakes to Avoid

Always verify electron/spin consistency before submitting:
- Total electrons = sum(atomic numbers) - charge
- Fe=26, Mn=25, V=23, Ni=28, Cr=24, Co=27, Cu=29
- Cl=17, Br=35, F=9, O=8
- (n_electrons mod 2) must equal (spin_2s mod 2)

Common valid combinations:
- [FeCl4]²⁻ charge=-2, 2S=4 (Fe²⁺ d⁶ quintet) ✅
- [FeCl4]⁻  charge=-1, 2S=5 (Fe³⁺ d⁵ sextet)  ✅
- [MnCl4]²⁻ charge=-2, 2S=5 (Mn²⁺ d⁵ sextet)  ✅
- [VBr6]³⁻  charge=-3, 2S=2 (V³⁺ d² triplet)   ✅

## Note on S²=6 in CASSCF output

If CASSCF shows S²=6.0 for a quintet (2S=4) system — this means
CASSCF converged to wrong spin state (septet). This is a known
AutoCAS failure mode. QICAS active space avoids this in most cases.

---

## Quick Start Commands for Every New System

After getting the JSON from Claude, do exactly this on Noctua2:

```bash
# 1. Login
ssh hpcmual@fe.noctua2.pc2.uni-paderborn.de

# 2. Go to pipeline directory and activate environment
cd ~/qicas_pipeline
source ~/.block2_fix/block2_env.sh

# 3. Create JSON file (paste your system values)
cat > my_system.json << 'JSONEOF'
{
  "metal": "Cr",
  "ligand": "Cl",
  "charge": -2,
  "spin_2s": 4,
  "geometry": "tet"
}
JSONEOF

# 4. Generate SLURM script
python run_qicas.py --from_json my_system.json

# 5. Submit
sbatch submit_<system_name>.slurm

# 6. Monitor
squeue -u hpcmual
tail -f logs/qicas_<system>_*.out
```
