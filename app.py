from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Folder where uploaded files will be saved
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}  # Allowed file extensions

# Create the 'uploads' folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    """Checks if the file extension is in the allowed list."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Home page - Shows welcome message, login, and registration options."""
    return render_template('index.html')  # Return the newly created HTML file

# Keep the old CV upload route for now, even if not directly accessible
@app.route('/upload_cv_page')  # We can add a link to this page later
def upload_cv_page():
    return render_template('upload_cv.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles the CV upload process."""
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return "Your CV has been successfully uploaded! For now, only this message exists; more features are coming soon."
    else:
        return "Invalid file format. Please upload a file in PDF, DOC, or DOCX format."

@app.route('/register')  # New registration page route
def register():
    """Displays the user registration form."""
    return render_template('register.html')  # Return the newly created HTML file

@app.route('/register_post', methods=['POST'])  # Route to process data from the registration form
def register_post():
    """Receives and processes data from the registration form."""
    # You can access form data with request.form
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']

    # For now, let's just print this information to the console
    # In a real application, you would save this information to a database.
    print(f"New User Registration:")
    print(f"First Name: {first_name}")
    print(f"Last Name: {last_name}")
    print(f"Email: {email}")
    print(f"Password (Before Hashing): {password}")  # Do not store passwords directly, always hash them!

    # After successful registration, we can redirect the user to a page
    # For example, to the home page or a success message page
    return redirect(url_for('index'))  # For now, redirecting to the home page

if __name__ == '__main__':
    app.run(debug=True)  # Run the application in debug mode