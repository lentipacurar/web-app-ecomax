# app.py
from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required # type: ignore
import smtplib
from email.message import EmailMessage
import os
import json
import base64
import requests
from requests.auth import HTTPBasicAuth

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

from docx import Document
from docxtpl import DocxTemplate

app = Flask(__name__)
app.secret_key = 'Laurentiu'  # Change this to a secret key
login_manager = LoginManager()
login_manager.init_app(app)

# GitHub Configuration
GITHUB_TOKEN = ''
REPO_OWNER = 'lentipacurar'
REPO_NAME = 'ecomaxCI'
BRANCH = 'main'  # Branch to which the file will be uploaded
COMMIT_MESSAGE = 'Add new file via API'
CLIENT_ID = ''
REDIRECT_URI = '#'
SCOPES = '#'
# Directory where templates are stored
TEMPLATES_DIR = 'docx-templates'
OUTPUT_DIR = 'docx-output'

# Ensure the environment variables are set
AZURE_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID')
AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')
# Check if environment variables are correctly set
if not AZURE_CLIENT_ID or not AZURE_TENANT_ID or not AZURE_CLIENT_SECRET:
    raise ValueError("Environment variables for Azure credentials are not set")

AZURE_ENDPOINT = 'https://siventysdocuintel.cognitiveservices.azure.com/'
AZURE_KEY = ''
KEY_VAULT_URL = 'https://siventys.vault.azure.net/'
# Initialize the SecretClient with DefaultAzureCredential
try:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
except Exception as e:
    print(f"Failed to authenticate with DefaultAzureCredential: {e}")
    raise

secret_name = 'GITHUB-LENTIPACURAR-TOKEN'
secret = client.get_secret(secret_name)
GITHUB_TOKEN = secret.value
print(f"step 3: {GITHUB_TOKEN}")
secret_azure_name = 'SIVENTYS-DOCUINTEL-AZURE-KEY'
secret_azure = client.get_secret(secret_azure_name)
AZURE_KEY = secret_azure.value

# sample document
formUrl = 'https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/DriverLicense.png'
extracted_id_data = {}

def to_json(obj):
    return json.dumps(obj, default=lambda obj: obj.__dict__)

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return redirect(url_for('google_login'))

@app.route('/google-login')
def google_login():
    return render_template('google_login.html', client_id=CLIENT_ID, redirect_uri=REDIRECT_URI, scopes=SCOPES)

@app.route('/google-auth', methods=['POST'])
def google_auth():
    token = request.form['idtoken']
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        user = User(idinfo['sub'])
        login_user(user)
        return redirect(url_for('upload'))
    except ValueError:
        return 'Invalid token'

@app.route('/about')
# @login_required
def about():
    return render_template('about.html')

@app.route('/process-upload', methods=['POST'])
# @login_required
def process_upload():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'image' not in request.files:
            return redirect(request.url)
        
        file = request.files['image']
        
        if file.filename == '':
            return redirect(request.url)
        
        if file:
            try:
                # Read the file content and encode it to base64
                content = base64.b64encode(file.read()).decode('utf-8')
                file_name = file.filename

                # Prepare the API URL
                url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_name}'

                # Prepare the payload
                payload = {
                    'message': COMMIT_MESSAGE,
                    'content': content,
                    'branch': BRANCH
                }

                # Make the request to GitHub API
                response = requests.put(url, json=payload, auth=HTTPBasicAuth(REPO_OWNER, GITHUB_TOKEN))

                # Check the response
                if response.status_code == 201 or response.status_code == 422:
                    extracted_id_data = extract_id_data('https://raw.githubusercontent.com/lentipacurar/ecomaxCI/main/'+file_name)
                if extracted_id_data:
                    return extracted_id_data
            except Exception as e:
                return {'error':'Eroare la procesarea si extragerea datelor cartii de identitate'}

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

def extract_id_data(formUrl):
    result = {}
    document_analysis_client = DocumentAnalysisClient(
        endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY)
    )
    
    poller = document_analysis_client.begin_analyze_document_from_url('prebuilt-idDocument', formUrl)
    id_documents = poller.result()

    for idx, id_document in enumerate(id_documents.documents):
        first_name = id_document.fields.get('FirstName')
        if first_name:
            result['first_name'] = first_name.value
            result['first_name_content'] = first_name.content
            result['first_name_confidence'] = first_name.confidence
        last_name = id_document.fields.get('LastName')
        if last_name:
            result['last_name'] = last_name.value
            result['last_name_content'] = last_name.content
            result['last_name_confidence'] = last_name.confidence
        document_number = id_document.fields.get('DocumentNumber')
        if document_number:
            result['document_number'] = document_number.value
            result['document_number_content'] = document_number.content
            result['document_number_confidence'] = document_number.confidence
        personal_number = id_document.fields.get('PersonalNumber')
        if personal_number:
            result['personal_number'] = personal_number.value
            result['personal_number_content'] = personal_number.content
            result['personal_number_confidence'] = personal_number.confidence
        dob = id_document.fields.get('DateOfBirth')
        if dob:
            result['dob'] = dob.value.strftime('%Y-%m-%d')
            result['dob_content'] = dob.content
            result['dob_confidence'] = dob.confidence
        doe = id_document.fields.get('DateOfExpiration')
        if doe:
            result['doe'] = doe.value.strftime('%Y-%m-%d')
            result['doe_content'] = doe.content
            result['doe_confidence'] = doe.confidence
        sex = id_document.fields.get('Sex')
        if sex:
            result['sex'] = sex.value
            result['sex_content'] = sex.content
            result['sex_confidence'] = sex.confidence
        address = id_document.fields.get('Address')
        if address:
            result['address'] = to_json(address.value)
            result['address_content'] = address.content
            result['address_confidence'] = address.confidence
        country_region = id_document.fields.get('CountryRegion')
        if country_region:
            result['country_region'] = country_region.value
            result['country_region_content'] = country_region.content
            result['country_region_confidence'] = country_region.confidence
        region = id_document.fields.get('Region')
        if region:
            result['region'] = region.value
            result['region_content'] = region.content
            result['region_confidence'] = region.confidence
        doi = id_document.fields.get('DateOfIssue')
        if doi:
            result['doi'] = doi.value.strftime('%Y-%m-%d')
            result['doi_content'] = doi.content
            result['doi_confidence'] = doi.confidence
        pob = id_document.fields.get('PlaceOfBirth')
        if pob:
            result['pob'] = pob.value
            result['pob_content'] = pob.content
            result['pob_confidence'] = pob.confidence
        
    return result

