import os
import zipfile
from pathlib import Path

def bundle_industrial():
    """
    Creates a professional, industrial-grade deployment package.
    Bundles TS build, Python brain, and Expert modules.
    """
    output_filename = "waseem_brain_v1.0_industrial.zip"
    # Ensure dist is fresh
    dirs_to_include = ["dist", "brain", "experts", "scripts", "interface", "router-daemon", "docs"]
    files_to_include = ["package.json", "docker-compose.yml", "waseem.manifest.json", "README.md", "pyproject.toml"]
    
    print(f"Creating Industrial Deployment Package: {output_filename}...")
    
    total_files = 0
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add directories
        for dir_name in dirs_to_include:
            dir_path = Path(dir_name)
            if dir_path.exists():
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        file_path = Path(root) / file
                        # Exclude cache and hidden files
                        if any(x in str(file_path) for x in ["__pycache__", "node_modules", ".git", ".mypy_cache"]):
                            continue
                        zip_file.write(file_path, file_path)
                        total_files += 1
                            
        # Add root files
        for file_name in files_to_include:
            file_path = Path(file_name)
            if file_path.exists():
                zip_file.write(file_path, file_path)
                total_files += 1
                
    print(f"Industrial Deployment Package Created Successfully: {output_filename} ({total_files} files)")

if __name__ == "__main__":
    bundle_industrial()
