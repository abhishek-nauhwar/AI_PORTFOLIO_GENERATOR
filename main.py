import os
import sys
import json
import re
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader

# Try importing google-genai, handle import failure
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: The 'google-genai' package is not installed. Run 'pip install -r requirements.txt' first.")
    sys.exit(1)


# --- Define Pydantic Schema for Structured Output ---

class SkillCategory(BaseModel):
    category: str = Field(description="The category of skills (e.g., 'Languages', 'Frameworks & Libraries', 'Databases & Tools')")
    items: List[str] = Field(description="List of specific skills within this category")

class EducationItem(BaseModel):
    institution: str = Field(description="Name of the school, university, or educational institution")
    degree: str = Field(description="Degree or qualification earned (e.g., 'Bachelor of Science')")
    major: str = Field(description="Field of study or major (e.g., 'Computer Science')")
    gpa: Optional[str] = Field(None, description="GPA if explicitly provided in the resume (leave null if not present)")
    start_date: str = Field(description="Start year or month/year")
    end_date: str = Field(description="End year or month/year (or 'Present')")

class ExperienceItem(BaseModel):
    company: str = Field(description="Name of the company or organization")
    position: str = Field(description="Job title or position")
    location: Optional[str] = Field(None, description="Location of employment (e.g., 'San Francisco, CA')")
    start_date: str = Field(description="Start date or year")
    end_date: str = Field(description="End date or year (or 'Present')")
    description: List[str] = Field(description="Bullet points describing responsibilities, projects, and achievements")

class ProjectItem(BaseModel):
    title: str = Field(description="Name of the project")
    description: str = Field(description="Short description of what the project does and accomplishes")
    technologies: List[str] = Field(description="List of key tools, libraries, or languages used in this project")
    link: Optional[str] = Field(None, description="URL or repository link of the project if present")

class ContactDetails(BaseModel):
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL or username")
    github: Optional[str] = Field(None, description="GitHub profile URL or username")
    website: Optional[str] = Field(None, description="Personal website or portfolio URL")
    location: Optional[str] = Field(None, description="Current city and state/country")

class PortfolioData(BaseModel):
    name: str = Field(description="Candidate's full name")
    headline: str = Field(description="Short, professional title or identity (e.g., 'Full-Stack Software Engineer')")
    summary: str = Field(description="A concise professional summary of the candidate, summarizing their experience and profile (2-3 sentences max)")
    skills: List[SkillCategory] = Field(description="Grouped list of technical/professional skills")
    education: List[EducationItem] = Field(description="Educational history")
    experience: List[ExperienceItem] = Field(description="Professional work history")
    projects: List[ProjectItem] = Field(description="Projects worked on")
    achievements: List[str] = Field(description="List of awards, certifications, or notable accomplishments mentioned")
    contact: ContactDetails = Field(description="Contact info and online profile links")


# --- Pipeline Functions ---

def clean_text(text: str) -> str:
    """Cleans and normalizes resume text before AI processing."""

    # Normalize Windows/Mac line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove trailing spaces from every line
    lines = [line.strip() for line in text.split("\n")]

    # Remove unnecessary empty lines
    cleaned_lines = []
    previous_blank = False

    for line in lines:
        if not line:
            if not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
        else:
            cleaned_lines.append(line)
            previous_blank = False

    text = "\n".join(cleaned_lines)

    # Replace multiple spaces/tabs inside text with one space
    text = re.sub(r"[ \t]+", " ", text)

    # Keep paragraph separation clean
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def load_resume(filepath: str) -> str:
    """Reads, validates, and cleans the resume input file."""

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Input file '{filepath}' is missing. "
            "Please create it and add your resume content."
        )

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        raise ValueError(
            f"Unable to read '{filepath}'. "
            "Please make sure the file is saved using UTF-8 encoding."
        )

    if not content.strip():
        raise ValueError(
            f"The resume file '{filepath}' is empty."
        )

    original_length = len(content)

    cleaned = clean_text(content)

    # Basic content validation
    if len(cleaned) < 50:
        raise ValueError(
            f"The content of '{filepath}' is too short. "
            "A minimum of 50 characters is required."
        )

    # Prevent meaningless repeated-character input
    alphanumeric_chars = re.sub(r"[^a-zA-Z0-9]", "", cleaned)

    if len(set(alphanumeric_chars.lower())) < 5:
        raise ValueError(
            "The resume content does not appear to contain meaningful text."
        )

    print(f"Original resume length: {original_length} characters")
    print(f"Cleaned resume length: {len(cleaned)} characters")
    print(f"Resume lines processed: {len(cleaned.splitlines())}")

    return cleaned

