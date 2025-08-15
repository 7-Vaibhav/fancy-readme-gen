import os
import zipfile
import tempfile
import shutil
import stat
import re
import time
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env")

client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper: Remove readonly files (Windows fix)
def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# Helper: Extract ZIP
def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

# Helper: Clone GitHub repo
def clone_github_repo(repo_url, dest_dir):
    os.system(f"git clone --depth 1 {repo_url} {dest_dir}")

# Helper: Read project files
def read_project_files(project_path):
    content = ""
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith((".md", ".py", ".js", ".ts", ".jsx", ".java", ".html", ".css", ".json")):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content += f"\n---\n# File: {file_path}\n{f.read()}"
                except:
                    pass
    return content

# Helper: Extract repo info from URL
def extract_repo_info(repo_url: str):
    pattern = r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$"
    match = re.search(pattern, repo_url.strip())
    if match:
        return match.group(1), match.group(2), repo_url.strip()
    return None, None, repo_url.strip()

# Helper: Generate fancy README
def generate_fancy_readme(project_content, repo_name=None, author_name=None, repo_url=None):
    fancy_prompt = f"""
Generate ONLY a fully polished README.md for GitHub in valid markdown + minimal HTML.
It must look like a top-starred open-source project page.

✨ Style Requirements:
1️⃣ Title:
- BIG, centered title: either <h1 align="center"> or markdown heading with an emoji.
- Below title: one-line bold tagline, centered, with 1-2 emojis.
- Immediately after tagline: Shields.io badges in one line (GitHub stars, forks, issues, license) using repo name/author if available.

2️⃣ Section Formatting:
- **Every single section must be wrapped with horizontal separators**: add `---` on a separate line above AND below the section content (including before the first section and after the last).
- Section headers must use emojis:
  - 🚀 Features
  - 📦 Installation
  - ⚙️ Usage
  - 🤝 Contributing
  - 📜 License

3️⃣ Features Section:
- Always a markdown unordered list.
- Each feature starts with ✅, 🔥, or ⚡ emoji, then **bold title**, colon, short description.
- Each feature is its own bullet, no paragraphs.

4️⃣ Usage Section:
- Use syntax-highlighted triple backticks for commands.
- If commands exist in repo files, list each command separately with a short description above it.

5️⃣ Other Rules:
- Use tables only for structured data (e.g., feature comparisons).
- If repo has images/screenshots, show them centered using markdown image links or <img>.
- End with a call-to-action: "⭐ Star this repo if you like it!" and "Made with ❤️ by {author_name or 'the team'}".
- No placeholders or fake info. Omit sections with no data.

📌 Context:
Repository name: {repo_name or 'Unknown Project'}
Author: {author_name or 'Unknown Author'}
Repository URL: {repo_url or 'Not provided'}
"""

    prompt = f"""
{fancy_prompt}

Repository content for analysis:
{project_content[:12000]}
"""

    chat_completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
    )

    return chat_completion.choices[0].message.content

@app.post("/generate-readme")
async def generate_readme(file: UploadFile = File(None), repo_url: str = Form(None)):
    temp_dir = tempfile.mkdtemp()
    try:
        project_path = None
        author_name = None
        repo_name = None
        final_repo_url = None

        if repo_url:
            # Extract repo details
            author_name, repo_name, final_repo_url = extract_repo_info(repo_url)
            # Clone repo
            repo_dir = os.path.join(temp_dir, "repo")
            clone_github_repo(repo_url, repo_dir)
            project_path = repo_dir

        elif file:
            # Save and extract ZIP
            zip_path = os.path.join(temp_dir, file.filename)
            with open(zip_path, "wb") as buffer:
                buffer.write(await file.read())

            if not zipfile.is_zipfile(zip_path):
                return {"error": "Uploaded file is not a valid ZIP"}

            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            extract_zip(zip_path, extract_dir)
            project_path = extract_dir

            # Guess repo name from folder name
            try:
                first_folder = os.listdir(extract_dir)[0]
                repo_name = first_folder
            except:
                repo_name = "Unknown Project"
            author_name = "Unknown Author"

        else:
            return {"error": "No file or repo URL provided"}

        # Read files
        project_content = read_project_files(project_path)

        # Generate README
        readme_content = generate_fancy_readme(project_content, repo_name, author_name, final_repo_url)

        return {"readme": readme_content}

    except zipfile.BadZipFile:
        return {"error": "Uploaded file is not a valid ZIP"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        shutil.rmtree(temp_dir, onerror=remove_readonly)

@app.get("/progress-stream")
async def progress_stream():
    def event_stream():
        steps = [
            "📂 Processing upload / cloning repo...",
            "📄 Reading project files...",
            "🤖 Asking AI to write README...",
            "✅ README ready!"
        ]
        for step in steps:
            yield f"data: {step}\n\n"
            time.sleep(1)  # simulate processing
    return StreamingResponse(event_stream(), media_type="text/event-stream")