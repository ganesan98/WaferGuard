# WaferGuard

A beginner's guide to running, understanding, and explaining a Python wafer inspection qualification project.

## 1. What the project does

WaferGuard creates artificial wafer images containing spots and scratches at known positions. An OpenCV program examines each image and reports possible defects. A separate scoring function compares those reports with the known positions, and automated tests check whether the program meets specific requirements.

You can run it on a laptop. The current model uses a circular, unpatterned surface with simulated brightness variation and noise. A wafer is the thin disk of semiconductor material used to manufacture chips. Here, its surface is represented by a grayscale image.

The central software quality engineering question is whether an inspection program finds the expected defects, reports extra defects, behaves consistently, and handles bad input correctly.

### Current evidence

| Item | Current status |
| --- | --- |
| Local automated suite | 27 tests passed on the user's Python 3.12.10 environment |
| Demo | Successfully generated two cases and a JSON report |
| Sensitivity experiment | 48 measured conditions saved in `experiment_output/sensitivity.csv` |
| Spacing experiment | Script exists as `waferguard/seperation.py`. Its results have not yet been reviewed |
| GitHub automation | Workflow file added. A successful GitHub run still needs verification |

The 27 passing tests describe the selected test cases. The sensitivity experiment deliberately includes difficult conditions that the inspector can miss.

## 2. The complete flow

```text
Define defects and a random seed
             |
             v
     NumPy image generator
             |
             +----> image pixels ----> OpenCV inspector ----> candidates
             |                                                  |
             +----> placement records ----> matcher <------------+
                                               |
                                               v
                                  matches, misses, extra candidates
                                               |
                                               v
                                   assertions and saved reports
```

The placement records are called ground truth. They supply the expected answer. The inspector receives only image pixels, while the matcher receives both the expected positions and the reported positions.

The inspector is the system under test, often shortened to SUT. The generator, matcher, and tests form the surrounding qualification framework.

## 3. Run it on Windows

Open PowerShell in the extracted project directory containing `requirements.txt`, `README.md`, `waferguard`, and `tests`.

For the current installation, that directory is `C:\Users\Lenovo\OneDrive\Documents\WaferGuard-Project`.

### First setup

Use Python 3.12 for this project's pinned dependencies.

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
```

A virtual environment is a project-specific Python installation and collection of packages. Activation makes the terminal use that environment. The prompt should start with `(.venv312)` and the version should show Python 3.12.x.

If PowerShell blocks activation because scripts are disabled, run the following in that same terminal, then activate again.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv312\Scripts\Activate.ps1
```

This execution-policy change lasts for the current PowerShell session. If an organization policy still blocks activation, use the environment's executable directly, for example `.\.venv312\Scripts\python.exe -m pytest -q`.

### Each later session

Open the project folder and activate the existing environment again. Installation is needed when setting up the environment or changing dependencies.

```powershell
.\.venv312\Scripts\Activate.ps1
python -m pytest -q
python -m waferguard.demo
explorer .\demo_output
```

The `-m` option runs a Python module. For example, `waferguard.demo` means the `demo.py` module inside the `waferguard` package. Run these commands from the project root so Python can find that package.

Run `deactivate` to leave the virtual environment.

## 4. Where everything lives

```text
WaferGuard-Project/
  README.md
  requirements.txt
  pytest.ini
  .gitignore
  waferguard/
    __init__.py
    synthetic.py
    inspection.py
    matching.py
    demo.py
    sensitivity.py
    seperation.py
  tests/
    test_matching.py
    test_qualification.py
  .github/
    workflows/
      qualification.yml
```

| File | Responsibility |
| --- | --- |
| `synthetic.py` | Make the wafer image and inject defects from placement records |
| `inspection.py` | Find possible defects from image pixels |
| `matching.py` | Pair candidates with expected locations and calculate scores |
| `demo.py` | Save example images, overlays, and a JSON report |
| `sensitivity.py` | Measure detection across size, contrast, and noise conditions |
| `seperation.py` | Investigate the effect of spacing between two spots |
| `test_matching.py` | Check the matching and scoring rules with supplied coordinates |
| `test_qualification.py` | Check inspection behavior across controlled scenarios |
| `requirements.txt` | Pin NumPy, OpenCV, and pytest to specific versions |
| `pytest.ini` | Tell pytest where tests live and configure its output |
| `.gitignore` | Keep environments and generated results out of ordinary Git additions |
| `qualification.yml` | Describe how GitHub should run and report the tests |

