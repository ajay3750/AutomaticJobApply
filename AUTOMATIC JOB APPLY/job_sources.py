import re
from html import unescape

import requests
import streamlit as st

REMOTIVE_API = "https://remotive.com/api/remote-jobs"


def clean_description(description):
    description = re.sub(r"<[^>]+>", " ", description or "")
    description = unescape(description)
    return re.sub(r"\s+", " ", description).strip()


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_remotive_jobs(search_term=""):
    params = {"limit": 100}

    if search_term.strip():
        params["search"] = search_term.strip()

    response = requests.get(
        REMOTIVE_API,
        params=params,
        timeout=30,
        headers={"User-Agent": "AutoJobApply/1.0"},
    )
    response.raise_for_status()

    results = []

    for job in response.json().get("jobs", []):
        results.append({
            "id": str(job.get("id", "")),
            "company": job.get("company_name") or "Unknown",
            "title": job.get("title") or "Untitled",
            "location": job.get("candidate_required_location") or "Remote",
            "description": clean_description(job.get("description", "")),
            "url": job.get("url", ""),
            "date": job.get("publication_date", ""),
            "category": job.get("category") or "Other",
            "job_type": job.get("job_type") or "Not specified",
            "salary": job.get("salary") or "Not specified",
            "source": "Remotive",
        })

    return results