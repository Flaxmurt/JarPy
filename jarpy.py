import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Literal, Tuple, Union

import requests

# A set of common binary file extensions to ignore in context mode.
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp',
    '.ogg', '.mp3', '.wav', '.flac',
    '.ttf', '.woff', '.woff2', '.eot',
    '.bin', '.dat', '.class'
}

def setup_logging():
    """Sets up simple logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
    )

def setup_decompiler(script_dir: Path) -> Path | None:
    """
    Downloads the latest full Vineflower decompiler atomically if needed.
    """
    api_url = "https://api.github.com/repos/Vineflower/vineflower/releases/latest"
    logging.info("Checking for the latest decompiler version...")
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        release_data = response.json()
        assets = release_data.get('assets', [])
        # Prioritize the full jar, fallback to any jar if not found.
        asset = next((a for a in assets if a['name'].endswith('.jar') and '-slim' not in a['name']), None)
        if not asset:
            asset = next((a for a in assets if a['name'].endswith('.jar')), None)
        if not asset:
            logging.error("Could not find a .jar file in the latest GitHub release.")
            return None
            
        latest_jar_name, download_url = asset['name'], asset['browser_download_url']
        decompiler_path = script_dir / latest_jar_name
        
        if decompiler_path.exists():
            logging.info(f"Latest decompiler '{latest_jar_name}' is already present.")
            return decompiler_path
        
        for old_jar in script_dir.glob('vineflower-*.jar'):
            old_jar.unlink()

        logging.info(f"Downloading new decompiler '{latest_jar_name}'...")
        temp_download_path = decompiler_path.with_suffix('.jar.part')
        with requests.get(download_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(temp_download_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        temp_download_path.rename(decompiler_path)
        logging.info("Download complete.")
        return decompiler_path
        
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logging.error(f"Failed to check for updates: {e}")
        if 'temp_download_path' in locals() and temp_download_path.exists():
            temp_download_path.unlink()
        existing = next(script_dir.glob('vineflower-*.jar'), None)
        if existing:
            logging.warning(f"Using existing decompiler as a fallback: {existing.name}")
            return existing
        return None

def decompile_jar(jar_path: Path, temp_dir: Path, decompiler_path: Path) -> bool:
    """Decompiles a single .jar file into a temporary directory."""
    logging.info(f"Decompiling '{jar_path.name}'...")
    command = ['java', '-jar', str(decompiler_path), str(jar_path), '--outputdir', str(temp_dir)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        logging.info(f"Successfully decompiled '{jar_path.name}'.")
        return True
    except FileNotFoundError:
        logging.error("Java is not installed or not in your system's PATH.")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Decompiler failed for '{jar_path.name}': {e.stderr}")
        return False

def create_context_files(
    grouped_files: Dict[str, List[Path]], output_path: Path, src_path: Path, max_size_mb: float
) -> List[Path]:
    """Creates context files for a single JAR's contents."""
    context_files = []
    max_size_bytes = max_size_mb * 1024 * 1024
    logging.info(f"Creating context files in '{output_path}'...")

    for ext, files in grouped_files.items():
        if ext in BINARY_EXTENSIONS:
            logging.info(f"  -> Skipping binary file type: {ext}")
            continue

        files.sort()
        part_num, current_size, outfile = 1, 0, None
        base_filename_stem = f"{ext[1:] if ext.startswith('.') else ext}_context"

        for file_path in files:
            try:
                file_size = file_path.stat().st_size
            except FileNotFoundError:
                continue

            if outfile and (current_size + file_size) > max_size_bytes and current_size > 0:
                outfile.close()
                outfile, part_num, current_size = None, part_num + 1, 0

            if outfile is None:
                context_filename = f"{base_filename_stem}_{part_num}.txt"
                context_filepath = output_path / context_filename
                outfile = open(context_filepath, 'w', encoding='utf-8', errors='replace')
                context_files.append(context_filepath)
            
            header = f"\n{'='*25} START: {file_path.relative_to(src_path)} {'='*25}\n\n"
            outfile.write(header)
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                content = file_path.read_text(encoding='latin-1', errors='replace')
            outfile.write(content)
            current_size += file_size
        if outfile:
            outfile.close()
    return context_files