The filename `seperation.py` uses the spelling present in this checkout. Its output directory uses the spelling `separation`.

## 5. How an image becomes numbers

A grayscale image is a grid of brightness values. This project uses 256 rows and 256 columns. Each value is an unsigned 8-bit integer, called `uint8`, ranging from 0 for black to 255 for white.

A position is written as `(x, y)`, where x is the column and y is the row. NumPy indexes the corresponding pixel as `image[y, x]`. Coordinates start at zero.

NumPy provides arrays and operations across all their pixels. OpenCV provides image-processing operations. Pytest discovers test functions and runs their assertions. CSV stores experiment tables, JSON stores structured demo results, and PNG stores the images.

## 6. How the generator works

The generator first creates a circular wafer centered at `(128, 128)` with radius 112 pixels. A pixel belongs to the circle when `(x - 128)^2 + (y - 128)^2 <= 112^2`.

Inside the circle, brightness varies gradually with position. This models uneven illumination. The background outside the wafer is darker.

A defect record holds an ID, kind, center, size, and contrast. For example, `Defect("bright-particle", "spot", 85, 93, 4, 78)` describes a circular spot centered at `(85, 93)` with radius 4. Its pixels receive a brightness increase of 78. Negative contrast makes a defect darker.

For a scratch, size means horizontal half-length. A scratch extends from `x - size` to `x + size`, with a thickness of three pixel rows. The same size field has different meanings for spots and scratches.

The generator then adds Gaussian noise, which randomly changes pixel brightness around a mean of zero. The noise argument is its standard deviation. Larger values generally produce larger brightness fluctuations. Finally, values are rounded, clipped to the range 0–255, and converted to `uint8`.

The random seed recreates the same noise for the same inputs in the same software environment. A seed is useful when a test fails because it identifies a reproducible image. At noise zero, changing the seed produces the same image.

Ground truth comes from the placement records created before detection. The renderer uses NumPy and imports no OpenCV inspection logic. This separates the oracle from the detection algorithm. The tests still depend on a simplified synthetic model, which limits what their results establish.

## 7. How the inspector works

### Validate the input

The array must be a 256 × 256 `uint8` grayscale image. The file-reading entry point decodes the file without converting color or bit depth automatically. Missing, empty, corrupt, color, wrong-size, and 16-bit files are checked by tests. Invalid input raises `InspectionInputError`.

### Estimate the local background

The inspector converts values to floating point before subtraction. This allows signed differences between pixels. Subtracting directly in unsigned 8-bit arithmetic can wrap negative values around.

It then applies Gaussian blur with `sigmaX=5`. Blurring computes a weighted neighborhood average, producing an estimate of the slowly varying background. This helps account for the illumination gradient. The estimate also absorbs some of the defect signal.

### Calculate the residual and threshold it

For each pixel, residual means `abs(original brightness - blurred brightness)`. A pixel with original brightness 190 and estimated background 130 has residual 60. A dark pixel of brightness 70 against background 130 also has residual 60.

Pixels with residual at least 24 become candidates. The inspector also restricts processing to an interior circle of radius 98 pixels, avoiding the strong brightness transition at the wafer boundary. This deliberately excludes some of the wafer area.

### Group pixels and report centers

OpenCV groups candidate pixels using eight-neighbor connectivity. Horizontal, vertical, and diagonal neighbors can connect. Each group is a connected component. Groups smaller than five pixels are discarded.

The remaining groups become `Detection` records containing a center and pixel area. The center, or centroid, is the mean position of the component's pixels. The inspector sorts detections by vertical position and then horizontal position, giving a stable output order.

The inspector reports locations and component areas. It does not classify a reported component as a spot or scratch. Defect kinds are known by the generator.

## 8. How matching and scoring work

The matching tolerance is three pixels, inclusive. The distance between two centers is `sqrt((x1 - x2)^2 + (y1 - y2)^2)`.

If truth is `(10, 10)` and a candidate is `(12, 11)`, the distance is about 2.24 pixels and the pair is valid. A candidate at `(14, 10)` is four pixels away and cannot match that truth point.

Each truth record and candidate can be used once. The matcher tries closer candidates first and can reassign an earlier pairing to allow more truth points to match. This is maximum-cardinality matching using augmenting paths. It maximizes the number of valid pairs. The total distance of all pairs is not an optimization objective.

