# Benchmark Reference Systems

These JSON files are verified QICAS results used to test the pipeline.

## Included References

| File | System | Spin | Category |
|------|--------|------|----------|
| `MnCl4_chg-2_spin5_reference.json` | [MnCl4]²⁻ sextet | 2S=5 | HIGH |
| `VBr6_chg-3_spin2_reference.json`  | [VBr6]³⁻ triplet | 2S=2 | MEDIUM |
| `MnBr4_chg-1_spin0_reference.json` | [MnBr4]⁻ singlet | 2S=0 | LOW |

## What Gets Checked

`python run_qicas.py --test` verifies:
- `qicas.n_active` matches reference
- `qicas.n_active_e` matches reference
- `spin_cat` is correct

## Adding a New Reference System

1. Run your system through the QICAS pipeline
2. Copy the output JSON to this directory
3. Rename it to `<name>_reference.json`
4. Add it to the `references` list in `tests/test_pipeline.py`

## JSON Fields Required for Benchmark

```json
{
  "name": "...",
  "spin_cat": "high|medium|low",
  "status": "OK",
  "qicas": {
    "n_active": <int>,
    "n_active_e": <int>
  },
  "goal1_casci": {
    "delta_mha": <float>
  }
}
```
