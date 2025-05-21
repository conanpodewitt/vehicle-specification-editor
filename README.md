# Vehicle Specification Editor
This application is a prototype graphical user interface (GUI) for editing, compiling, and verifying specifications written in the Vehicle language. 

> **Note:**  
> This is a prototype application. Some features may be under active development or have limitations.

## Key Features

#### Code Editor
- Central editor with syntax highlighting for `.vcl` files.

#### File Management
- Standard **New**, **Open**, and **Save** operations for Vehicle specification files.

#### Compilation & Verification
- Buttons to trigger **Compile** and **Verify** operations on the current specification.
- Option to set a specific verifier (e.g., **Marabou**).
- A **Stop** button to interrupt ongoing compilation or verification processes.

#### Resource Management
- An **Additional Input** panel to specify:
  - Paths for required resources like networks and datasets.
  - Values for parameters

#### Interactive Console
- **Problems** tab displaying errors and detailed tracebacks.
- **Output** tab showing standard output from Vehicle commands.

#### Hierarchical Output View (Under Development)
- After verification or compilation, a tree-like structure in the **Output** panel shows:
  - Properties and their associated queries.
  - Verification status (`True` / `False` / `Pending`).
  - Counterexamples for disproven properties

## Build Instructions
### 1. Open a virtual environment
For example, a conda environment or Python venv/virtualenv environment

### 2. Install `vehicle-lang` from source
Clone the repository [vehicle-updates](https://github.com/developing-ar/vehicle-updates)
```bash
$ git clone https://github.com/developing-ar/vehicle-updates.git
```
`vehicle-lang` is the Python library for running Vehicle commands. To install it:
- Navigate to the `vehicle-python/` directory within the `vehicle-updates` repository.
- Run the following inside of the `vehicle-updates/vehicle-python` directory to install `vehicle-lang`
```bash
$ pip install .
```

### 3. Install `pygments` external language lexer
The external language lexer is used for syntax highlighting Vehicle `(.vcl) files. To install it:
- Navigate to the `pygments/` directory within the `vehicle-specification-editor` repository.
- Run the following in the `pygments/` directory to install the lexer:
```bash
$ pip install .
```

**Note: you must be using a virtual environment to install vehicle-lang from source**

## Running the GUI
Run the file `run.py` to open the GUI
```bash
$ python run.py
```
There are example Vehicle `(.vcl)` specification files in the `vehicle-updates/examples` directory.
To verify the `acasXu` example:
1. Open the `acasXu.vcl` specification file.
2. Load the `acasXu_1_7.onnx` network.
3. Test compilation by clicking the *Compile* button. You should see a set of low-level Marabou Queries in the Output tab.
4. Test verification by clicking the *Verify* button. You should see the verification output in the Output tab.