| Outcome | Meaning |
| --- | --- |
| True positive, TP | A candidate paired with an expected defect within tolerance |
| False negative, FN | An expected defect left unmatched, also called a miss |
| False positive, FP | A candidate left unmatched, also called an extra detection |

Two candidates near one real defect can produce one match and one extra. A candidate too far from a real defect can produce both an extra and a miss.

Precision is `TP / (TP + FP)`. It asks how many reported candidates received credit. Recall is `TP / (TP + FN)`. It asks how many expected defects were found. If there are three true defects, two valid matches, and one extra candidate, precision and recall are both `2/3`.

The code returns `None` when a ratio's denominator is zero. JSON writes that as `null`. For one missed defect and zero candidates, recall is zero and precision is undefined. The project uses object-level matching, so a count of every correct background pixel is not part of the score.

**The three settings to remember**

| Setting | Unit | Decision it controls |
| --- | --- | --- |
| Residual threshold 24 | Brightness difference | Which pixels become candidates |
| Minimum component area 5 | Pixels | Which connected groups are retained |
| Matching tolerance 3 | Pixel distance | Which reported centers get credit |

## 9. Read the demo results

```powershell
python -m waferguard.demo
explorer .\demo_output
Get-Content .\demo_output\report.json
```

The mixed case contains a bright spot, a dark spot, and a dark scratch. The low-contrast case contains a faint spot with contrast +8. The demo saves each original PNG, an annotated version with `-overlay` in its filename, and `report.json`.

Blue/cyan rings indicate the known placement centers. Green crosses indicate reported candidate centers. The annotations are drawn after inspection and are not supplied to the inspector.

The mixed case should produce three matches and zero extras. The faint case demonstrates a miss. Its ring has no matching cross, recall is zero, and precision is null. The JSON contains seeds, ground truth, paired centers and distances, missed records, and extra candidates.

The demo saves files and prints their destination. It has no graphical application window. Demo images use the file-decoding entry point, exercising PNG encoding and decoding as part of the flow.

## 10. Understand the automated tests

A unit test supplies known inputs to one small piece of logic and asserts the expected result. Matcher unit tests provide coordinates directly. An integration test checks several pieces together. The PNG qualification test creates a known image, writes it, decodes it, runs inspection, and scores its output.

Pytest discovers functions named `test_...`. An `assert` fails when its condition is false. Parameterization runs a test with multiple input cases. The `tmp_path` fixture provides a temporary directory for a test's files.

| ID | Scenario | Assertion |
| --- | --- | --- |
| Q01 | Clean frames at noise 0, 2, and 6 | Zero reported defects for the selected seeds |
| Q02 | One bright spot read from PNG | One valid match and zero extras |
| Q03 | Three defects across 32 noisy frames | All 96 defects matched within tolerance, with zero extras |
| Q04 | Spot radii 1–4 at high contrast and no noise | All selected probes detected. A separate one-pixel spot is filtered |
| Q05 | A defect entirely in the excluded rim | Zero reported candidates |
| Q06 | Repeated generation and inspection | Reproducible output, different noisy pixels for a different seed, and unchanged input pixels |
| Q07 | Unsupported or unreadable files | Controlled `InspectionInputError` |
| Q08 | Faint spot | The known miss is recorded correctly |
| Q09 | Deliberately raise threshold to 100 | The normal detection assertion rejects the changed behavior |

Matcher tests separately cover duplicate candidates, reassignment in an ambiguous case, a candidate just beyond tolerance, empty inputs, and invalid tolerance values.

Q08 and Q09 pass when they observe the intended failure behavior. Q09 temporarily changes the threshold using `monkeypatch`, calls the normal detection assertion, and expects an `AssertionError`. Pytest restores the threshold afterward. This is one targeted mutation demonstration. It shows that a particular check detects a plausible regression.

The 32-frame Q03 batch is one pytest test function, so pytest's test count and the number of images processed are different quantities.

Useful commands follow.

```powershell
python -m pytest -q
python -m pytest -v
python -m pytest -q -k test_q02_single_particle_on_decoded_wafer
python -m pytest -q --junitxml=qualification-results.xml
```

When a detection check fails, its message includes the seed, missing defect records, extra candidates, and matches. Recreate the image using the seed and defect records, inspect its overlay, and determine whether the issue arose during detection or matching.

## 11. Understand the sensitivity experiment