def resolve_schema_refs(schema: dict) -> dict:
    """Recursively resolves and inlines $ref keys from $defs in a JSON schema, and simplifies anyOf."""
    defs = schema.get("$defs", {})
    
    def resolve(node, key_name=None):
        if isinstance(node, dict):
            # Simplify anyOf (e.g. [type: string, type: null] -> type: string)
            if "anyOf" in node:
                non_null_items = [item for item in node["anyOf"] if isinstance(item, dict) and item.get("type") != "null"]
                if non_null_items:
                    resolved = resolve(non_null_items[0], key_name)
                    for k, v in node.items():
                        if k != "anyOf" and k not in resolved:
                            resolved[k] = v
                    node = resolved
                else:
                    node = resolve(node["anyOf"][0], key_name)

            if "$ref" in node:
                ref_path = node["$ref"]
                if ref_path.startswith("#/$defs/"):
                    def_name = ref_path.split("/")[-1]
                    resolved_def = resolve(defs[def_name].copy(), key_name)
                    return resolved_def

            result_dict = {}
            for k, v in node.items():
                if k == "$defs":
                    continue
                if k == "title" and key_name != "properties":
                    continue
                if k == "default" and key_name != "properties":
                    continue
                result_dict[k] = resolve(v, key_name=k)
            return result_dict

        elif isinstance(node, list):
            return [resolve(item, key_name) for item in node]
        return node

    result = resolve(schema)
    if "$defs" in result:
        del result["$defs"]
    return result

def fetch_portfolio_data(resume_text: str, api_key: Optional[str] = None) -> PortfolioData:
    """Sends the resume to Gemini and requests structured JSON mapping to the Pydantic schema."""
    # Ensure API Key exists
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Please create a '.env' file in this directory and add: GEMINI_API_KEY=your_key")

    print("Initializing Gemini Client and sending request...")
    try:
        # Initialise Client
        client = genai.Client(api_key=api_key)
        
        # Build strict prompt
        prompt = (
            "Analyze the following resume and convert it into a structured portfolio JSON object.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Extract ONLY information that is explicitly stated or directly supported by the resume text.\n"
            "2. Do NOT invent, assume, or hallucinate any skills, jobs, companies, projects, dates, achievements, credentials, or links.\n"
            "3. If any field or section is not mentioned in the resume, leave it empty or null in the JSON.\n"
            "4. Keep the professional summary concise and strictly factual (2-3 sentences maximum).\n"
            "5. Reorganize skills into appropriate categories (e.g. 'Languages', 'Frameworks', 'Tools') to look highly professional.\n\n"
            f"--- CLEANED RESUME START ---\n{resume_text}\n--- CLEANED RESUME END ---\n"
        )
        
        # Generate and inline the schema to comply with Gemini API requirements
        raw_schema = PortfolioData.model_json_schema()
        inlined_schema = resolve_schema_refs(raw_schema)
        
        import time
        max_retries = 5
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                # Request content generation using gemini-3.5-flash with structured schema
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=inlined_schema,
                        temperature=0.1,  # Low temperature to prevent hallucinations
                    ),
                )
                break
            except Exception as e:
                # If it's a 503 error, retry
                if "503" in str(e) and attempt < max_retries - 1:
                    print(f"Gemini API is busy (503). Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise e
        
        # Extract and parse the output
        response_text = response.text
        if not response_text:
            raise RuntimeError("Received empty response from Gemini API.")
            
        data = PortfolioData.model_validate_json(response_text)
        return data

    except Exception as e:
        raise RuntimeError(f"API call or JSON parsing failed. Details: {e}")

def render_portfolio(data: PortfolioData, template_path: str) -> str:
    """Renders the HTML portfolio page using the parsed data and template.html and returns it as a string."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file '{template_path}' is missing.")
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_path)
    return template.render(data.model_dump())

def generate_portfolio(data: PortfolioData, template_path: str, output_path: str):
    """Renders the HTML portfolio page and writes it to the output file."""
    html_content = render_portfolio(data, template_path)
    print(f"Writing output portfolio to '{output_path}'...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    # Load environment variables from .env
    load_dotenv()

    # Define paths
    resume_file = "resume.txt"
    template_file = "template.html"
    output_file = "portfolio.html"

    try:
        # Step 1: Load and clean resume
        print(f"Step 1: Reading and validating '{resume_file}'...")
        resume_text = load_resume(resume_file)
        print(f"Success: Read and cleaned {len(resume_text)} characters of resume text.\n")

        # Step 2: Fetch structured data from Gemini
        print("Step 2: Sending data to Gemini API...")
        portfolio_data = fetch_portfolio_data(resume_text)
        print("Success: Received structured, validated data from Gemini.\n")

        # Step 3: Generate HTML portfolio
        print("Step 3: Compiling portfolio HTML webpage...")
        generate_portfolio(portfolio_data, template_file, output_file)
        print("\n" + "="*50)
        print(f"SUCCESS: Portfolio generated successfully!")
        print(f"You can now open '{output_file}' in your web browser.")
        print("="*50)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
