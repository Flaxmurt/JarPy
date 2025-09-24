# Jarpy Decompiler & Archiver

A robust Python tool to decompile and archive Java `.jar` files in bulk. It is designed to handle a large number of files efficiently by processing a folder of JARs.

This tool is ideal for reverse-engineering, mod analysis, and preparing large codebases for review or AI model ingestion.

---

## Features

-   **Automatic Decompiler Management**: Automatically downloads and updates to the latest version of the [Vineflower](https://github.com/Vineflower/vineflower) decompiler.
-   **Folder-Based Processing**: Drag a folder containing hundreds of `.jar` files to bypass command-line length limits.
-   **Multiple Processing Modes**:
    1.  **Context Mode**: Decompiles each JAR into a separate folder, combining source files by type into `.txt` files. Ignores binary assets.
    2.  **Direct Mode**: Decompiles each JAR into a separate folder, preserving the original file structure.
    3.  **Combined Context Mode**: Decompiles all JARs and intelligently merges their source code into a single set of `.txt` files, sorted by type. Ideal for analyzing a whole project at once.
-   **Memory Efficient**: "Combined Mode" streams data directly to disk, keeping memory usage low regardless of the number of files.
-   **Dependency Handling**: The `run_jarpy.bat` script automatically checks for and installs the required `requests` Python library.

---

## Requirements

-   **Python 3.7+**: Must be installed and accessible from the command line (`python` and `pip`).
-   **Java Runtime Environment (JRE)**: Required to run the decompiler.
-   **OS**: Tested on Windows. The `run_jarpy.bat` script is Windows-specific.

---

## Usage

1.  **Place Files**: Ensure `jarpy.py` and `run_jarpy.bat` are in the same directory.
2.  **Prepare JARs**: Put all the `.jar` files you want to process into a single folder.
3.  **Run**: Drag and drop that folder onto the `run_jarpy.bat` file.
4.  **Select Mode**: Choose one of the processing modes from the on-screen menu.

The script will begin processing, and all output will be placed in `_decompiled_*` folders created in the same directory as the script.

---

## Use Cases

-   **AI/LLM Data Preparation**: Decompile an entire modpack and merge the source code into a single dataset, perfect for analysis by a Large Language Model.
-   **Bulk Security Auditing**: Quickly search the combined source code of hundreds of JARs for vulnerabilities or deprecated code.
-   **Asset Extraction**: Use "Direct Mode" to extract all resources (images, sounds, configs) from an application.
-   **Reverse-Engineering**: Analyze the mechanics of a complex Java application or library, even without access to the original source code.

---

## Getting Help

If you encounter a bug or have a feature request, please [open an issue](https://github.com/Flaxmurt/Jarpy/issues) on the GitHub repository.

---

## Contributing

Contributions are welcome. Please read the `CONTRIBUTING.md` file for guidelines on how to submit pull requests.