@app.route('/get-templates', methods=['GET'])
def get_templates():
    templates_dir = os.path.join(os.path.dirname(__file__), TEMPLATES_DIR)
    if not os.path.exists(templates_dir):
        return jsonify({'error': 'Templates directory does not exist'}), 404
    
    templates = os.listdir(templates_dir)
    return jsonify({'templates': templates})

def send_email(subject, body, to_email, files):
    # Email account credentials
    from_email = 'lenti.pacurar@gmail.com'
    password = 'Rsy0dKXbnq1FWJGO'

    # Create the email message
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    msg.set_content(body)

    # Attach files
    for file in files:
        with open(os.path.join(OUTPUT_DIR, file), 'rb') as f:
            file_data = f.read()
            file_name = file
            msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)

    # Connect to the SMTP server and send the email
    try:
        with smtplib.SMTP_SSL('smtp-relay.brevo.com', 465) as server:
            server.login(from_email, password)
            server.send_message(msg)
        print('Email sent successfully')
    except smtplib.SMTPException as e:
        print(f'SMTP error occurred: {e}')
        raise e
    except Exception as e:
        print(f'An error occurred: {e}')
        raise e
    
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

@app.route('/generate-docs', methods=['POST'])
def generate_docs():
    if request.method == 'POST':
        try:
            # Parse form data
            nume = request.form['nume']
            prenume = request.form['prenume']
            adresa = request.form['adresa']
            cnp = request.form['cnp']
            numar_ci = request.form['numar_ci']
            data_nasterii = request.form['data_nasterii']
            locul_nasterii = request.form['locul_nasterii']
            data_eliberarii = request.form['data_eliberarii']
            data_expirarii = request.form['data_expirarii']
            data_curenta = request.form['data_curenta']
            email = request.form['email']
            templates = request.form.getlist('templates')
            asigurator = request.form['asigurator']
            nr_inmatriculare = request.form['nr_inmatriculare']
            marca_auto = request.form['marca_auto']
            nr_contract = request.form['nr_contract']
            cuantum = request.form['cuantum']
            nr_factura = request.form['nr_factura']
            data_factura = request.form['data_factura']
            dosar_dauna = request.form['dosar_dauna']
            # Data context for the document
            context = {
                'nume': nume,
                'prenume': prenume,
                'adresa': adresa,
                'cnp': cnp,
                'numar_ci': numar_ci,
                'data_nasterii': data_nasterii,
                'locul_nasterii': locul_nasterii,
                'data_eliberarii': data_eliberarii,
                'data_expirarii': data_expirarii,
                'data_curenta': data_curenta,
                'email': email,
                'asigurator': asigurator,
                'nr_inmatriculare': nr_inmatriculare,
                'marca_auto': marca_auto,
                'nr_contract': nr_contract,
                'cuantum': cuantum,
                'nr_factura': nr_factura,
                'data_factura': data_factura,
                'dosar_dauna': dosar_dauna
            }

            # Convert the single string element into a list of file names
            file_names_string = templates[0]  # Get the single string from the array
            file_list = file_names_string.split(',')  # Split the string by commas to get the list

            # Process each template
            generated_files = []
            for template_name in file_list:
                # concatenate template path
                template_path = os.path.join(TEMPLATES_DIR, template_name)

                if not os.path.exists(template_path):
                    return jsonify({'error': f'Modelul {template_name} nu a fost gasit'}), 404

                # Load the template
                doc = DocxTemplate(template_path)

                # Render the template with the context data
                doc.render(context)

                # Save the filled document to the output directory
                output_filename = f'{nume}_{prenume}_completat_{template_name}'
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                doc.save(output_path)

                generated_files.append(output_filename)
            
            # Email usage
            subject = f'Documentele generate pentru {nume} {prenume} in data de {data_curenta}'
            body = 'Atasat documentele generate pe baza cartii de identitate furnizate.'
            to_email = email

            send_email(subject, body, to_email, generated_files)
            return jsonify({'message': 'Documentele au fost generate si expediate prin email cu succes', 'files': generated_files}), 200

        except Exception as e:
            return jsonify({'error':'Eroare la generarea si expedierea documentelor' + str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
