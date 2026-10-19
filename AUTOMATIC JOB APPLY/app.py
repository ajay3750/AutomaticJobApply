import sqlite3
from pathlib import Path

import fitz
import pandas as pd
import requests
import streamlit as st

from job_sources import fetch_remotive_jobs
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="AutoJobApply",
    page_icon="💼",
    layout="wide",
)

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "jobs.db"


# =====================================================
# DATABASE
# =====================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT,
                company TEXT,
                title TEXT,
                location TEXT,
                description TEXT,
                url TEXT,
                date TEXT,
                category TEXT,
                job_type TEXT,
                salary TEXT,
                source TEXT,
                status TEXT DEFAULT 'Saved',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Upgrade old databases without deleting data.
        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(jobs)")
        }

        required = {
            "source_id": "TEXT",
            "company": "TEXT",
            "title": "TEXT",
            "location": "TEXT",
            "description": "TEXT",
            "url": "TEXT",
            "date": "TEXT",
            "category": "TEXT",
            "job_type": "TEXT",
            "salary": "TEXT",
            "source": "TEXT",
            "status": "TEXT DEFAULT 'Saved'",
            "notes": "TEXT DEFAULT ''",
            "created_at": "TIMESTAMP",
        }

        for column, definition in required.items():
            if column not in existing:
                conn.execute(
                    f'ALTER TABLE jobs ADD COLUMN "{column}" {definition}'
                )

        conn.commit()


def save_job(job):
    source_id = str(
        job.get("id")
        or job.get("url")
        or f"{job.get('company')}-{job.get('title')}"
    )

    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id FROM jobs
            WHERE source_id = ? OR (url = ? AND url != '')
            LIMIT 1
            """,
            (source_id, job.get("url", "")),
        ).fetchone()

        if existing:
            return False

        conn.execute("""
            INSERT INTO jobs (
                source_id, company, title, location,
                description, url, date, category,
                job_type, salary, source, status, notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            source_id,
            job.get("company", "Unknown"),
            job.get("title", "Untitled"),
            job.get("location", ""),
            job.get("description", ""),
            job.get("url", ""),
            job.get("date", ""),
            job.get("category", ""),
            job.get("job_type", ""),
            job.get("salary", ""),
            job.get("source", "Manual"),
            job.get("status", "Saved"),
            job.get("notes", ""),
        ))

        conn.commit()

    return True


def get_jobs():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM jobs ORDER BY id DESC",
            conn,
        )


def update_job_status(job_id, status, notes):
    with get_connection() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, notes = ? WHERE id = ?",
            (status, notes, int(job_id)),
        )
        conn.commit()


initialize_db()


# =====================================================
# RESUME MATCHING
# =====================================================

def extract_resume_text(uploaded_file):
    if uploaded_file is None:
        return ""

    if uploaded_file.name.lower().endswith(".pdf"):
        document = fitz.open(
            stream=uploaded_file.getvalue(),
            filetype="pdf",
        )
        try:
            return "\n".join(
                page.get_text() for page in document
            )
        finally:
            document.close()

    if uploaded_file.name.lower().endswith(".txt"):
        return uploaded_file.getvalue().decode(
            "utf-8", errors="ignore"
        )

    return ""


def calculate_match(resume_text, job_description):
    if not resume_text.strip() or not job_description.strip():
        return 0.0

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
        )

        vectors = vectorizer.fit_transform([
            resume_text,
            job_description,
        ])

        similarity = cosine_similarity(
            vectors[0:1],
            vectors[1:2],
        )[0][0]

        return round(float(similarity) * 100, 1)

    except ValueError:
        return 0.0


# =====================================================
# PAGE HEADER
# =====================================================

st.title("💼 AutoJobApply")
st.caption(
    "Discover jobs, match your resume, and track applications."
)


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.header("Resume Matcher")

    resume_file = st.file_uploader(
        "Upload your resume",
        type=["pdf", "txt"],
    )

    resume_text = extract_resume_text(resume_file)

    if resume_text:
        st.success("Resume uploaded successfully.")
        word_count = len(resume_text.split())
        st.metric("Words extracted", word_count)

        with st.expander("View extracted resume text", expanded=True):
            st.text_area(
                "Text extracted from your resume",
                value=resume_text,
                height=320,
                disabled=True,
                key="extracted_resume_preview",
            )

        st.download_button(
            "Download extracted text (.txt)",
            data=resume_text,
            file_name="extracted_resume.txt",
            mime="text/plain",
            use_container_width=True,
        )

        st.caption(
            "This is the text read from your PDF/TXT file. "
            "Scanned PDFs may require OCR before their text can be extracted."
        )
    else:
        st.info(
            "Upload your resume to extract its text and compare it "
            "with job descriptions."
        )


