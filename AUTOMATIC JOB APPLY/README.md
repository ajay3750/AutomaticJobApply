# AutoJobApply 💼

**AutoJobApply** is a Python-based job search and application tracking tool built with Streamlit. It helps users search job listings, extract text from resumes, compare resumes with job descriptions, and manage job applications in one place.

## 🚀 Features

- **Job Search:** Search remote job listings using the Remotive public API.
- **Resume Text Extraction:** Extract text from PDF and TXT resumes.
- **Resume Matching:** Calculate text similarity between a resume and a job description.
- **Job Tracking:** Save job listings and track application statuses.
- **Multi-Portal Search:** Prepare job searches for LinkedIn, Naukri, Indeed, Foundit, and Glassdoor.
- **SQLite Database:** Store saved jobs and application details locally.
- **Streamlit Interface:** Use a simple, interactive dashboard.

## 🛠️ Tech Stack

- Python
- Streamlit
- SQLite
- Pandas
- Scikit-learn
- PyMuPDF
- Requests

## 📂 Project Structure

```text
AutoJobApply/
├── app.py
├── job_sources.py
├── requirements.txt
├── README.md
├── .gitignore
└── data/
    └── jobs.db  (local database; not uploaded to GitHub)
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/ajay3750/AutoJobApply.git
cd AutoJobApply
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

**Windows:**

```bat
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
streamlit run app.py
```

Open the local URL shown in the terminal, usually:

`http://localhost:8501`

## 🔎 Job Portal Support

The application currently integrates Remotive for in-app remote job listings.

It also provides search links for:

- LinkedIn Jobs
- Naukri.com
- Indeed
- Foundit
- Glassdoor

The other portals' listings are not automatically imported into the app. Live integrations require an authorized API, data feed, or other permitted access method.

## 📄 Resume Matching

The application extracts text from uploaded PDF and TXT resumes and calculates text similarity with job descriptions using TF-IDF and cosine similarity.

**Note:** This score measures textual similarity. It is not a prediction of hiring probability.

## 🔒 Privacy

- Resume files are processed locally by the application.
- Saved job information is stored in a local SQLite database.
- Do not upload personal resumes, private information, database files, or API credentials to a public repository.

## ⚠️ Limitations

- Job availability and eligibility should be verified on the original listing.
- Search results depend on the connected job source.
- Automated job application submission is not currently implemented.
- Additional job portal integrations may require API access or authorization.

## 🔮 Future Improvements

- Resume-based job ranking
- Better skill extraction and matching
- Additional authorized job-source integrations
- Application date and interview tracking
- Resume tailoring for individual job descriptions
- Application form assistance

## 👨‍💻 Author

**Ajay Maurya**

GitHub: [ajay3750](https://github.com/ajay3750)
