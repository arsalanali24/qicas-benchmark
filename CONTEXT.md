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
Work dir: ~/activeml/qio/QIO-master/examples_benchmark/pilot/benchmark_geom/
```

**Upload files from Windows:**
```powershell
scp <file> hpcmual@fe.noctua2.pc2.uni-paderborn.de:~/activeml/qio/QIO-master/examples_benchmark/pilot/benchmark_geom/<file>
```

---

## How to Start a New Calculation

**Option A — New system from scratch:**
```bash
python run_qicas.py --new
```
Asks: metal, ligand, charge, spin (2S), geometry. Auto-fills everything else.

**Option B — From an existing JSON file:**
```bash
python run_qicas.py --from_json my_system.json
```
Reads the JSON, validates it, generates SLURM script, ready to submit.

**Option C — Run benchmark test cases first:**
```bash
python run_qicas.py --test
```
Runs 3 known benchmark systems (MnCl4, VBr6, MnBr4low) and checks results
match reference values. Confirms pipeline is working before new calculations.

---

## JSON Input Format

To run a new system, create a JSON file with this structure:

```json
{
  "name": "Fe_Cl4_chg-1_spin4",
  "metal": "Fe",
  "ligand": "Cl",
  "n_ligands": 4,
  "charge": -1,
  "spin_2s": 4,
  "geometry": "tet",
  "dist_ang": 2.19,
  "xyz_file": null,
  "autocas_reference": {
    "ne": 15, "no": 9
  }
}
```

**Minimal required fields:** `metal`, `ligand`, `charge`, `spin_2s`, `geometry`

**Optional fields:**
- `dist_ang` — bond distance in Å (auto-filled from database if omitted)
- `xyz_file` — path to DFT-optimized XYZ file (overrides `dist_ang`)
- `autocas_reference` — known AutoCAS result for comparison
- `M`, `sweeps`, `window_size` — DMRG parameters (auto-selected by spin if omitted)

---

## Benchmark Reference Systems

Three verified systems are included in `benchmarks/` for testing:

| System | 2S | QICAS result | Metric A |
|---|---|---|---|
| MnCl4 (sextet) | 5 | (21e,14o) | −50.0 mHa |
| VBr6 (triplet) | 2 | (18e,10o) | −14.0 mHa |
| MnBr4 (singlet) | 0 | (24e,14o) | −4.8 mHa |

Run `python run_qicas.py --test` to verify these before new calculations.

---

## Output

Each run produces a JSON file in `results/` with:
- Active space selected by QICAS
- Entropies before/after F_QI rotation
- CASCI energy delta (QICAS vs HF orbitals)
- CASSCF convergence comparison

---

## In a New Chat Session

Upload `CONTEXT.md` and say:
> "I am running the QICAS pipeline. Read CONTEXT.md.
>  I want to run [system name] — here is my JSON: [paste JSON]"

Claude will immediately generate the correct SLURM script and commands.
No background explanation needed.
