# Comparison: oelint-adv vs bake_linter

This document compares **oelint-adv** (a mature Yocto/OpenEmbedded linter) with our **bake_linter** implementation to identify good ideas and potential improvements.

**Analysis Date**: January 19, 2026

---

## 📋 **GOOD IDEAS FROM OELINT-ADV TO DISCUSS**

### **1. TESTING & QUALITY ASSURANCE**

#### **1.1 Test Coverage**
- ✅ **100% code coverage requirement** (`--cov-fail-under=100`)
- ✅ **Branch coverage** tracking (`--cov-branch`)
- 📝 Each rule has its own dedicated test file (e.g., `test_class_oelint_var_mandatory.py`)
- 📝 Comprehensive test base class with helper methods for temp files, args creation
- 📝 Tests include both positive and negative cases

**Your current state**: Basic pytest setup, but missing coverage requirements

**Recommendation**: Add coverage requirements and expand test cases per rule

---

#### **1.2 Test Infrastructure**
- ✅ **Fixture-based test files** - tests create temporary files with test content
- ✅ **Auto-fix testing** - `fix_and_check()` method validates auto-fix functionality
- ✅ **Parallel test execution** (`-n auto` with pytest-xdist)
- ✅ **Random test order** to catch test interdependencies

**Your current state**: Basic test structure with fixtures

**Recommendation**: Add auto-fix testing capabilities when you implement fixing

---

### **2. DOCUMENTATION**

#### **2.1 Rule Documentation**
- ✅ **Individual markdown file per rule** in `docs/wiki/`
- ✅ **Standardized template** with:
  - Severity level
  - Example (bad code)
  - "Why is this bad?" explanation
  - "Ways to fix it" with example
  - Fine-tuning options
- ✅ **Wiki URLs** embedded in output messages for easy reference
- ✅ **Auto-generated** from template

**Your current state**: Inline documentation in code only

**Recommendation**: Create wiki-style documentation for each rule - VERY useful for users!

**Example template structure**:
```markdown
# RULE_ID

severity: error

## Example

```
bad code example
```

## Why is this bad?

Explanation of the problem

## Ways to fix it

```
good code example
```
```

---

#### **2.2 Documentation Generation**
- ✅ Script to generate documentation (`wiki-creator.py`, `gen_docu.py`)
- ✅ Links to specific rule documentation in error messages

**Example from oelint-adv**:
```python
wikiurl = f'https://github.com/priv-kweihmann/oelint-adv/blob/{__version__}/docs/wiki/{self.ID}.md'
```

---

### **3. CONFIGURATION & FLEXIBILITY**

#### **3.1 Release-Specific Behavior**
- ✅ **Release selection** (`--release`) for Yocto versions (e.g., kirkstone, scarthgap)
- ✅ **Rules can be enabled/disabled per release**
  ```python
  valid_till_release: str = ''
  valid_from_release: str = ''
  ```
- ✅ **Tweaks class** manages release-specific constants and behavior

**Your current state**: No release-aware functionality

**Recommendation**: Consider adding this if you support multiple Yocto versions

---

#### **3.2 Constants Database**
- ✅ **External JSON data file** (`oelint.json`) with:
  - Known functions and their order
  - Image classes
  - Mandatory/suggested variables
  - Context-specific variables (conf-only, recipe-only, bbappend-only)
  - URL mirrors/replacements
- ✅ **Runtime modifications** via `--constantmods`:
  - `+file.json` to add
  - `-file.json` to remove
  - `file.json` to override
- ✅ **Layer-specific constant files** for customization

**Your current state**: Hardcoded constants in rules

**Recommendation**: Externalize constants to JSON - makes it MUCH more flexible!

**Example constants structure**:
```json
{
    "functions": {
        "known": [],
        "order": ["do_fetch", "do_unpack", "do_patch", ...]
    },
    "oelint-mandatoryvar": {
        "SRC_URI-exclude-classes": ["pypi", "gnomebase"],
        "image-excludes": ["CVE_PRODUCT", "HOMEPAGE", "SRC_URI"],
        "pkggroup-excludes": ["CVE_PRODUCT", "HOMEPAGE", "LICENSE", "SRC_URI"]
    }
}
```

---

#### **3.3 Rulefile System**
- ✅ **JSON rulefile** to enable/disable rules and set severity
- ✅ **`--print-rulefile`** to export current configuration
- ✅ **Useful for CI** - commit a rulefile to standardize team checks

**Your current state**: YAML config (good!) but no export functionality

**Recommendation**: Add `--print-config` to export current effective config

---

### **4. PERFORMANCE & SCALABILITY**