```powershell
python -m waferguard.sensitivity
Invoke-Item .\experiment_output\sensitivity.csv
```

The experiment checks radii 1, 2, 3, and 4; positive contrasts 10, 25, 50, and 75; noise levels 0, 2, and 6; and seeds 100–109. That produces 48 rows with ten defect images each, plus ten clean images per noise level. There are 510 inspection calls in total. At noise zero, the ten seeded images for one condition are identical.

| CSV field | Meaning |
| --- | --- |
| `threshold` | Inspector brightness-residual threshold used in this run |
| `radius_px` | Injected spot radius |
| `contrast` | Added spot brightness |
| `noise_sigma` | Standard deviation of brightness noise |
| `frames` | Trials for that condition |
| `matched`, `missed` | Total matched and unmatched expected defects |
| `recall` | Matched divided by matched plus missed |
| `extra_detections` | Total unmatched candidates |
| `extras_per_frame` | Extra detections divided by frames |
| `clean_detections_per_frame` | Average candidate count on clean frames at that noise level |

The clean-frame measurement is computed once per noise level and repeated across its rows. Summing that repeated column would count the same baseline repeatedly.

### Findings from the saved run

All tested spots at contrasts 50 and 75 were detected. All at contrast 10 were missed. Contrast 25 gave the following recalls.

| Radius | Noise 0 | Noise 2 | Noise 6 |
| --- | --- | --- | --- |
| 1 px | 100% | 0% | 0% |
| 2 px | 0% | 30% | 50% |
| 3 px | 0% | 0% | 80% |
| 4 px | 0% | 0% | 30% |

There were zero extra candidates in the defect trials and zero candidates in the selected clean trials.

A radius-two, contrast-25, noise-two row with three matches and seven misses means recall `3/10 = 30%`. Each trial contains one expected defect, so the accounting is straightforward.

A larger spot affects more of the blurred background estimate and can therefore reduce its own residual. Noise can push some pixels above threshold and others below it. Since the inspector requires five connected pixels, changes in connectivity can affect the final candidate count. These mechanisms help explain the observed behavior, but inspecting residuals and components for individual seeds would be needed to confirm a specific cause.

This is an exploratory characterization of bright center spots under these conditions. It has ten trials per condition, with repeated images at zero noise. The experiment does not automatically turn measured recall values into acceptance requirements. Re-running overwrites the CSV.

## 12. Understand the spacing experiment

```powershell
python -m waferguard.seperation
explorer .\experiment_output\separation
```

Two spots have radius 3, contrast 75, and zero noise. Their centers move symmetrically apart from separation 2 to 20 pixels in steps of two. The script saves ten overlays and a CSV containing candidate counts, centers, matches, misses, and extras. Results have not yet been reviewed for this checkout.

Inspect candidate count and centers before looking at matches. One candidate between the two expected positions suggests the response has formed one retained component. Depending on its location, it may match one expected defect or fall outside both matching tolerances.

At separations of six pixels or less, the rendered spot footprints overlap or touch. The generator adds contrast for each defect, so shared pixels receive both additions and can clip at 255. The CSV's `physical_footprints_overlap` flag marks this geometry condition; the distances refer to the synthetic image. Use the overlays to distinguish overlapping injected shapes from failures to separate visually distinct responses.

## 13. GitHub automation

The workflow is `.github/workflows/qualification.yml`. It triggers on pushes, pull requests, and manual requests through GitHub Actions. It expects `requirements.txt` at the repository root.

On a fresh Linux runner, it downloads the repository, selects Python 3.12, installs dependencies, and runs pytest. Pytest writes `qualification-results.xml`, a structured JUnit-format report. The final workflow step attempts to upload that report even when tests fail.

After committing and pushing the workflow to a GitHub repository, open its Actions tab, select the WaferGuard qualification run, inspect the test log, and download the report artifact. A failed pytest command makes the job fail. Branch protection would be a separate repository setting if you wanted a passing check to be required before merging.

The workflow file is installed locally. Its first successful hosted run still needs verification. GitHub executes the qualification suite; the two exploratory experiments are run separately with the commands above.

`.gitignore` includes `.venv312/`, `experiment_output/`, and `qualification-results.xml` to keep local environments and generated data out of ordinary commits. It also ignores caches and demo output. Already tracked files require separate handling by Git.

## 14. Relevance to software quality engineering