def create_archives(files: List[Path], output_path: Path, chunk_size: int, prefix: str, src_path: Path = None):
    """Zips the provided files into one or more archives."""
    if not files:
        logging.info("No files to archive.")
        return
    num_archives = (len(files) + chunk_size - 1) // chunk_size
    logging.info(f"Creating {num_archives} archive(s)...")
    files.sort()
    for i in range(0, len(files), chunk_size):
        chunk = files[i:i + chunk_size]
        archive_num = (i // chunk_size) + 1
        zip_filename = output_path / f'{prefix}_{archive_num}.zip'
        logging.info(f"Creating '{zip_filename}' with {len(chunk)} files...")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in chunk:
                arcname = file_path.relative_to(src_path) if src_path else file_path.name
                zipf.write(file_path, arcname)
    logging.info(f"Archive creation complete.")

def main(decompiler_path: Path):
    """Main processing logic, runs after setup is confirmed."""
    parser = argparse.ArgumentParser(description="A tool to decompile and archive .jar files.")
    parser.add_argument("input_directory", help="The directory containing .jar files to process.")
    parser.add_argument("--combine", action='store_true', help="Combine all JARs into a single output folder.")
    parser.add_argument("--mode", choices=['direct', 'context'], default='context', help="Archiving mode.")
    parser.add_argument("-s", "--size", type=int, default=10, help="Number of files per ZIP archive.")
    parser.add_argument("--max-size", type=float, default=100.0, help="(Context Mode) Max size of each context file in MB.")

    args = parser.parse_args()
    script_dir = Path(__file__).parent.resolve()
    input_dir = Path(args.input_directory)

    if not input_dir.is_dir():
        logging.error(f"Error: Provided path '{input_dir}' is not a valid directory.")
        return

    jar_files = sorted(list(input_dir.glob('*.jar')))
    if not jar_files:
        logging.warning(f"No .jar files found in '{input_dir}'.")
        return
    
    logging.info(f"Found {len(jar_files)} .jar file(s) to process in '{input_dir.name}'.")

    if args.combine:
        # --- REFACTORED COMBINED MODE (MEMORY EFFICIENT) ---
        output_path = script_dir / f"_decompiled_combined_{input_dir.name}"
        output_path.mkdir(parents=True, exist_ok=True)
        
        open_files = {}
        created_context_files = set()

        try:
            for i, jar_path in enumerate(jar_files):
                logging.info(f"\n--- Processing ({i+1}/{len(jar_files)}) for combined output: {jar_path.name} ---")
                with tempfile.TemporaryDirectory() as temp_dir_str:
                    temp_dir = Path(temp_dir_str)
                    if decompile_jar(jar_path, temp_dir, decompiler_path):
                        current_jar_groups = defaultdict(list)
                        for file_path in temp_dir.rglob('*'):
                            if file_path.is_file():
                                ext = file_path.suffix.lower() or 'no_extension'
                                current_jar_groups[ext].append(file_path)

                        for ext, files in current_jar_groups.items():
                            if ext in BINARY_EXTENSIONS:
                                continue

                            if ext not in open_files:
                                context_filename = f"{(ext[1:] if ext.startswith('.') else ext)}_context_1.txt"
                                context_filepath = output_path / context_filename
                                open_files[ext] = open(context_filepath, 'a', encoding='utf-8', errors='replace')
                                created_context_files.add(context_filepath)
                            
                            handle = open_files[ext]
                            for file_path in sorted(files):
                                header = f"\n{'='*30}\n=== SOURCE JAR: {jar_path.name}\n=== FILE:       {file_path.name}\n{'='*30}\n\n"
                                handle.write(header)
                                try:
                                    content = file_path.read_text(encoding='utf-8')
                                except UnicodeDecodeError:
                                    content = file_path.read_text(encoding='latin-1', errors='replace')
                                handle.write(content)
        finally:
            logging.info("Closing all context files...")
            for handle in open_files.values():
                handle.close()

        create_archives(list(created_context_files), output_path, args.size, "combined_context")

    else: # Individual Mode
        for i, jar_path in enumerate(jar_files):
            logging.info(f"\n--- Processing ({i+1}/{len(jar_files)}) individually: {jar_path.name} ---")
            output_path = script_dir / f"_decompiled_{jar_path.stem}"
            output_path.mkdir(parents=True, exist_ok=True)
            
            with tempfile.TemporaryDirectory() as temp_dir_str:
                temp_dir = Path(temp_dir_str)
                if decompile_jar(jar_path, temp_dir, decompiler_path):
                    if args.mode == 'context':
                        grouped_files = defaultdict(list)
                        for file_path in temp_dir.rglob('*'):
                             if file_path.is_file():
                                ext = file_path.suffix.lower() or 'no_extension'
                                grouped_files[ext].append(file_path)
                        
                        context_files = create_context_files(grouped_files, output_path, temp_dir, args.max_size)
                        create_archives(context_files, output_path, args.size, f"context_{jar_path.stem}")
                    
                    elif args.mode == 'direct':
                        all_files = [p for p in temp_dir.rglob('*') if p.is_file()]
                        create_archives(all_files, output_path, args.size, f"direct_{jar_path.stem}", src_path=temp_dir)

    logging.info(f"\n--- All jobs complete. ---")
    input("Press Enter to exit...")

def cli():
    """CLI entry point. Handles setup before calling main logic."""
    setup_logging()
    script_dir = Path(__file__).parent.resolve()
    decompiler_path = setup_decompiler(script_dir)
    
    if decompiler_path:
        main(decompiler_path)
    else:
        logging.error("Could not find or download the decompiler. Exiting.")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    cli()