#### **4.1 Multiprocessing**
- ✅ **Parallel execution** with `multiprocessing.Pool`
- ✅ **Configurable job count** (`--jobs`, default: CPU count)
- ✅ **File grouping** to optimize include/require resolution
- ✅ **Context-aware multiprocessing** (handles Python 3.14+ forkserver)

**Implementation approach**:
```python
with ctx.Pool(processes=min(args.jobs, len(groups))) as pool:
    issues, fixedfiles = flatten(pool.map(partial(group_run, ...)))
```

**Your current state**: Single-threaded execution

**Recommendation**: Add multiprocessing for large codebases (MAJOR improvement!)

---

#### **4.2 Caching System**
- ✅ **Optional caching** (`--cached`, `--cachedir`)
- ✅ **Fingerprint-based** cache invalidation (hashes args + file content)
- ✅ **Per-rule and per-stash** caching
- ✅ **`--clear-caches`** option
- ✅ **Pickle-based** serialization

**Your current state**: No caching

**Recommendation**: Add caching for repeated linting (CI use case)

---

### **5. OUTPUT & FORMATTING**

#### **5.1 Customizable Output Format**
- ✅ **`--messageformat`** with placeholders:
  ```python
  '{path}:{line}:{severity}:{id}:{msg}'
  '{wikiurl}'  # Link to documentation
  '{rungroup}' # Files being checked together
  ```
- ✅ **Product matrix** appended to messages (e.g., `[branch:true]`)
  - Shows which permutation/context found the issue
  - Example: `[branch:false,mydistro.conf]` means issue only on false branch with mydistro.conf

**Your current state**: Fixed format per output type

**Recommendation**: Add customizable message templates

---

#### **5.2 Inline Suppression**
- ✅ **Per-line suppressions** with `# nooelint: RULE_ID`
- ✅ **Multiple rules** can be suppressed: `# nooelint: RULE1,RULE2`
- ✅ **Tracking of used suppressions**
- ✅ **Warning on unused suppressions** (`FileNotApplicableInlineSuppression`)

**Implementation**:
```python
# Parse comments for suppressions
m = re.match(r'^#\s+nooelint:\s+(?P<ids>[A-Za-z0-9\.,_\s-]*)', line)
# Check before reporting issue
if rule_id in inline_suppressions.get(file, {}).get(line - 1, []):
    return []  # Suppressed
```

**Your current state**: No inline suppression

**Recommendation**: Add this feature - developers love it for false positives!

---

### **6. AUTO-FIXING**

#### **6.1 Fix Capability**
- ✅ **`--fix`** flag for automatic fixes
- ✅ **`--nobackup`** to skip `.bak` creation
- ✅ **Rules implement `fix()` method** alongside `check()`
- ✅ **Marks fixable rules** with **[F]** in documentation
- ✅ **Returns list of modified files**

**Rule interface**:
```python
def fix(self, _file: str, stash: Stash) -> List[str]:
    """Fix issues in file and return list of modified files"""
    return []
```

**Your current state**: No auto-fix yet

**Recommendation**: Implement for simple issues (spacing, ordering, etc.)

---

### **7. INTEGRATION**

#### **7.1 Pre-commit Hook**
- ✅ **`.pre-commit-hooks.yaml`** for pre-commit framework
- ✅ **`.pre-commit-config.yaml`** with codespell integration
- ✅ File pattern matching for BitBake files

**Example `.pre-commit-hooks.yaml`**:
```yaml
- id: oelint-adv
  name: Advanced oelint
  description: Linter for bitbake-recipes
  entry: oelint-adv
  language: python
  language_version: python3
  files: .*\.(bb)|(bbappend)|(bbclass)|(conf)$
```

**Your current state**: No pre-commit integration

**Recommendation**: Add pre-commit hook support - easy wins for adoption!

---

#### **7.2 Shell Completion**
- ✅ **argcomplete** for bash/zsh completion
- ✅ **Custom completers** for file patterns, directories
- ✅ **`# PYTHON_ARGCOMPLETE_OK`** marker at top of main file

**Implementation**:
```python
# PYTHON_ARGCOMPLETE_OK
import argcomplete

parser.add_argument('--customrules', ...).completer = argcomplete.DirectoriesCompleter
parser.add_argument('files', ...).completer = argcomplete.FilesCompleter(
    allowednames=('bb', 'bbappend', 'bbclass', 'conf')
)
argcomplete.autocomplete(parser)
```

**Your current state**: No completion

**Recommendation**: Add argcomplete - improves UX significantly

---

### **8. ARCHITECTURE & CODE DESIGN**

