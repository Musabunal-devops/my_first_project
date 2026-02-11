# Interactive Online CV Platform

This project is a web platform aimed at transforming traditional online CVs into dynamic and interactive formats. Users can upload their CVs, divide them into sections, and receive feedback from recruiters or mentors.

## About the Project
Users can upload their CVs in PDF or Word formats. The system parses these documents and presents them in an interactive format.

## Requirements

- **Docker** and **Docker Compose** must be installed on your computer to run this project.
- No additional Python installation is needed — everything runs inside the Docker container.

## Setup and Running (with Docker)

### Steps:

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd <your-repo-name>
   ```

2. **Start with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

3. **Access the Application:**
   Go to the following address in your browser: [http://localhost:5000](http://localhost:5000)

### Notes
- The database is automatically created when the application is first launched.
- Uploaded files are stored in the `uploads/` folder, and the database is stored in the `instance/` folder (Docker persistent volumes).
- To stop, you can press `Ctrl+C` in the terminal or use the `docker-compose down` command.
- The `SECRET_KEY` in `docker-compose.yml` is a hardcoded demo value for development purposes. In a production environment, it should be stored securely in a `.env` file.

## Usage

1. Register an account and log in.
2. Upload your CV (PDF or Word format) on the upload page.
3. After uploading, a profile page is automatically generated from your CV.
4. **Click on the profile photo** to view the full profile section.
5. Recruiters or mentors can leave feedback on your CV through the feedback system.

## Database Structure

The application uses **SQLite** with three tables:

| Table      | Key Columns                                                        |
|------------|--------------------------------------------------------------------|
| **User**   | id, first_name, last_name, email (unique), password_hash, created_at |
| **CV**     | id, user_id (FK → User), filename, filepath, upload_time            |
| **Feedback** | id, cv_id (FK → CV), user_id (FK → User), author_name, content, rating (1-5), feedback_type, is_anonymous, created_at |

## Known Issues & Future Improvements

- **Email verification** is not yet implemented — users can register with any email without confirmation.
- **Password requirements** are not enforced — there are no rules for minimum length, special characters, etc.
- **CV parsing accuracy** — depending on the CV layout, some sections may be parsed incorrectly or missing. Manual corrections may be needed after profile generation.