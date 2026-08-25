# AI-Assisted Resume Portfolio Generator

A Python application that converts plain text resumes into professional, responsive portfolio websites using the Gemini API and structured JSON schemas.

## Features
- **Clean Pipeline**: Automated cleaning and formatting of text input resumes.
- **Structured Output**: Employs Pydantic schemas via the modern `google-genai` SDK to guarantee robust JSON responses without extraction parser errors.
- **Premium Styling**: Beautiful light/dark mode glassmorphism layout with CSS variables, modern custom layouts, timeline elements, and responsive designs.
- **Responsible AI**: Designed with privacy prompts and strict guidelines to prevent hallucinations.

---

## Technical Architecture & Workflow
1. **Input**: Reads raw resume content from `resume.txt`.
2. **Sanitization**: Checks text validity, enforces length thresholds, and collapses whitespace.
3. **Structured Extraction**: Prompts the Gemini model (`gemini-2.5-flash`) using a strict JSON schema. The model extracts details and aligns them to a Pydantic structure.
4. **Jinja2 Rendering**: Compiles data dynamically into a template-driven `template.html`.
5. **Output**: Automatically outputs `portfolio.html` styled by `style.css` in the local directory.

---

## Setup & Running

### Prerequisites
- Python 3.10+,
- A Google Gemini API Key (obtained from [Google AI Studio](https://aistudio.google.com/))

### Installation
1. Clone this repository to your local machine:
   ```bash
   git clone <repository-url>
   cd resume-portfolio-generator
   ```

2. Create a virtual environment and activate it:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in your Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```

### Run the Application
1. Place your resume text in `resume.txt` (a sample is provided for testing).
2. Execute the python script:
   ```bash
   python main.py
   ```
3. Open `portfolio.html` in your web browser to view your brand new portfolio!

---

## Prompt Design
The prompt used inside `main.py` is carefully engineered to guarantee accuracy and safety:
- **Clean Bordering**: Inputs are bounded with header/footer tags (`--- CLEANED RESUME START ---`) to ensure the model distinguishes prompt instructions from user data.
- **Strict Limitation**: Enforces that the model *must not* assume or invent any skills, titles, company names, dates, or contact links that are not explicitly present.
- **Structured Mapping**: Utilizes a strict Pydantic model (`PortfolioData`) as `response_schema` which forces the API to format its response according to a predetermined typed schema, outputting fields like name, headline, summary, grouped skill categories, experience timeline, and project details.

---

## Responsible AI & Limitations
- **Hallucinations**: While low temperature (`0.1`) and schema restrictions minimize hallucination risks, generative language models may occasionally group skills incorrectly or paraphrase dates. **Always manually verify the output portfolio page against your resume before publishing.**
- **Privacy & Security**: Never include sensitive, non-public details (e.g., social security numbers, bank details, home addresses, or passwords) in your `resume.txt`.
- **API Key Exposure**: Never upload your `.env` file or commit your real API key to GitHub. The project includes a `.gitignore` to prevent accidental commits of keys and generated HTML assets.

---

## AI Usage Log
During development, the following prompts were used with the coding assistant to build this application:

| AI Tool | Prompt/Request | Generated Content | Actions/Corrections Made |
| :--- | :--- | :--- | :--- |
| Gemini 3.5 | Clean the resume.txt input and structure the Pydantic schema for structured output. | Python `main.py` validation logic and Pydantic fields. | Verified variable compatibility with `google-genai` types. |
| Gemini 3.5 | Create a glassmorphism portfolio template and CSS with dark mode toggle. | Responsive `template.html` and `style.css`. | Adapted SVG icons, structured Jinja2 loops for list items, and aligned CSS custom variables. |

---

## Mandatory Test Cases
To verify code correctness, the application was tested with the following inputs:

| Test Case | Inputs / Scenario | Expected Behaviour | Result |
| :--- | :--- | :--- | :--- |
| Missing `resume.txt` | File deleted or renamed. | Graceful error message printed: `Error: Input file 'resume.txt' is missing...` | Pass |
| Empty / Short Resume | Empty file or < 50 chars. | Graceful rejection message printed. | Pass |
| Missing API Key | `GEMINI_API_KEY` empty/missing from `.env`. | Configurations error showing setup guidelines. | Pass |
| Valid Run | Complete resume provided. | Compiles `portfolio.html` without warnings. | Pass |
Contributed by Krish Agrawal