#### **8.1 Parser Integration**
- ✅ **Separate parser library** (`oelint-parser`)
- ✅ **Stash object** for parsed file management
- ✅ **AST-like item hierarchy** (Variable, Inherit, Comment, Task, etc.)
- ✅ **Handles includes/requires** automatically
- ✅ **Tracks file origin** and line numbers

**Your current state**: Simple regex-based parsing

**Recommendation**: Consider extracting parser to separate module as complexity grows

---

#### **8.2 Rule Classification System**
- ✅ **File type classification** enum:
  ```python
  class Classification(Enum):
      RECIPE = 0
      BBAPPEND = 1
      BBCLASS = 2
      MACHINECONF = 3
      DISTROCONF = 4
      LAYERCONF = 5
  ```
- ✅ **Rules declare applicability** via `run_on` parameter
- ✅ **Context-aware checking** (e.g., image-only variables)
- ✅ **Automatic classification** from filename patterns

**Your current state**: Basic file type filtering with sets

**Recommendation**: Enhance file classification system with enum

---

#### **8.3 State Management**
- ✅ **Centralized State object** shared across processes
- ✅ **Immutable configuration** after initialization
- ✅ **Clean separation** of state from rules
- ✅ **Tracks inline suppressions** globally
- ✅ **Color management** per severity

**State class holds**:
- Color settings
- Inline suppressions map
- Message format
- Hide severity settings
- Suppression list
- Cache instance

**Your current state**: Configuration mixed with engine

**Recommendation**: Consider separating state management

---

### **9. CI/CD INTEGRATION**

#### **9.1 GitHub Actions**
- ✅ **Matrix testing** across Python 3.10-3.14
- ✅ **Multiple checks**:
  - pre-commit linting
  - flake8
  - pytest with coverage
  - Build sdist and wheel
  - Install and test package
- ✅ **Verifies package contents** (LICENSE, README in tarball)
- ✅ **Tests installed package** works correctly

**Pipeline stages**:
```yaml
- name: linter (pre-commit)
  run: pre-commit run --all-files
- name: linter (flake8)
  run: flake8
- name: test (pytest)
  run: pytest
- name: build
  run: python3 -m build --sdist --wheel
- name: test (installed)
  run: oelint-adv --help
```

**Your current state**: No visible CI setup

**Recommendation**: Add comprehensive CI pipeline

---

#### **9.2 Exit Code Strategy**
- ✅ **`--exit-zero`** for non-blocking CI integration
- ✅ **Different exit codes** (though could be clearer than your approach)

**Your current state**: Clear exit codes (0, 1, 2, 3) - BETTER than oelint-adv!

| Code | Meaning |
|------|---------|
| 0 | Success - no issues found |
| 1 | Errors found |
| 2 | Warnings found (no errors) |
| 3 | Runtime/configuration error |

**Recommendation**: Keep your approach, maybe add `--exit-zero` option

---

### **10. ADVANCED FEATURES**

#### **10.1 File Grouping & Context**
- ✅ **Groups related files** for analysis:
  - `.bb` files grouped by recipe name
  - Matching `.bbappend` files added to group
  - `.bbclass` files grouped by class name
- ✅ **Machine/distro conf** permutations in "all" mode
- ✅ **Matrix testing** of different configurations
- ✅ **Shares includes/requires** within group

**Grouping logic**:
```python
# Group bb files by name
for f in files:
    if f.endswith('.bb'):
        key = basename_without_version(f)
        groups[key].add(f)

# Add matching bbappends
for f in files:
    if f.endswith('.bbappend'):
        for group in groups:
            if matches_pattern(f, group):
                groups[group].add(f)
```

**Your current state**: Individual file analysis

**Recommendation**: Add file relationship awareness for complex checks

---

#### **10.2 Custom Rules Support**
- ✅ **`--customrules`** to load external rule directories
- ✅ **`--addrules`** to activate non-default rule sets
- ✅ **Plugin architecture** for third-party rules
- ✅ **Dynamic rule loading** from Python modules

**Usage**:
```bash
oelint-adv --customrules /path/to/custom/rules --addrules jetm recipes/
```

**Your current state**: All rules are built-in

**Recommendation**: Add plugin system for organization-specific rules

---

#### **10.3 Mode Selection**
- ✅ **`--mode fast`** (default) - basic checks
- ✅ **`--mode all`** - comprehensive checks with:
  - Machine configuration permutations
  - Distro configuration permutations
  - Branch permutations (true/false)
  - Multiple test matrices

**Your current state**: Single mode

**Recommendation**: Consider if multiple modes would be valuable

---