The project gives you concrete examples of defining expected behavior, building reproducible inputs, separating the test oracle from the SUT, testing invalid input, measuring misses and false alarms, diagnosing boundary behavior, and running regression checks automatically.

KLA describes inspection and review tools that identify, locate, and analyze defects on wafer surfaces. WaferGuard's connection is the qualification of inspection output and its failure cases. The scope is a synthetic educational model, with no physical calibration or proprietary algorithm reproduction. [KLA annual report](https://ir.kla.com/sec-filings/annual-reports/content/0000319201-26-000027/klac-20260630.htm)

Current limits include fixed image geometry, an excluded rim, simple shapes, limited noise and illumination models, and no defect classification. Minimum detectable size depends on contrast and noise in this model. Pixel sizes cannot be converted to physical defect sizes without calibration. Real-image validation, a hardware interface, performance targets, and a long-duration reliability run remain outside the current evidence.

## 15. Interview revision

### A short explanation to practice

> WaferGuard qualifies a simple Python and OpenCV inspection system using synthetic wafer images. The generator records defect positions before rendering, the inspector receives only the image, and the matcher pairs reported positions with expected ones within three pixels. The tests cover detection, false alarms, repeatability, invalid files, and a deliberate threshold regression. I also ran a sensitivity experiment that showed strong-contrast spots were detected consistently in the selected trials while near-threshold behavior depended on size and noise.

### Questions and reasoning to understand

| Interview question | Points to explain |
| --- | --- |
| What is being tested? | The image-only OpenCV inspector, its file entry point, and the correctness of the surrounding matching logic |
| How do you know the expected answer? | The generator's placement records establish positions before inspection |
| Why synthetic images? | Exact positions and controlled variation support reproducible qualification |
| Why blur the image? | Estimate local illumination so gradual brightness variation is accounted for |
| Why take the absolute difference? | Both bright and dark departures can become candidates |
| Why five pixels? | It is the current component-size filter, trading small responses against rejection of isolated pixels |
| Why a three-pixel tolerance? | It is an explicit chosen acceptance rule in image coordinates. A real system would need a justified localization requirement |
| Can larger defects be harder? | The background estimate absorbs part of a broader feature, changing its residual |
| Why can noise improve some outcomes? | It can push enough neighboring pixels over threshold near a detection boundary |
| What did the experiments show? | Contrast 50 and 75 gave full recall in the selected trials; contrast 10 gave zero; contrast 25 depended on size and noise |
| How do you prove the tests catch a regression? | Q09 raises the threshold to 100 and checks that a normally passing detection assertion fails |
| Why are all tests green if some defects are missed? | The faint-case test expects and verifies a miss; normal detection cases require successful matches |
| Does the output identify scratches? | The inspector reports component centers and areas. The generator supplies the known shape labels |
| What have you verified on GitHub? | A workflow is configured locally. Confirm its hosted run before claiming successful CI execution |
| What was your own contribution? | Describe the parts you actually implemented, ran, investigated, or revised and explain the assistance you used |

### A three-minute demonstration

1. Run `python -m pytest -q` and explain what the 27 passing cases cover.
2. Open `mixed-overlay.png` and explain the expected centers and reported centers.
3. Open `low-contrast-overlay.png` and point out the miss in `report.json`.
4. Show the saved sensitivity table and explain one successful condition and one weak condition.
5. Show Q09 and explain how its temporary threshold change exposes a regression.
6. If a hosted workflow has run, show its actual log and report artifact.

Use the guide to explain decisions and results in your own words. A useful preparation check is to trace one defect from its placement record through rendering, thresholding, component formation, matching, and a final assertion.

## 16. Troubleshooting

| Symptom | What to check |
| --- | --- |
| Activation script blocked | Use the process-scoped PowerShell policy command in setup |
| Wrong Python version | Activate `.venv312` and check `python --version` |
| `No module named cv2` or `pytest` | Install `requirements.txt` using the active environment's Python |
| `No module named waferguard` | Run from the directory containing the `waferguard` folder |
| Demo prints only a save message | Open `demo_output` to see the PNGs and JSON |
| Spacing command cannot find the module | This checkout uses `python -m waferguard.seperation` |
| Existing experiment results change after running again | The scripts overwrite their output files using the current settings |
| A normally passing detection test fails | Check threshold 24, reproduce the reported seed, and inspect the recorded misses and extras |
| GitHub workflow is not running | Confirm the workflow was committed under `.github/workflows/` in the repository and inspect the Actions tab |
