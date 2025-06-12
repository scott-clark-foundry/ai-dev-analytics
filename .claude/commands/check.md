# Quality Check Command

Run quality checks before committing or moving between tasks.

## Steps:

1. **Format check**
   ```bash
   black src/ tests/ --check
   ```
   If formatting needed, run without --check flag

2. **Lint**
   ```bash
   ruff check src/ tests/
   ```
   Fix any critical issues, note warnings for later

3. **Type check**
   ```bash
   mypy src/ --strict
   ```
   Ensure all type hints are correct

4. **Run tests**
   ```bash
   pytest -v
   ```
   All tests should pass

5. **Check for debug code**
   ```bash
   grep -r "print(" src/ | grep -v "#"
   grep -r "breakpoint()" src/
   ```

## Early Development Mode
If in early development, you can be lenient on:
- Missing tests (note for later)
- Non-critical lint warnings
- TODO comments

But always ensure:
- Code runs without errors
- No syntax errors
- No security issues

Report results and any issues that were skipped with justification.