# =====================================================
# TABS
# =====================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Job Dashboard",
    "➕ Add a Job",
    "📋 Application Tracker",
    "🔎 Find Jobs",
    "🌐 Job Portals",
])


# =====================================================
# TAB 1: DASHBOARD
# =====================================================

with tab1:
    st.header("Job Dashboard")

    df = get_jobs()

    total = len(df)
    applied = int((df["status"] == "Applied").sum())
    interviews = int((df["status"] == "Interview").sum())
    offers = int((df["status"] == "Offer").sum())

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Saved Jobs", total)
    col2.metric("Applied", applied)
    col3.metric("Interviews", interviews)
    col4.metric("Offers", offers)

    st.subheader("Your Jobs")

    if df.empty:
        st.info("No jobs saved yet.")
    else:
        st.dataframe(
            df[
                ["company", "title", "location", "source", "status"]
            ],
            use_container_width=True,
            hide_index=True,
        )


# =====================================================
# TAB 2: ADD JOB
# =====================================================

with tab2:
    st.header("Add a Job")

    with st.form("add_job_form"):
        company = st.text_input("Company")
        title = st.text_input("Job Title")
        location = st.text_input("Location")
        url = st.text_input("Job URL")
        description = st.text_area("Job Description")

        submitted = st.form_submit_button("Save Job")

    if submitted:
        if not company.strip() or not title.strip():
            st.error("Company and job title are required.")
        else:
            saved = save_job({
                "company": company.strip(),
                "title": title.strip(),
                "location": location.strip(),
                "url": url.strip(),
                "description": description.strip(),
                "source": "Manual",
            })

            if saved:
                st.success("Job saved successfully.")
            else:
                st.warning("This job is already saved.")


# =====================================================
# TAB 3: APPLICATION TRACKER
# =====================================================