### **11. PACKAGING & DISTRIBUTION**

#### **11.1 Package Metadata**
- ✅ **Comprehensive pyproject.toml** with:
  - Build system requirements
  - Package data inclusion
  - Dynamic version from module
  - Multiple Python version classifiers (3.10-3.14)
  - Development dependencies
- ✅ **MANIFEST.in** to control package contents
- ✅ **Version management** with bumpversion tool

**Your current state**: Basic pyproject.toml

**Recommendation**: Enhance metadata and add version management

---

#### **11.2 Dependencies**
- ✅ **Separate parser library** (`oelint-parser`)
- ✅ **Data package** (`oelint-data`) for constants
- ✅ **Minimal runtime dependencies**:
  - `anytree` for data structures
  - `argcomplete` for completion
  - `colorama` for colors
  - `urllib3` for network

**Your current state**: Minimal dependencies (PyYAML only)

**Recommendation**: Keep dependencies minimal, add only what's needed

---

### **12. ERROR REPORTING**

#### **12.1 Finding Method**
- ✅ **Centralized `finding()` method** in Rule base class
- ✅ **Automatic suppression checking**
- ✅ **Severity filtering**
- ✅ **Path normalization** (absolute/relative)
- ✅ **Color application** based on severity
- ✅ **Matrix information** appended

**Method signature**:
```python
def finding(self, _file: str, _line: int,
            override_msg: str = None,
            appendix: str = None,
            blockoffset: int = 0,
            severity_override: str = '') -> Tuple[...]:
```

**Your current state**: `create_result()` helper method

**Recommendation**: Your approach is cleaner - keep it!

---

#### **12.2 Rule Appendix System**
- ✅ **Sub-IDs for rules** (e.g., `oelint.var.mandatoryvar.LICENSE`)
- ✅ **Dynamic appendix** based on what was found
- ✅ **Documented in README** with **[S]** marker

**Example**:
```python
# Rule can have multiple appendixes
appendix = ['LICENSE', 'SUMMARY', 'DESCRIPTION']
# Finding creates: oelint.var.mandatoryvar.LICENSE
```

**Your current state**: Single ID per rule

**Recommendation**: Consider if sub-IDs would be useful for grouped checks

---

## 🎯 **TOP PRIORITIES FOR YOUR LINTER**

Based on impact vs. effort:

### **MUST HAVE** (High Impact, Medium Effort):
1. ✅ **Rule documentation wiki** - Users need this!
   - Create `docs/rules/` directory
   - One markdown file per rule
   - Use template for consistency
   - Link from error messages

2. ✅ **Inline suppressions** (`# nolint: RULE_ID`)
   - Parse comments for suppression markers
   - Track which suppressions are used
   - Warn on unused suppressions

3. ✅ **Pre-commit hook** integration
   - Create `.pre-commit-hooks.yaml`
   - Add to installation instructions

4. ✅ **Constants database** (external JSON)
   - Extract hardcoded lists to `data/constants.json`
   - Support runtime modifications
   - Document customization options

5. ✅ **100% test coverage** requirement
   - Update pytest.ini with coverage settings
   - Add coverage badge to README
   - Write tests for all uncovered code

### **SHOULD HAVE** (High Impact, High Effort):
6. ✅ **Multiprocessing** for performance
   - Use `multiprocessing.Pool`
   - Make job count configurable
   - Test on large codebases

7. ✅ **Auto-fix** capability
   - Add `--fix` flag
   - Implement `fix()` method for rules
   - Create backups by default

8. ✅ **Caching system**
   - Hash-based cache invalidation
   - Optional via `--cached` flag
   - Configurable cache directory

9. ✅ **Export config** functionality
   - `--print-config` to show effective config
   - Helps users understand what's active
   - Useful for CI setup

### **NICE TO HAVE** (Medium Impact):
10. ✅ **Shell completion** (argcomplete)
    - Easy to add
    - Big UX improvement

11. ✅ **Custom rules plugin** system
    - `--custom-rules-dir` option
    - Document plugin API

12. ✅ **Release-specific** behavior
    - `--release` flag for Yocto versions
    - Rules can be version-aware

13. ✅ **File grouping** for related files
    - Group .bb + .bbappend
    - Shared context analysis

### **MAYBE LATER** (Lower Priority):
14. ✅ **Separate parser module**
    - Only if complexity justifies it

15. ✅ **Multiple test modes**
    - Fast vs comprehensive

16. ✅ **Configuration permutations**
    - Machine/distro matrix testing

---

## 🚫 **WHAT YOUR LINTER DOES BETTER**

Don't lose these advantages:

### **✅ Architecture**
- **Clearer exit codes** (0, 1, 2, 3 vs. just 0/1)
- **Multiple output formats** (HTML, JSON, JSONL)
- **Better organized output** module
- **Modern type hints** throughout
- **Cleaner separation** of concerns

### **✅ Configuration**
- **YAML config** (more readable than JSON)
- **Comprehensive default config** file
- **Better documented** config options
- **Rule grouping** by category

### **✅ Code Quality**
- **More Pythonic** code style
- **Better dataclass** usage
- **Cleaner models** (LintResult, FileContext)
- **Better naming** conventions

### **✅ Documentation**
- **More comprehensive README**
- **Better examples** in documentation
- **Clearer configuration** instructions
- **Professional copyright** headers

### **✅ User Experience**
- **Better error messages**
- **More intuitive** CLI arguments
- **Clearer output** formatting
- **Better organized** rules by category

---

## 📊 **FEATURE COMPARISON MATRIX**

| Feature | oelint-adv | bake_linter | Recommendation |
|---------|-----------|--------------|----------------|
| **Testing** |
| 100% coverage | ✅ | ❌ | Add |
| Branch coverage | ✅ | ❌ | Add |
| Parallel tests | ✅ | ❌ | Add |
| Auto-fix tests | ✅ | ❌ | Add when implementing fix |
| **Documentation** |
| Rule wiki | ✅ | ❌ | **HIGH PRIORITY** |
| Doc generation | ✅ | ❌ | Add |
| Wiki URLs in output | ✅ | ❌ | Add |
| **Configuration** |
| Config file | ✅ JSON | ✅ YAML | Keep YAML |
| Export config | ✅ | ❌ | Add |
| Constants DB | ✅ | ❌ | **HIGH PRIORITY** |
| Release-aware | ✅ | ❌ | Consider |
| **Performance** |
| Multiprocessing | ✅ | ❌ | **HIGH PRIORITY** |
| Caching | ✅ | ❌ | Add |
| File grouping | ✅ | ❌ | Consider |
| **Output** |
| Custom format | ✅ | ❌ | Consider |
| Multiple formats | ❌ | ✅ | Keep advantage |
| Inline suppression | ✅ | ❌ | **HIGH PRIORITY** |
| **Auto-fixing** |
| Fix capability | ✅ | ❌ | Add |
| Backup option | ✅ | ❌ | Add with fix |
| **Integration** |
| Pre-commit | ✅ | ❌ | **HIGH PRIORITY** |
| Shell completion | ✅ | ❌ | Add |
| CI/CD ready | ✅ | ✅ | Enhance |
| **Extensibility** |
| Custom rules | ✅ | ❌ | Add |
| Plugin system | ✅ | ❌ | Consider |
| **Code Quality** |
| Type hints | Partial | ✅ | Keep advantage |
| Modern Python | ✅ | ✅ | Equal |
| Clean architecture | ✅ | ✅ | Equal |

---

## 📝 **IMPLEMENTATION ROADMAP**

### **Phase 1: Foundation** (1-2 weeks)
- [ ] Add test coverage requirements
- [ ] Create rule documentation template
- [ ] Set up docs/rules/ directory
- [ ] Extract constants to JSON file
- [ ] Add inline suppression support

### **Phase 2: Integration** (1 week)
- [ ] Add pre-commit hook configuration
- [ ] Add shell completion (argcomplete)
- [ ] Add --print-config option
- [ ] Enhance CI pipeline

### **Phase 3: Performance** (2-3 weeks)
- [ ] Implement multiprocessing
- [ ] Add caching system
- [ ] Add file grouping logic

### **Phase 4: Auto-fixing** (2-3 weeks)
- [ ] Design fix() interface
- [ ] Implement fixes for simple rules
- [ ] Add --fix and --nobackup flags
- [ ] Add auto-fix tests

### **Phase 5: Extensibility** (1-2 weeks)
- [ ] Add custom rules support
- [ ] Document plugin API
- [ ] Add release-awareness if needed

---

## 🔗 **REFERENCES**

- **oelint-adv**: https://github.com/priv-kweihmann/oelint-adv
- **oelint-parser**: https://github.com/priv-kweihmann/oelint-parser
- **OpenEmbedded Styleguide**: https://www.openembedded.org/wiki/Styleguide

---

## 📞 **NEXT STEPS**

1. **Review this document** with the team
2. **Prioritize features** based on your use cases
3. **Create issues** for selected improvements
4. **Start with high-impact, medium-effort** items
5. **Maintain your advantages** while adding new features

---

**Remember**: Don't try to copy everything - pick what makes sense for your use case and users!