with tab3:
    st.header("Application Tracker")

    df = get_jobs()

    if df.empty:
        st.info("Save a job to begin tracking.")
    else:
        options = {
            f"{row['company']} — {row['title']} (#{row['id']})":
                int(row["id"])
            for _, row in df.iterrows()
        }

        selected = st.selectbox(
            "Select Job",
            list(options.keys()),
        )

        selected_id = options[selected]

        job = df[df["id"] == selected_id].iloc[0]

        statuses = [
            "Saved",
            "Applied",
            "Interview",
            "Offer",
            "Rejected",
        ]

        current_status = job["status"]

        if current_status not in statuses:
            current_status = "Saved"

        status = st.selectbox(
            "Application Status",
            statuses,
            index=statuses.index(current_status),
        )

        notes = st.text_area(
            "Notes",
            value=job["notes"] if pd.notna(job["notes"]) else "",
        )

        if st.button("Update Application"):
            update_job_status(
                selected_id,
                status,
                notes,
            )
            st.success("Application updated.")
            st.rerun()

        st.subheader("All Applications")

        st.dataframe(
            df[
                [
                    "company",
                    "title",
                    "location",
                    "status",
                    "source",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# =====================================================
# TAB 4: FIND JOBS
# =====================================================

with tab4:
    st.header("Find Jobs")

    st.write(
        "Search remote job listings from Remotive."
    )

    with st.form("search_jobs_form"):
        search_term = st.text_input(
            "Search keyword",
            value="data analyst",
        )

        location_filter = st.selectbox(
            "Location",
            [
                "Any location",
                "India",
                "Worldwide",
            ],
        )

        role_filter = st.selectbox(
            "Role Category",
            [
                "All relevant roles",
                "Data Analyst",
                "Data Science",
                "Software / IT",
            ],
        )

        search_clicked = st.form_submit_button(
            "Search Jobs"
        )

    if search_clicked:
        st.session_state["search_term"] = search_term
        st.session_state["location_filter"] = location_filter
        st.session_state["role_filter"] = role_filter

    active_search = st.session_state.get(
        "search_term",
        "data analyst",
    )

    active_location = st.session_state.get(
        "location_filter",
        "Any location",
    )

    active_role = st.session_state.get(
        "role_filter",
        "All relevant roles",
    )

    if st.button("Refresh Listings"):
        fetch_remotive_jobs.clear()
        st.rerun()

    try:
        with st.spinner("Searching jobs..."):
            jobs = fetch_remotive_jobs(active_search)

        filtered_jobs = []

        for job in jobs:
            location = job["location"].lower()
            title = job["title"].lower()
            category = job["category"].lower()

            if active_location == "India":
                allowed = [
                    "india",
                    "worldwide",
                    "anywhere",
                    "global",
                    "asia",
                    "apac",
                ]

                if not any(word in location for word in allowed):
                    continue

            elif active_location == "Worldwide":
                allowed = [
                    "worldwide",
                    "anywhere",
                    "global",
                ]

                if not any(word in location for word in allowed):
                    continue

            if active_role == "Data Analyst":
                if not any(
                    term in title or term in category
                    for term in [
                        "analyst",
                        "analytics",
                        "business intelligence",
                    ]
                ):
                    continue

            elif active_role == "Data Science":
                if not any(
                    term in title or term in category
                    for term in [
                        "data scientist",
                        "data science",
                        "machine learning",
                    ]
                ):
                    continue

            elif active_role == "Software / IT":
                if not any(
                    term in title or term in category
                    for term in [
                        "software",
                        "developer",
                        "engineer",
                        "it",
                    ]
                ):
                    continue

            filtered_jobs.append(job)

        st.info(
            f"API results: {len(jobs)} | "
            f"Matching jobs: {len(filtered_jobs)}"
        )

        if not filtered_jobs:
            st.warning(
                "No matching listings found. Try searching "
                "'analyst' or 'SQL' with Any location."
            )

        for index, job in enumerate(filtered_jobs):
            with st.container(border=True):
                st.subheader(job["title"])

                st.write(
                    f"**Company:** {job['company']}"
                )

                st.write(
                    f"**Location:** {job['location']}"
                )

                st.write(
                    f"**Category:** {job['category']}"
                )

                st.write(
                    f"**Salary:** {job['salary']}"
                )

                if resume_text:
                    score = calculate_match(
                        resume_text,
                        job["description"],
                    )

                    st.progress(
                        min(score / 100, 1.0),
                        text=f"Resume similarity: {score}%",
                    )

                with st.expander("Job Description"):
                    st.write(job["description"])

                if job["url"]:
                    st.markdown(
                        f"[View original job on Remotive]({job['url']})"
                    )

                if st.button(
                    "Save Job",
                    key=f"save_{job['id']}_{index}",
                ):
                    saved = save_job(job)

                    if saved:
                        st.success("Job saved.")
                    else:
                        st.warning("Job already exists.")

        st.caption(
            "Source: Remotive. Verify location eligibility "
            "and availability on the original listing. "
            "Resume similarity does not predict hiring chances."
        )

    except requests.RequestException as error:
        st.error("Unable to connect to the job API.")
        st.code(str(error))

    except (KeyError, ValueError) as error:
        st.error("Unexpected job data received.")
        st.code(str(error))


# =====================================================
# TAB 5: JOB PORTALS
# =====================================================

from urllib.parse import quote_plus

with tab5:
    st.header("🌐 Search by Job Portal")
    st.write(
        "Choose a portal, enter your job interest and location, "
        "then search. In-app job cards are available for connected sources."
    )

    with st.form("portal_search_form"):
        selected_portal = st.selectbox(
            "Select job portal",
            [
                "Remotive",
                "LinkedIn Jobs",
                "Naukri.com",
                "Indeed",
                "Foundit",
                "Glassdoor",
            ],
        )

        portal_keyword = st.text_input(
            "Job title or keyword",
            value="Data Analyst",
            placeholder="e.g. Data Analyst, SQL Developer",
        )

        portal_location = st.text_input(
            "Location",
            value="India",
            placeholder="e.g. India, Noida, Bengaluru",
        )

        search_clicked = st.form_submit_button("Search Jobs")

    if search_clicked:
        st.session_state["selected_portal"] = selected_portal
        st.session_state["portal_keyword"] = portal_keyword.strip()
        st.session_state["portal_location"] = portal_location.strip()

    selected_portal = st.session_state.get(
        "selected_portal", "Remotive"
    )
    keyword = st.session_state.get("portal_keyword", "Data Analyst")
    location = st.session_state.get("portal_location", "India")

    if keyword:
        q = quote_plus(keyword)
        loc = quote_plus(location)
        keyword_slug = "-".join(keyword.lower().split())
        location_slug = "-".join(location.lower().split())

        portal_urls = {
            "LinkedIn Jobs": (
                "https://www.linkedin.com/jobs/search/"
                f"?keywords={q}&location={loc}"
            ),
            "Naukri.com": (
                f"https://www.naukri.com/{keyword_slug}-jobs"
                + (f"-in-{location_slug}" if location_slug else "")
            ),
            "Indeed": (
                f"https://in.indeed.com/jobs?q={q}"
                + (f"&l={loc}" if loc else "")
            ),
            "Foundit": (
                "https://www.foundit.in/srp/results"
                f"?query={q}" + (f"&locations={loc}" if loc else "")
            ),
            "Glassdoor": (
                "https://www.glassdoor.co.in/Job/jobs.htm"
                f"?sc.keyword={q}" + (f"&locKeyword={loc}" if loc else "")
            ),
        }

        if selected_portal == "Remotive":
            st.subheader(f"Remotive listings for {keyword}")
            try:
                with st.spinner("Searching Remotive listings..."):
                    portal_jobs = fetch_remotive_jobs(keyword)

                matching_jobs = []
                for job in portal_jobs:
                    job_location = (
                        job.get("location") or "Remote"
                    ).lower()

                    # Only apply the location filter when the user specified one.
                    if location.strip():
                        requested = location.strip().lower()
                        remote_terms = [
                            "worldwide", "anywhere", "global",
                            "remote", "all locations",
                        ]
                        if requested in {"india", "in"}:
                            allowed = [
                                "india", "worldwide", "anywhere",
                                "global", "asia", "apac",
                            ]
                            if not any(x in job_location for x in allowed):
                                continue
                        elif requested not in {"any", "anywhere", "any location"}:
                            # Keep explicit location filtering conservative.
                            if requested not in job_location and not any(
                                term in job_location for term in remote_terms
                            ):
                                continue

                    matching_jobs.append(job)

                st.caption(
                    f"{len(matching_jobs)} matching listings found."
                )

                if not matching_jobs:
                    st.warning(
                        "No matching jobs found. Try a broader keyword "
                        "or enter India/Worldwide as the location."
                    )

                for index, job in enumerate(matching_jobs):
                    with st.container(border=True):
                        st.subheader(job.get("title", "Untitled"))
                        st.write(
                            f"**Company:** {job.get('company', 'Unknown')}"
                        )
                        st.write(
                            f"**Location:** {job.get('location', 'Remote')}"
                        )
                        st.write(
                            f"**Category:** {job.get('category', 'Other')}"
                        )
                        st.write(
                            f"**Job type:** {job.get('job_type', 'Not specified')}"
                        )
                        st.write(
                            f"**Salary:** {job.get('salary', 'Not specified')}"
                        )

                        if resume_text:
                            score = calculate_match(
                                resume_text,
                                job.get("description", ""),
                            )
                            st.progress(
                                min(score / 100, 1.0),
                                text=f"Resume text similarity: {score}%",
                            )

                        with st.expander("View job description"):
                            st.write(
                                job.get("description")
                                or "No description provided."
                            )

                        if job.get("url"):
                            st.link_button(
                                "Open original listing",
                                job["url"],
                            )

                        if st.button(
                            "Save to Application Tracker",
                            key=f"portal_save_{job.get('id', index)}_{index}",
                        ):
                            if save_job(job):
                                st.success("Job saved to your tracker.")
                            else:
                                st.info("This job is already saved.")

            except requests.RequestException as error:
                st.error(
                    "Could not fetch Remotive listings. Check your internet "
                    "connection and try again."
                )
                st.caption(str(error))
            except (KeyError, ValueError) as error:
                st.error("Remotive returned unexpected job data.")
                st.caption(str(error))

        else:
            st.subheader(f"{selected_portal} — {keyword}")
            st.warning(
                f"{selected_portal} is selected, but its live listings are "
                "not connected to this app yet. This portal does not offer "
                "an unrestricted public API that this app can use without "
                "authorization. I won't show invented or unrelated listings."
            )
            st.write(
                "Open the portal's own search for the same keyword and location:"
            )
            st.link_button(
                f"Search {selected_portal}",
                portal_urls[selected_portal],
                use_container_width=True,
            )
            st.caption(
                "To display that portal's actual listings inside AutoJobApply, "
                "we need an approved API/feed or another permitted integration."
            )

